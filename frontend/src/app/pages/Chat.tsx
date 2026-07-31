// Status: partial-real
// 统一问答优先走 durable tutor workflow；不可用时显式降级到本地演示回答。

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Bot,
  ChevronDown,
  MessageSquarePlus,
  RotateCcw,
  Sparkles,
  Workflow,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { ChatComposer } from '@/app/features/chat/components/ChatComposer';
import { ChatMessageList } from '@/app/features/chat/components/ChatMessageList';
import { CitationPanel } from '@/app/features/chat/components/CitationPanel';
import {
  generateChatImage,
  generateChatVideo,
  generateMockAnswer,
  streamChatReal,
  type VideoPreparationStatus,
} from '@/app/features/chat/api';
import {
  activityFromProgress,
  activityFromTrace,
  completeActivities,
  createComposeActivity,
  createDemoActivities,
  createEvidenceActivity,
  createInitialActivities,
  createReconnectActivity,
  createWorkflowActivity,
  upsertActivity,
} from '@/app/features/chat/activity';
import { CHAT_AGENTS, getChatAgent } from '@/app/features/chat/mockData';
import { resolveLocalVideoPreset } from '@/app/features/chat/mediaPresets';
import { useChatWorkspace } from '@/app/features/chat/store';
import { useAuth } from '@/app/features/auth/store';
import { cancelCourseTask } from '@/app/features/course/api';
import {
  CHAT_AGENT_IDS,
  type ChatAgentId,
  type ChatCitation,
  type ChatMessage,
  type ChatRuntimeSummary,
  type MediaAttachment,
  type MediaGenerationRequest,
} from '@/app/features/chat/types';
import {
  createAssistantPlaceholder,
  createChatSession,
  createMediaAssistantPlaceholder,
  createMediaUserMessage,
  createUserMessage,
  getSessionsByAgent,
  normalizeVideoFailureMessage,
} from '@/app/features/chat/utils';
import type { EvidenceChunkDTO } from '@/lib/sse.types';

function isChatAgentId(value: string | null): value is ChatAgentId {
  return CHAT_AGENT_IDS.includes(value as ChatAgentId);
}

// 把 ChatCitation 转成右侧证据面板期望的 EvidenceChunkDTO。
function citationToChunk(citation: ChatCitation): EvidenceChunkDTO {
  if (citation.evidence) return citation.evidence;
  return {
    chunk_id: citation.id,
    document_id: `chat-${citation.id}`,
    chunk_text: citation.excerpt,
    score: citation.reliability / 100,
    platform: citation.type === 'internal' ? 'securehub' : citation.type,
    rights_note: '演示引用，仅用于本地问答面板',
    source_url: citation.url,
    title: citation.title,
    author: citation.source,
    published_at: null,
    fetched_at: null,
    asset_type: citation.type,
    page_no: null,
    chapter: citation.title,
    timestamp: null,
    license: null,
    reliability: citation.reliability / 100,
  };
}

function chunkToCitation(chunk: EvidenceChunkDTO): ChatCitation {
  const descriptor = `${chunk.platform} ${chunk.asset_type ?? ''}`.toLowerCase();
  let type: ChatCitation['type'] = 'internal';
  if (/(paper|论文|arxiv|scholar)/.test(descriptor)) type = 'paper';
  else if (/(policy|政策|gov|法规)/.test(descriptor)) type = 'policy';
  else if (/(competition|竞赛|赛事)/.test(descriptor)) type = 'competition';
  else if (/(news|新闻|媒体)/.test(descriptor)) type = 'news';
  else if (/(project|项目|github)/.test(descriptor)) type = 'project';

  const rawReliability = chunk.reliability ?? chunk.score;
  const reliability = rawReliability <= 1 ? rawReliability * 100 : rawReliability;
  return {
    id: chunk.chunk_id,
    title: chunk.title ?? chunk.chapter ?? `证据片段 ${chunk.chunk_id.slice(0, 8)}`,
    source: chunk.author ?? chunk.platform,
    url: chunk.source_url ?? '',
    type,
    reliability: Math.round(Math.max(0, Math.min(100, reliability))),
    excerpt: chunk.chunk_text || chunk.excerpt || '该证据片段暂无可展示文本。',
    evidence: chunk,
  };
}

