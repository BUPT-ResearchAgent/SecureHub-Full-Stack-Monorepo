// Status: partial-real
// 统一问答优先走 durable tutor workflow；不可用时显式降级到本地演示回答。

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ChevronDown,
  MessageSquarePlus,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/app/components/ui/popover';
import { CompanionComposer } from '@/app/features/course/companion/CompanionComposer';
import { CompanionMessageList } from '@/app/features/course/companion/CompanionMessageList';
import type { CompanionMessage } from '@/app/features/course/companion/types';
import { CitationPanel } from '@/app/features/chat/components/CitationPanel';
import { generateMockAnswer, streamChatReal } from '@/app/features/chat/api';
import { CHAT_AGENTS, getChatAgent } from '@/app/features/chat/mockData';
import { useChatWorkspace } from '@/app/features/chat/store';
import { useAuth } from '@/app/features/auth/store';
import { cancelCourseTask } from '@/app/features/course/api';
import {
  CHAT_AGENT_IDS,
  type ChatAgentId,
  type ChatCitation,
  type ChatMessage,
} from '@/app/features/chat/types';
import {
  createAssistantPlaceholder,
  createChatSession,
  createUserMessage,
  getSessionsByAgent,
} from '@/app/features/chat/utils';
import type { EvidenceChunkDTO } from '@/lib/sse.types';

function isChatAgentId(value: string | null): value is ChatAgentId {
  return CHAT_AGENT_IDS.includes(value as ChatAgentId);
}

// 把 ChatCitation 转成 CompanionMessageList 期望的 EvidenceChunkDTO。
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

function chatToCompanionMessages(messages: ChatMessage[]): CompanionMessage[] {
  return messages.map((message) => {
    let status: CompanionMessage['status'] = 'done';
    if (message.status === 'generating') status = 'generating';
    else if (message.status === 'error') status = 'error';
    else if (message.status === 'stopped') status = 'stopped';
    return {
      id: message.id,
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: message.status === 'generating' && !message.content ? '正在思考...' : message.content,
      status,
      evidence: (message.citations ?? []).map(citationToChunk),
    };
  });
}

