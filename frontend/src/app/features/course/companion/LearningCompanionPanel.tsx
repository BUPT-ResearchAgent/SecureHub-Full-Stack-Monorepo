import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, PanelRightOpen } from 'lucide-react';
import { toast } from 'sonner';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { cn } from '@/app/components/ui/utils';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { analyzeImage } from '@/lib/api';
import type { AgentRunDTO } from '@/lib/sse.types';
import {
  type WorkflowEvent,
  type WorkflowRunStartResponse,
} from '@/lib/workflow-run.types';
import type { CourseCatalogItem } from '../catalog/courseCatalog.types';
import { resumeCourseTask, startCourseTask, tutorAnswerFromWorkflowStatus } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';
import { CompanionComposer } from './CompanionComposer';
import { CompanionMessageList } from './CompanionMessageList';
import { getCompanionPreset } from './companionPresets';
import type { CompanionAttachment, CompanionMessage } from './types';

function messageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function initialMessages(courseId: string, greeting: string): CompanionMessage[] {
  return [{
    id: `assistant-intro-${courseId}`,
    role: 'assistant',
    content: greeting,
    status: 'done',
    evidence: [],
  }];
}

export function LearningCompanionPanel({
  course,
  onWorkflowTrace,
  onWorkflowStart,
  onWorkflowEvent,
  onShowWorkflow,
  onImageWorkflowRun,
  presenterMode = false,
  workflowCollapsed,
  className,
}: {
  course: CourseCatalogItem;
  onWorkflowTrace: (run: AgentRunDTO) => void;
  onWorkflowStart: (start: WorkflowRunStartResponse) => void;
  onWorkflowEvent: (event: WorkflowEvent) => void;
  /** Chat-first：右侧编排图折叠时，header 显示「显示编排图」入口。 */
  onShowWorkflow?: () => void;
  onImageWorkflowRun?: () => void;
  /** Fixtures are only available when CourseStudy explicitly enables PresenterMode. */
  presenterMode?: boolean;
  workflowCollapsed?: boolean;
  className?: string;
}) {
  const preset = useMemo(() => getCompanionPreset(course), [course]);
  const isPreview = course.contentStatus === 'preview';
  const { taskContext, companionSessions } = useCourseState();
  const courseDispatch = useCourseDispatch();
  const [draft, setDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const streamCancelRef = useRef<(() => void) | undefined>();
  const recoveryAttemptedRef = useRef<string | null>(null);
  const objectUrlsRef = useRef<string[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [attachments, setAttachments] = useState<CompanionAttachment[]>([]);
  const [conversationState, setConversationState] = useState(() => ({
    courseId: course.id,
    messages: companionSessions[course.id] ?? initialMessages(course.id, preset.greeting),
  }));
  const messages = conversationState.messages;

  const updateMessages = (update: (current: CompanionMessage[]) => CompanionMessage[]) => {
    setConversationState((current) => ({ ...current, messages: update(current.messages) }));
  };

  const updateAssistant = (assistantId: string, update: (message: CompanionMessage) => CompanionMessage) => {
    updateMessages((current) => current.map((message) => (message.id === assistantId ? update(message) : message)));
  };

  // Keep each course's durable conversation separate while allowing a page
  // switch or reload to restore its last terminal/pending tutor root.
  useEffect(() => {
    if (conversationState.courseId === course.id) return;
    streamCancelRef.current?.();
    recoveryAttemptedRef.current = null;
    setIsGenerating(false);
    setDraft('');
    setAttachments([]);
    objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    objectUrlsRef.current = [];
    setConversationState({
      courseId: course.id,
      messages: companionSessions[course.id] ?? initialMessages(course.id, preset.greeting),
    });
  }, [companionSessions, conversationState.courseId, course.id, preset.greeting]);

  useEffect(() => {
    courseDispatch({
      type: 'setCompanionSession',
      courseId: conversationState.courseId,
      messages: conversationState.messages,
    });
  }, [conversationState, courseDispatch]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isGenerating]);

  useEffect(() => () => {
    streamCancelRef.current?.();
    objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const completeAssistant = (assistantId: string, status: Parameters<typeof tutorAnswerFromWorkflowStatus>[0]) => {
    if (status.status !== 'succeeded') {
      setIsGenerating(false);
      updateAssistant(assistantId, (message) => ({
        ...message,
        status: 'error',
        content: status.error?.message ?? `辅导任务终态为 ${status.status}`,
      }));
      return;
    }
    try {
      updateAssistant(assistantId, (message) => ({
        ...message,
        content: tutorAnswerFromWorkflowStatus(status),
        status: 'done',
      }));
    } catch (error) {
      updateAssistant(assistantId, (message) => ({
        ...message,
        status: 'error',
        content: error instanceof Error ? error.message : '辅导结果无法展示，请重试该问题。',
      }));
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    const pending = [...messages].reverse().find((message) => (
      message.role === 'assistant' && message.status === 'generating' && message.workflowRunId
    ));
    if (!pending?.workflowRunId || recoveryAttemptedRef.current === pending.workflowRunId) return undefined;
    recoveryAttemptedRef.current = pending.workflowRunId;
    setIsGenerating(true);
    streamCancelRef.current = resumeCourseTask(
      pending.workflowRunId,
      createCourseTaskLifecycle('ask_tutor', courseDispatch, {
        onWorkflowEvent,
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
          updateAssistant(pending.id, (message) => ({
            ...message,
            evidence: message.evidence.some((item) => item.chunk_id === chunk.chunk_id)
              ? message.evidence
              : [...message.evidence, chunk],
          }));
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
          onWorkflowTrace(run);
        },
        onWorkflowTerminal(status) {
          completeAssistant(pending.id, status);
        },
        onError(error) {
          if (error.recoverable) return;
          setIsGenerating(false);
          updateAssistant(pending.id, (message) => ({ ...message, status: 'error', content: error.message }));
        },
      }),
    );
    return () => streamCancelRef.current?.();
    // Recovery is keyed to one durable root, not a transient stream event.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseDispatch, evidence, messages, onWorkflowEvent, onWorkflowTrace, traceDispatch]);

  const runImageAnswer = (assistantId: string, imageAttachments: CompanionAttachment[]) => {
    onImageWorkflowRun?.();
    const files = imageAttachments.map((item) => item.file).filter((file): file is File => Boolean(file));
    analyzeImage(files, { courseId: course.id, kpId: course.currentKnowledgePoint })
      .then((task) => {
        if (task.evidence?.length) {
          evidence.pushEvidence(task.evidence);
          updateAssistant(assistantId, (message) => ({ ...message, evidence: task.evidence ?? message.evidence }));
        }
        const content = task.result ?? `截图分析任务已提交，任务编号：${task.task_id}。`;
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({ ...message, content, status: 'done' }));
      })
      .catch((error) => {
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({
          ...message,
          status: 'error',
          content: error instanceof Error ? error.message : '截图分析失败，请稍后重试。',
        }));
      });
  };

  const addAttachments = (files: File[]) => {
    setAttachments((current) => {
      const slots = Math.max(0, 3 - current.length);
      if (!slots) {
        toast.info('最多同时上传 3 张截图');
        return current;
      }
      const nextFiles = files.filter((file) => file.type.startsWith('image/')).slice(0, slots);
      if (nextFiles.length < files.length) toast.info('最多同时上传 3 张截图，已自动保留前 3 张');
      const next = nextFiles.map((file) => {
        const url = URL.createObjectURL(file);
        objectUrlsRef.current.push(url);
        return {
          id: messageId('image'),
          name: file.name || '截图.png',
          type: file.type,
          size: file.size,
          url,
          file,
        };
      });
      return [...current, ...next];
    });
  };

  const removeAttachment = (attachmentId: string) => {
    setAttachments((current) => {
      const target = current.find((item) => item.id === attachmentId);
      if (target) {
        URL.revokeObjectURL(target.url);
        objectUrlsRef.current = objectUrlsRef.current.filter((url) => url !== target.url);
      }
      return current.filter((item) => item.id !== attachmentId);
    });
  };

  const submitQuestion = (rawQuestion: string) => {
    const question = rawQuestion.trim();
    const imageAttachments = attachments;
    if ((!question && imageAttachments.length === 0) || isGenerating) return;
    if (isPreview) {
      setDraft('');
      setAttachments([]);
      updateMessages((current) => [
        ...current,
        { id: messageId('user'), role: 'user', content: question || '查看预置内容', status: 'done', evidence: [], attachments: imageAttachments },
        { id: messageId('assistant'), role: 'assistant', content: '这是只读预置内容预览；课程辅导尚未就绪，因此没有创建工作流、AgentRun 或 Evidence Snapshot。', status: 'done', evidence: [] },
      ]);
      return;
    }
    streamCancelRef.current?.();

    const assistantId = messageId('assistant');
    setDraft('');
    setAttachments([]);
    setIsGenerating(true);
    updateMessages((current) => [
      ...current,
      {
        id: messageId('user'),
        role: 'user',
        content: question || '请分析这几张截图',
        status: 'done',
        evidence: [],
        attachments: imageAttachments,
      },
      { id: assistantId, role: 'assistant', content: '', status: 'generating', evidence: [] },
    ]);

    if (imageAttachments.length > 0) {
      runImageAnswer(assistantId, imageAttachments);
      return;
    }

    streamCancelRef.current = startCourseTask({
      intent: 'ask_tutor',
      context: taskContext,
      payload: { question },
    }, createCourseTaskLifecycle('ask_tutor', courseDispatch, {
      onWorkflowStart(start) {
        onWorkflowStart(start);
        recoveryAttemptedRef.current = start.run_id;
        updateAssistant(assistantId, (message) => ({ ...message, workflowRunId: start.run_id }));
      },
      onWorkflowEvent(event) {
        onWorkflowEvent(event);
      },
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
        updateAssistant(assistantId, (message) => ({
          ...message,
          evidence: message.evidence.some((item) => item.chunk_id === chunk.chunk_id)
            ? message.evidence
            : [...message.evidence, chunk],
        }));
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
        onWorkflowTrace(run);
      },
      onWorkflowTerminal(status) {
        completeAssistant(assistantId, status);
      },
      onError(error) {
        if (error.recoverable) return;
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({
          ...message,
          status: 'error',
          content: error.message || '学习助手暂时无法完成本次回答。',
        }));
      },
    }), { mode: presenterMode ? 'fixture' : 'real' });
  };

  const stop = () => {
    streamCancelRef.current?.();
    setIsGenerating(false);
    updateMessages((current) =>
      current.map((message) =>
        message.status === 'generating'
          ? { ...message, status: 'stopped', content: message.content || '已停止生成。' }
          : message,
      ),
    );
  };

  // 关键：只要用户已经发过任何一条消息（即对话进入正式阶段），就隐藏建议问题。
  const hasUserSent = useMemo(
    () => messages.some((message) => message.role === 'user'),
    [messages],
  );
  const showSuggestions = !hasUserSent && preset.suggestedPrompts.length > 0;

  return (
    <section
      className={cn('flex min-h-[520px] min-w-0 flex-col gap-3', className)}
      aria-label={`${course.title} 学习助手对话区`}
    >
      {/* 低权重 header：assistant 标识 + 当前课程 + 可选「显示编排图」入口 */}
      <header className="flex items-center justify-between gap-3 px-1 sm:px-2">
        <div className="flex min-w-0 items-center gap-2">
          <div
            aria-hidden
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-blue-500/85 to-brand-blue-700 text-white"
          >
            <Bot className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium text-slate-900">学习助手</p>
            <p className="truncate text-[11px] text-slate-500">
              {course.title} · {isPreview ? '预置内容预览（辅导关闭）' : course.currentKnowledgePoint}
            </p>
          </div>
        </div>
        {workflowCollapsed && onShowWorkflow && (
          <button
            type="button"
            onClick={onShowWorkflow}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white/85 px-2 py-1 text-[11px] text-slate-500 transition-colors hover:bg-slate-50 hover:text-brand-blue-700"
            title="显示 9 智能体编排图"
          >
            <PanelRightOpen className="h-3 w-3" />
            显示编排图
          </button>
        )}
      </header>

      <CompanionMessageList ref={scrollRef} messages={messages} />

      {showSuggestions && (
        <div className="mx-auto flex w-full max-w-[760px] flex-wrap gap-1.5 px-1 sm:px-2">
          {preset.suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => submitQuestion(prompt)}
              disabled={isGenerating}
              className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs text-slate-700 shadow-sm transition-colors hover:border-brand-blue-300 hover:bg-brand-blue-50 hover:text-brand-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <div className="mx-auto w-full max-w-[760px] pb-1 pt-1">
        <CompanionComposer
          value={draft}
          placeholder={preset.composerPlaceholder}
          isGenerating={isGenerating}
          contextHint={`正在学习：${course.currentKnowledgePoint}`}
          attachments={attachments}
          onChange={setDraft}
          onSend={() => submitQuestion(draft)}
          onStop={stop}
          onAddFiles={addAttachments}
          onRemoveAttachment={removeAttachment}
        />
      </div>
    </section>
  );
}