export function Chat() {
  const { workspace, dispatch, resetDemo } = useChatWorkspace();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mediaRequest, setMediaRequest] = useState<MediaGenerationRequest>();
  const cancelledMessages = useRef<Set<string>>(new Set());
  const mediaJobsRef = useRef<Map<string, AbortController>>(new Map());
  const activeStreamRef = useRef<{
    sessionId: string;
    messageId: string;
    runId?: string;
    unsubscribe: () => void;
  }>();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const tabParam = params.get('tab');
  const activeAgentId: ChatAgentId = isChatAgentId(tabParam)
    ? tabParam
    : workspace.activeAgentId;
  const activeAgent = getChatAgent(activeAgentId);
  const sessions = getSessionsByAgent(workspace, activeAgentId);
  const activeSession =
    sessions.find((session) => session.id === workspace.activeSessionId) ?? sessions[0];
  const activeDraft = activeSession ? (workspace.drafts[activeSession.id] ?? '') : '';
  const isGenerating = Boolean(workspace.generatingMessageId);

  const lastAssistantMessage = useMemo(() => {
    if (!activeSession) return undefined;
    return [...activeSession.messages]
      .reverse()
      .find((message) => message.role === 'assistant' && message.status !== 'stopped');
  }, [activeSession]);

  const citationChunks = (lastAssistantMessage?.citations ?? []).map(citationToChunk);

  // URL 优先：tab=<agentId> 同步到 store。
  useEffect(() => {
    if (tabParam && isChatAgentId(tabParam)) {
      if (tabParam !== workspace.activeAgentId) {
        dispatch({ type: 'setActiveAgent', agentId: tabParam });
      }
      return;
    }
    const next = new URLSearchParams(params);
    next.set('tab', workspace.activeAgentId);
    navigate(`/chat?${next.toString()}`, { replace: true });
  }, [dispatch, navigate, params, tabParam, workspace.activeAgentId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [activeSession?.messages, isGenerating]);

  useEffect(() => () => {
    activeStreamRef.current?.unsubscribe();
    mediaJobsRef.current.forEach((controller) => controller.abort());
    mediaJobsRef.current.clear();
  }, []);

  const runAnswerGeneration = async (
    agentId: ChatAgentId,
    sessionId: string,
    messageId: string,
    question: string,
    messages: ChatMessage[],
  ) => {
    cancelledMessages.current.delete(messageId);
    let accumulatedContent = '';
    let citations: ChatCitation[] = [];
    let activities = createInitialActivities(agentId);
    let runtime: ChatRuntimeSummary = {
      mode: 'real',
      startedAt: new Date().toISOString(),
    };
    let fallbackStarted = false;
    let settled = false;
    let unsubscribe = () => {};

    const publishExecution = (patch: Partial<ChatMessage> = {}) => {
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          activities: [...activities],
          runtime: { ...runtime },
          ...patch,
        },
      });
    };

    const clearActiveStream = () => {
      if (activeStreamRef.current?.messageId === messageId) {
        activeStreamRef.current = undefined;
      }
    };

    const runFallback = async () => {
      if (fallbackStarted || settled || cancelledMessages.current.has(messageId)) return;
      fallbackStarted = true;
      unsubscribe();
      const liveRunId = activeStreamRef.current?.messageId === messageId
        ? activeStreamRef.current.runId
        : undefined;
      clearActiveStream();
      if (liveRunId) {
        void cancelCourseTask(liveRunId).catch(() => undefined);
      }
      toast.warning('后端暂不可用，已降级为演示模式');
      runtime = {
        mode: 'demo',
        startedAt: new Date().toISOString(),
      };
      activities = createDemoActivities(agentId, 0, 'running');
      publishExecution({ status: 'generating' });
      try {
        const payload = await generateMockAnswer(agentId, messages, question);
        if (cancelledMessages.current.has(messageId)) {
          cancelledMessages.current.delete(messageId);
          return;
        }
        settled = true;
        activities = createDemoActivities(agentId, payload.citations.length);
        runtime = {
          ...runtime,
          finishedAt: new Date().toISOString(),
        };
        dispatch({
          type: 'updateMessage',
          sessionId,
          messageId,
          patch: {
            ...payload,
            status: 'done',
            activities,
            runtime,
            favorited: workspace.favoriteMessageIds.includes(messageId),
          },
        });
        dispatch({ type: 'setGenerating' });
      } catch (error) {
        if (cancelledMessages.current.has(messageId)) {
          cancelledMessages.current.delete(messageId);
          return;
        }
        settled = true;
        activities = upsertActivity(activities, {
          id: 'demo-error',
          kind: 'system',
          title: '演示回答生成失败',
          detail: error instanceof Error ? error.message : '本地演示规则未能返回结果',
          status: 'error',
        });
        runtime = { ...runtime, finishedAt: new Date().toISOString() };
        dispatch({
          type: 'updateMessage',
          sessionId,
          messageId,
          patch: {
            status: 'error',
            content: error instanceof Error ? error.message : '演示回答生成失败，请重试。',
            citations: [],
            structuredCards: [],
            activities,
            runtime,
          },
        });
        dispatch({ type: 'setGenerating' });
        toast.error('回答生成失败，可点击重试');
      }
    };

    if (!user?.id) {
      await runFallback();
      return;
    }

    try {
      unsubscribe = streamChatReal(agentId, question, messages, {
        userId: user.id,
        onRunStart(start) {
          if (activeStreamRef.current?.messageId === messageId) {
            activeStreamRef.current.runId = start.run_id;
          }
          activities = upsertActivity(activities, {
            id: 'intent-routing',
            kind: 'plan',
            title: '理解问题并规划回答',
            detail: '已完成场景识别，正在调度所需智能体',
            status: 'done',
          });
          activities = upsertActivity(activities, createWorkflowActivity(start.run_id));
          publishExecution({ workflowRunId: start.run_id });
          if (cancelledMessages.current.has(messageId)) {
            void cancelCourseTask(start.run_id).finally(() => {
              unsubscribe();
              cancelledMessages.current.delete(messageId);
              clearActiveStream();
            });
          }
        },
        onProgress(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          activities = upsertActivity(activities, activityFromProgress(event));
          publishExecution();
        },
        onTrace(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          activities = upsertActivity(activities, activityFromTrace(event));
          runtime = {
            ...runtime,
            provider: event.provider ?? runtime.provider,
            model: event.model ?? runtime.model,
            qualityScore: event.quality_score && event.quality_score > 0
              ? event.quality_score
              : runtime.qualityScore,
          };
          publishExecution();
        },
        onToken(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          accumulatedContent = event.replace
            ? event.content
            : accumulatedContent + event.content;
          if (activities.some((activity) => activity.id === 'stream-reconnect')) {
            activities = upsertActivity(activities, {
              ...createReconnectActivity(),
              detail: '回答流已恢复，并从上次位置继续',
              status: 'done',
            });
          }
          activities = upsertActivity(activities, createComposeActivity('running'));
          publishExecution({
            content: accumulatedContent,
            status: 'generating',
          });
        },
        onEvidence(chunk) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          const citation = chunkToCitation(chunk);
          citations = citations.some((item) => item.id === citation.id)
            ? citations
            : [...citations, citation];
          activities = upsertActivity(activities, createEvidenceActivity(citations.length));
          publishExecution({ citations });
        },
        onDone(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          if (event.status === 'cancelled') {
            settled = true;
            clearActiveStream();
            activities = completeActivities(activities);
            activities = upsertActivity(activities, {
              id: 'compose-answer',
              kind: 'compose',
              title: '回答生成已停止',
              detail: '用户停止了后续生成，已保留当前可见内容',
              status: 'error',
            });
            runtime = { ...runtime, finishedAt: new Date().toISOString() };
            dispatch({
              type: 'updateMessage',
              sessionId,
              messageId,
              patch: {
                status: 'stopped',
                content: accumulatedContent || '已停止生成。',
                activities,
                runtime,
              },
            });
            dispatch({ type: 'setGenerating' });
            return;
          }
          settled = true;
          clearActiveStream();
          activities = completeActivities(activities);
          activities = upsertActivity(activities, createComposeActivity('done'));
          if (event.quality_score > 0) {
            const qualityPercent = event.quality_score <= 1
              ? Math.round(event.quality_score * 100)
              : Math.round(event.quality_score);
            activities = upsertActivity(activities, {
              id: 'quality-check',
              kind: 'quality',
              title: '质量评估智能体 · 执行质量检查',
              detail: `回答通过质量闸，评分 ${qualityPercent}%`,
              status: 'done',
              agentId: 'outcome_evaluator',
              skillId: 'QualityCheck',
            });
          }
          runtime = {
            ...runtime,
            qualityScore: event.quality_score || runtime.qualityScore,
            finishedAt: new Date().toISOString(),
          };
          dispatch({
            type: 'updateMessage',
            sessionId,
            messageId,
            patch: {
              content: accumulatedContent || '回答已完成。',
              status: 'done',
              citations,
              structuredCards: [],
              activities,
              runtime,
              favorited: workspace.favoriteMessageIds.includes(messageId),
            },
          });
          dispatch({ type: 'setGenerating' });
        },
        onError(error) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          if (error.code === 'sse_reconnecting' && error.recoverable) {
            activities = upsertActivity(activities, createReconnectActivity());
            publishExecution();
            return;
          }
          void runFallback();
        },
      });
      activeStreamRef.current = {
        sessionId,
        messageId,
        unsubscribe,
      };
    } catch {
      await runFallback();
    }
  };

  const runMediaGeneration = async (
    sessionId: string,
    messageId: string,
    request: MediaGenerationRequest,
  ) => {
    mediaJobsRef.current.get(messageId)?.abort();
    const controller = new AbortController();
    mediaJobsRef.current.set(messageId, controller);
    const startedAt = new Date().toISOString();
    const usesCuratedVideo = request.type === 'video'
      && Boolean(resolveLocalVideoPreset(request.prompt));
    let activities: NonNullable<ChatMessage['activities']> = [
      {
        id: 'media-request',
        kind: 'plan',
        title: '解析媒体生成请求',
        detail: `已确认${request.type === 'image' ? '图片' : '视频'}类型、尺寸与课程主题`,
        status: 'done',
        startedAt,
        finishedAt: startedAt,
      },
      {
        id: usesCuratedVideo ? 'media-local-match' : 'media-provider',
        kind: 'tool',
        title: usesCuratedVideo ? '匹配本地课程媒体' : '调用实时媒体生成服务',
        detail: usesCuratedVideo
          ? '正在检查固定提示词与本地视频映射'
          : '正在提交受保护的生成请求',
        status: 'running',
        startedAt,
      },
    ];

    const publishActivities = () => {
      if (controller.signal.aborted) return;
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          activities: [...activities],
          mediaGenerationStatus: 'generating',
          status: 'generating',
          runtime: {
            mode: usesCuratedVideo ? 'curated' : 'real',
            startedAt,
          },
        },
      });
    };

    const onProviderStatus = (
      status: VideoPreparationStatus,
      attempt?: number,
    ) => {
      if (controller.signal.aborted) return;
      if (status === 'matching-local') {
        const matchedAt = new Date().toISOString();
        activities = upsertActivity(activities, {
          id: 'media-local-match',
          kind: 'tool',
          title: '匹配本地课程媒体',
          detail: '固定提示词已命中 HTTP / HTTPS 课程视频映射',
          status: 'done',
          finishedAt: matchedAt,
        });
        activities = upsertActivity(activities, {
          id: 'media-asset',
          kind: 'tool',
          title: '准备本地视频资源',
          detail: '正在校验 MP4 文件的可访问性与媒体类型',
          status: 'running',
          startedAt: matchedAt,
        });
      } else if (status === 'loading-local') {
        activities = upsertActivity(activities, {
          id: 'media-asset',
          kind: 'tool',
          title: '准备本地视频资源',
          detail: '已确认本地 MP4，正在准备会话内播放',
          status: 'done',
          finishedAt: new Date().toISOString(),
        });
      } else if (status === 'submitting') {
        activities = upsertActivity(activities, {
          id: 'media-provider',
          kind: 'tool',
          title: '调用实时媒体生成服务',
          detail: '已通过统一鉴权 API 提交生成参数',
          status: 'running',
        });
      } else if (status === 'pending' || status === 'processing') {
        activities = upsertActivity(activities, {
          id: 'media-provider',
          kind: 'tool',
          title: '调用实时媒体生成服务',
          detail: '上游已接受任务，本地仅保留用户隔离的任务标识',
          status: 'done',
        });
        activities = upsertActivity(activities, {
          id: 'media-poll',
          kind: 'tool',
          title: '轮询视频生成状态',
          detail: `第 ${attempt ?? 1} 次查询 · ${status === 'pending' ? '等待渲染' : '正在渲染'}`,
          status: 'running',
        });
      } else {
        activities = upsertActivity(activities, {
          id: 'media-provider',
          kind: 'tool',
          title: '调用实时媒体生成服务',
          detail: '媒体服务已返回生成结果',
          status: 'done',
        });
        if (request.type === 'video') {
          activities = upsertActivity(activities, {
            id: 'media-poll',
            kind: 'tool',
            title: '轮询视频生成状态',
            detail: '任务已完成，停止继续轮询',
            status: 'done',
          });
        }
        activities = upsertActivity(activities, {
          id: 'media-asset',
          kind: 'tool',
          title: '准备受保护媒体资源',
          detail: '资源已由后端安全持久化，正在准备会话内展示',
          status: 'running',
        });
      }
      publishActivities();
    };

    publishActivities();
    try {
      let attachment: MediaAttachment;
      if (request.type === 'image') {
        if (!request.kpId) {
          throw new Error(
            '图片生成需要明确关联知识点，请重新打开图片生成面板选择预设或确认默认关联。',
          );
        }
        attachment = await generateChatImage(
          request.kpId,
          request.prompt,
          '2K',
          {
            signal: controller.signal,
            onStatus: (status) => onProviderStatus(status),
          },
        );
      } else {
        attachment = await generateChatVideo(request.prompt, {
          kpId: request.kpId,
          size: request.size === '720x1280' ? '720x1280' : '1280x720',
          duration: '10',
          signal: controller.signal,
          onStatus: onProviderStatus,
        });
      }
      if (controller.signal.aborted) return;
      activities = completeActivities(activities);
      activities = upsertActivity(activities, {
        id: 'media-asset',
        kind: 'tool',
        title: attachment.source === 'curated' ? '准备本地视频资源' : '准备受保护媒体资源',
        detail: attachment.source === 'curated'
          ? '已准备同源本地视频，可在会话内直接播放'
          : '已生成会话内可鉴权加载的媒体附件',
        status: 'done',
      });
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          content: request.type === 'image'
            ? '教学图解已生成，可点击图片放大查看。'
            : attachment.source === 'curated'
              ? '教学视频已准备，可在下方直接播放。'
              : '教学视频已生成，可在下方直接播放。',
          status: 'done',
          mediaGenerationStatus: 'completed',
          mediaAttachments: [attachment],
          activities,
          runtime: {
            mode: attachment.source === 'curated' ? 'curated' : 'real',
            provider: attachment.provider,
            model: attachment.model,
            startedAt,
            finishedAt: new Date().toISOString(),
          },
          favorited: workspace.favoriteMessageIds.includes(messageId),
        },
      });
      toast.success(
        request.type === 'image'
          ? '图片生成完成'
          : attachment.source === 'curated'
            ? '本地教学视频已准备'
            : '视频生成完成',
      );
    } catch (error) {
      const aborted = error instanceof DOMException && error.name === 'AbortError';
      const failureMessage = aborted
        ? '已停止等待媒体生成结果，可修改描述后重新提交。'
        : request.type === 'video'
          ? normalizeVideoFailureMessage(
            error instanceof Error ? error.message : '实时媒体生成失败，请稍后重试。',
          )
          : error instanceof Error
            ? error.message
            : '实时媒体生成失败，请稍后重试。';
      activities = activities.map((activity) => (
        activity.status === 'running' || activity.status === 'pending'
          ? {
            ...activity,
            status: 'error' as const,
            detail: aborted ? '用户停止了前端等待' : failureMessage,
            finishedAt: new Date().toISOString(),
          }
          : activity
      ));
      dispatch({
        type: 'updateMessage',
        sessionId,
        messageId,
        patch: {
          content: failureMessage,
          status: aborted ? 'stopped' : 'error',
          mediaGenerationStatus: 'failed',
          mediaAttachments: [],
          activities,
          runtime: {
            mode: usesCuratedVideo ? 'curated' : 'real',
            startedAt,
            finishedAt: new Date().toISOString(),
          },
        },
      });
      if (!aborted) {
        toast.error(usesCuratedVideo ? '本地视频资源尚未就绪' : '媒体生成失败，可在消息中重试');
      }
    } finally {
      if (mediaJobsRef.current.get(messageId) === controller) {
        mediaJobsRef.current.delete(messageId);
        dispatch({ type: 'setGenerating' });
      }
    }
  };

  const createSessionForAgent = (agentId: ChatAgentId) => {
    const session = createChatSession(agentId);
    dispatch({ type: 'addSession', session });
    return session;
  };

  const handleSend = (questionOverride?: string) => {
    const question = (questionOverride ?? activeDraft).trim();
    if (!question) return;
    if (isGenerating) {
      toast.info('当前回答仍在生成中，请先停止或等待完成');
      return;
    }

    const session = activeSession ?? createSessionForAgent(activeAgentId);
    if (mediaRequest) {
      const request = { ...mediaRequest, prompt: question };
      const userMessage = createMediaUserMessage(session.id, request);
      const assistantMessage = createMediaAssistantPlaceholder(session.id, request);
      dispatch({ type: 'setDraft', sessionId: session.id, value: '' });
      dispatch({
        type: 'appendMessages',
        sessionId: session.id,
        messages: [userMessage, assistantMessage],
      });
      dispatch({
        type: 'setGenerating',
        sessionId: session.id,
        messageId: assistantMessage.id,
      });
      setMediaRequest(undefined);
      void runMediaGeneration(session.id, assistantMessage.id, request);
      return;
    }
    const userMessage = createUserMessage(session.id, question);
    const assistantMessage = createAssistantPlaceholder(session.id, activeAgentId);
    const messagesForGeneration = [...session.messages, userMessage];

    dispatch({ type: 'setDraft', sessionId: session.id, value: '' });
    dispatch({
      type: 'appendMessages',
      sessionId: session.id,
      messages: [userMessage, assistantMessage],
    });
    dispatch({
      type: 'setGenerating',
      sessionId: session.id,
      messageId: assistantMessage.id,
    });
    void runAnswerGeneration(activeAgentId, session.id, assistantMessage.id, question, messagesForGeneration);
  };

  const handleMediaSelect = (request: MediaGenerationRequest) => {
    const session = activeSession ?? createSessionForAgent(activeAgentId);
    setMediaRequest(request);
    dispatch({ type: 'setDraft', sessionId: session.id, value: request.prompt });
  };

  const handleRetryMedia = (messageId: string) => {
    if (isGenerating) {
      toast.info('当前任务仍在生成中，请先停止或等待完成');
      return;
    }
    const session = workspace.sessions.find((item) =>
      item.messages.some((message) => message.id === messageId),
    );
    const message = session?.messages.find((item) => item.id === messageId);
    if (!session || !message?.mediaRequest) {
      toast.error('未找到可重试的媒体请求');
      return;
    }
    const retryRequest: MediaGenerationRequest = message.mediaRequest.type === 'image'
      ? { ...message.mediaRequest, size: '2K' }
      : message.mediaRequest;
    dispatch({ type: 'setActiveSession', sessionId: session.id });
    dispatch({ type: 'setDraft', sessionId: session.id, value: retryRequest.prompt });
    setMediaRequest(retryRequest);
    toast.info('已载入原描述，修改并发送后将创建新的媒体任务');
  };

  const handleStop = () => {
    const sessionId = workspace.generatingSessionId;
    const messageId = workspace.generatingMessageId;
    if (!sessionId || !messageId) return;
    const generatingMessage = workspace.sessions
      .find((session) => session.id === sessionId)
      ?.messages.find((message) => message.id === messageId);
    const mediaController = mediaJobsRef.current.get(messageId);
    if (mediaController) {
      mediaController.abort();
      toast.info('已停止前端等待；上游任务可能仍会按服务方策略结束');
      return;
    }
    const activeStream = activeStreamRef.current?.messageId === messageId
      ? activeStreamRef.current
      : undefined;
    const runId = activeStream?.runId ?? generatingMessage?.workflowRunId;

    cancelledMessages.current.add(messageId);
    const stoppedActivities = generatingMessage?.activities?.map((activity) => (
      activity.status === 'running' || activity.status === 'pending'
        ? {
          ...activity,
          status: 'error' as const,
          detail: activity.id === 'compose-answer'
            ? '用户停止了后续生成，已保留当前可见内容'
            : activity.detail,
          finishedAt: new Date().toISOString(),
        }
        : activity
    ));
    dispatch({
      type: 'updateMessage',
      sessionId,
      messageId,
      patch: {
        status: 'stopped',
        content: generatingMessage?.content || '已停止生成。',
        activities: stoppedActivities,
        runtime: generatingMessage?.runtime
          ? { ...generatingMessage.runtime, finishedAt: new Date().toISOString() }
          : undefined,
      },
    });
    dispatch({ type: 'setGenerating' });

    if (runId) {
      activeStream?.unsubscribe();
      activeStreamRef.current = undefined;
      void cancelCourseTask(runId)
        .then(() => toast.info('已停止真实回答任务'))
        .catch(() => toast.error('停止请求未获后端确认，请稍后检查任务状态'))
        .finally(() => cancelledMessages.current.delete(messageId));
      return;
    }
    toast.info(activeStream ? '正在停止真实回答任务' : '已停止生成');
  };

  const handleScenarioChange = (agentId: ChatAgentId) => {
    setMediaRequest(undefined);
    dispatch({ type: 'setActiveAgent', agentId });
    const next = new URLSearchParams(params);
    next.set('tab', agentId);
    navigate(`/chat?${next.toString()}`);
  };

  const handleNewSession = () => {
    setMediaRequest(undefined);
    createSessionForAgent(activeAgentId);
    toast.success('已新建会话');
  };

  const handleReset = () => {
    const messageId = workspace.generatingMessageId;
    const activeStream = activeStreamRef.current;
    if (messageId) cancelledMessages.current.add(messageId);
    if (activeStream?.runId) {
      activeStream.unsubscribe();
      void cancelCourseTask(activeStream.runId).catch(() => undefined);
      activeStreamRef.current = undefined;
    }
    mediaJobsRef.current.forEach((controller) => controller.abort());
    mediaJobsRef.current.clear();
    setMediaRequest(undefined);
    resetDemo();
    navigate('/chat?tab=topic', { replace: true });
    toast.success('已重置演示数据');
  };

  const handleDraftChange = (value: string) => {
    if (activeSession) dispatch({ type: 'setDraft', sessionId: activeSession.id, value });
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 dark:border-slate-800 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="mb-2 hidden items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-blue-700 dark:text-blue-300 sm:inline-flex">
            <Sparkles className="h-3.5 w-3.5" />
            SecureHub Intelligence
          </p>
          <h1 className="text-2xl font-semibold tracking-[-0.025em] text-slate-950 dark:text-slate-50 sm:text-[28px]">
            智能问答
          </h1>
          <p className="mt-1.5 hidden max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400 sm:block">
            像使用通用大模型一样自然提问，同时查看 9 个智能体的可审计协作、工具动作与证据来源。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
            <ScenarioSwitcher agentId={activeAgentId} onSelect={handleScenarioChange} />
            <button
              type="button"
              onClick={handleNewSession}
              className="inline-flex h-9 w-9 items-center justify-center gap-1.5 rounded-full bg-brand-blue-600 text-xs font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-brand-blue-700 hover:shadow-md sm:w-auto sm:px-3.5"
              aria-label="新建会话"
            >
              <MessageSquarePlus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">新建会话</span>
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex h-9 w-9 items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-white text-xs text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 sm:w-auto sm:px-3.5"
              aria-label="重置演示"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">重置演示</span>
            </button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_310px]">
        <section className="flex min-h-[640px] flex-col overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-[0_24px_70px_-50px_rgba(15,23,42,0.45)] dark:border-slate-800 dark:bg-slate-950 xl:h-[calc(100vh-13.5rem)]">
          <div className="flex items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90 sm:px-5">
            <span
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-white shadow-[0_8px_22px_-14px_rgba(0,51,153,0.8)]"
              style={{ backgroundColor: activeAgent.color }}
            >
              <Bot className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-slate-800 dark:text-slate-100">安枢智能助手</p>
              <p className="mt-0.5 truncate text-[10px] text-slate-400">{activeAgent.name}场景 · 证据增强回答</p>
            </div>
            <div className="ml-auto hidden items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 sm:inline-flex">
              <Workflow className="h-3 w-3" />
              可审计协作
            </div>
          </div>

          <ChatMessageList
            ref={scrollRef}
            messages={activeSession?.messages ?? []}
            agent={activeAgent}
            emptyGreeting={scenarioGreeting(activeAgentId)}
            onToggleFavorite={(messageId) => dispatch({ type: 'toggleFavoriteMessage', messageId })}
            onHelpful={(messageId, helpful) => {
              dispatch({ type: 'setMessageHelpful', messageId, helpful });
              toast.success(helpful ? '已标记为有帮助' : '已记录改进反馈');
            }}
            onRetryMedia={handleRetryMedia}
          />

          <ChatComposer
            value={activeDraft}
            placeholder={mediaRequest
              ? `编辑${mediaRequest.type === 'image' ? '图片' : '视频'}生成描述…`
              : `向智能助手提问，当前为${activeAgent.name}场景…`}
            isGenerating={isGenerating}
            contextHint={mediaRequest
              ? `媒体模式：${mediaRequest.type === 'image'
                ? '实时图片生成'
                : resolveLocalVideoPreset(mediaRequest.prompt)
                  ? '本地课程视频'
                  : '实时视频生成'}`
              : `当前场景：${activeAgent.name} · 自动路由到合适的智能体`}
            mediaRequest={mediaRequest}
            onChange={handleDraftChange}
            onMediaSelect={handleMediaSelect}
            onClearMedia={() => setMediaRequest(undefined)}
            onSend={() => handleSend()}
            onStop={handleStop}
          />
        </section>

        <aside className="hidden xl:block xl:h-[calc(100vh-13.5rem)] xl:overflow-y-auto xl:pr-1 [scrollbar-width:thin]">
          <CitationPanel chunks={citationChunks} />
        </aside>
      </div>
    </div>
  );
}