export function Chat() {
  const { workspace, dispatch, resetDemo } = useChatWorkspace();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const cancelledMessages = useRef<Set<string>>(new Set());
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

  const companionMessages = useMemo<CompanionMessage[]>(() => {
    if (activeSession && activeSession.messages.length) {
      return chatToCompanionMessages(activeSession.messages);
    }
    // 首屏空对话时显示一条 assistant 介绍，模仿 in-course companion 的 hero 文案。
    return [
      {
        id: `intro-${activeAgentId}`,
        role: 'assistant',
        content: scenarioGreeting(activeAgentId),
        status: 'done',
        evidence: [],
      },
    ];
  }, [activeAgentId, activeSession]);

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
  }, [companionMessages, isGenerating]);

  useEffect(() => () => activeStreamRef.current?.unsubscribe(), []);

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
    let fallbackStarted = false;
    let settled = false;
    let unsubscribe = () => {};

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
      try {
        const payload = await generateMockAnswer(agentId, messages, question);
        if (cancelledMessages.current.has(messageId)) {
          cancelledMessages.current.delete(messageId);
          return;
        }
        settled = true;
        dispatch({
          type: 'updateMessage',
          sessionId,
          messageId,
          patch: {
            ...payload,
            status: 'done',
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
        dispatch({
          type: 'updateMessage',
          sessionId,
          messageId,
          patch: {
            status: 'error',
            content: error instanceof Error ? error.message : '演示回答生成失败，请重试。',
            citations: [],
            structuredCards: [],
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
          dispatch({
            type: 'updateMessage',
            sessionId,
            messageId,
            patch: { workflowRunId: start.run_id },
          });
          if (cancelledMessages.current.has(messageId)) {
            void cancelCourseTask(start.run_id).finally(() => {
              unsubscribe();
              cancelledMessages.current.delete(messageId);
              clearActiveStream();
            });
          }
        },
        onToken(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          accumulatedContent = event.replace
            ? event.content
            : accumulatedContent + event.content;
          dispatch({
            type: 'updateMessage',
            sessionId,
            messageId,
            patch: {
              content: accumulatedContent,
              status: 'generating',
            },
          });
        },
        onEvidence(chunk) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          const citation = chunkToCitation(chunk);
          citations = citations.some((item) => item.id === citation.id)
            ? citations
            : [...citations, citation];
          dispatch({
            type: 'updateMessage',
            sessionId,
            messageId,
            patch: { citations },
          });
        },
        onDone(event) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          if (event.status === 'cancelled') {
            settled = true;
            clearActiveStream();
            dispatch({
              type: 'updateMessage',
              sessionId,
              messageId,
              patch: {
                status: 'stopped',
                content: accumulatedContent || '已停止生成。',
              },
            });
            dispatch({ type: 'setGenerating' });
            return;
          }
          settled = true;
          clearActiveStream();
          dispatch({
            type: 'updateMessage',
            sessionId,
            messageId,
            patch: {
              content: accumulatedContent || '回答已完成。',
              status: 'done',
              citations,
              structuredCards: [],
              favorited: workspace.favoriteMessageIds.includes(messageId),
            },
          });
          dispatch({ type: 'setGenerating' });
        },
        onError(error) {
          if (settled || fallbackStarted || cancelledMessages.current.has(messageId)) return;
          if (error.code === 'sse_reconnecting' && error.recoverable) return;
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
    const userMessage = createUserMessage(session.id, question);
    const assistantMessage = createAssistantPlaceholder(session.id);
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

  const handleStop = () => {
    const sessionId = workspace.generatingSessionId;
    const messageId = workspace.generatingMessageId;
    if (!sessionId || !messageId) return;
    const generatingMessage = workspace.sessions
      .find((session) => session.id === sessionId)
      ?.messages.find((message) => message.id === messageId);
    const activeStream = activeStreamRef.current?.messageId === messageId
      ? activeStreamRef.current
      : undefined;
    const runId = activeStream?.runId ?? generatingMessage?.workflowRunId;

    cancelledMessages.current.add(messageId);
    dispatch({
      type: 'updateMessage',
      sessionId,
      messageId,
      patch: {
        status: 'stopped',
        content: generatingMessage?.content || '已停止生成。',
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
    dispatch({ type: 'setActiveAgent', agentId });
    const next = new URLSearchParams(params);
    next.set('tab', agentId);
    navigate(`/chat?${next.toString()}`);
  };

  const handleNewSession = () => {
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
    resetDemo();
    navigate('/chat?tab=topic', { replace: true });
    toast.success('已重置演示数据');
  };

  const handleDraftChange = (value: string) => {
    if (activeSession) dispatch({ type: 'setDraft', sessionId: activeSession.id, value });
  };

  return (
    <div className="space-y-4">
      <header className="space-y-2 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <p className="inline-flex items-center gap-1.5 rounded-full bg-brand-blue-50 px-3 py-1 text-xs font-medium text-brand-blue-700">
              <Sparkles className="h-3 w-3" />
              智能问答
            </p>
            <h1 className="text-2xl font-semibold text-slate-950 dark:text-slate-50">向智能助手提问</h1>
            <p className="max-w-2xl text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              非课程场景下的统一问答入口，9 个智能体在底层协作；选择「问答场景」会改变提问提示与内部路由偏好，
              对话方仍是抽象的智能助手。
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ScenarioSwitcher agentId={activeAgentId} onSelect={handleScenarioChange} />
            <button
              type="button"
              onClick={handleNewSession}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-blue-600 px-3 py-2 text-sm text-white hover:bg-brand-blue-700"
            >
              <MessageSquarePlus className="h-3.5 w-3.5" />
              新建会话
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              重置演示
            </button>
          </div>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-15rem)] gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="flex min-h-[520px] flex-col gap-3 rounded-2xl border border-slate-200 bg-white/60 p-3 dark:border-slate-800 dark:bg-slate-50/[0.97]">
          <CompanionMessageList ref={scrollRef} messages={companionMessages} />
          <div className="mx-auto w-full max-w-[760px]">
            <CompanionComposer
              value={activeDraft}
              placeholder={`向智能助手提问：${activeAgent.name}场景…`}
              isGenerating={isGenerating}
              contextHint={`问答场景：${activeAgent.name}`}
              onChange={handleDraftChange}
              onSend={() => handleSend()}
              onStop={handleStop}
            />
          </div>
        </section>

        <aside className="hidden space-y-4 xl:block xl:max-h-[calc(100vh-15rem)] xl:overflow-y-auto">
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
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <span className="text-[11px] uppercase tracking-wide text-slate-400">场景</span>
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
  return `你好！这里是「${agent.name}」场景下的智能助手。\n\n${agent.description}\n\n本助手由 9 个智能体协作支持，提问后右侧将显示证据链。`;
}