function ScenarioSwitcher({
  agentId,
  onSelect,
}: {
  agentId: ChatAgentId;
  onSelect: (agentId: ChatAgentId) => void;
}) {
  const active = getChatAgent(agentId);
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="选择问答场景"
          className="inline-flex h-9 items-center gap-2 rounded-full border border-slate-200 bg-white px-2.5 text-xs text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 sm:px-3.5"
        >
          <span className="hidden text-[10px] uppercase tracking-[0.1em] text-slate-400 sm:inline">场景</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">{active.name}</span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[320px] p-0">
        <ul role="listbox" aria-label="问答场景">
          {CHAT_AGENTS.map((agent) => {
            const selected = agent.id === agentId;
            return (
              <li key={agent.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => onSelect(agent.id)}
                  className={`flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-xs transition-colors hover:bg-slate-50 dark:hover:bg-slate-800 ${
                    selected ? 'bg-brand-blue-50/60 dark:bg-brand-blue-800/30' : ''
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{agent.name}</span>
                    {selected && (
                      <span className="rounded-full bg-brand-blue-100 px-1.5 py-0.5 text-[10px] text-brand-blue-700">
                        当前
                      </span>
                    )}
                  </span>
                  <span className="line-clamp-2 text-[11px] text-slate-500 dark:text-slate-400">{agent.description}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

function scenarioGreeting(agentId: ChatAgentId): string {
  const agent = getChatAgent(agentId);
  const starters = agent.starterQuestions.slice(0, 3).map((question) => `- ${question}`).join('\n');
  return [
    `你好，我是「${agent.name}」场景下的智能助手。`,
    '',
    agent.description,
    '',
    '### 你可以这样问',
    '',
    starters,
    '',
    '> 发送问题后，我会展示参与协作的智能体、执行动作和可核验的证据来源。',
  ].join('\n');
}
