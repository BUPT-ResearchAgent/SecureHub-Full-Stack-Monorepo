// Status: real
import { useEffect, useRef, useState } from 'react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { getLLMErrorCopy } from '@/app/components/StateView';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { ConversationPane } from '@/app/features/chat/components/ConversationPane';
import type { ChatAgent, ChatMessage, ChatSession } from '@/app/features/chat/types';
import { resumeCourseTask, startCourseTask, tutorAnswerFromWorkflowStatus } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';
import { useSelectedCourse } from '../catalog/useSelectedCourse';

const tutorAgent: ChatAgent = {
  id: 'path',
  name: '课程辅导',
  description: '结合当前课程与知识点进行多智能体路由答疑。',
  iconName: 'Compass',
  color: '#003399',
  systemPrompt: '围绕当前知识点给出证据驱动的中文答疑。',
  starterQuestions: ['联合查询注入为什么要先判断列数？', '参数化查询和过滤输入有什么区别？', '如何判断当前页面有没有 SQL 注入风险？'],
  outputStyle: 'path',
  capabilities: ['课程上下文', '证据引用', '多智能体路由'],
};

function createMessage(sessionId: string, role: ChatMessage['role'], content: string, status: ChatMessage['status']): ChatMessage {
  return {
    id: `course-chat-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    sessionId,
    role,
    content,
    status,
    createdAt: new Date().toISOString(),
    citations: [],
    actions: [],
    structuredCards: [],
  };
}

function createSession(): ChatSession {
  const id = `course-session-${Date.now()}`;
  return {
    id,
    agentId: 'path',
    title: '课程学习辅导',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    pinned: false,
    archived: false,
    tags: ['课程学习'],
  };
}

export function TutorDialog() {
  const { taskContext, tutorSessions } = useCourseState();
  const { course } = useSelectedCourse();
  const isPreview = course?.contentStatus === 'preview';
  const courseDispatch = useCourseDispatch();
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const cancelRef = useRef<() => void>();
  const recoveryAttemptedRef = useRef<string | null>(null);
  const [sessionState, setSessionState] = useState(() => ({
    courseId: taskContext.courseId,
    session: tutorSessions[taskContext.courseId] ?? createSession(),
  }));
  const [draft, setDraft] = useState('联合查询注入为什么要先判断列数？');
  const [generating, setGenerating] = useState(false);
  const session = sessionState.session;

  useEffect(() => {
    if (sessionState.courseId === taskContext.courseId) return;
    recoveryAttemptedRef.current = null;
    setGenerating(false);
    setSessionState({
      courseId: taskContext.courseId,
      session: tutorSessions[taskContext.courseId] ?? createSession(),
    });
  }, [sessionState.courseId, taskContext.courseId, tutorSessions]);

  useEffect(() => {
    courseDispatch({
      type: 'setTutorSession',
      courseId: sessionState.courseId,
      session: sessionState.session,
    });
  }, [courseDispatch, sessionState]);

  const updateSession = (update: (current: ChatSession) => ChatSession) => {
    setSessionState((current) => ({ ...current, session: update(current.session) }));
  };

  const patchMessage = (messageId: string, patch: Partial<ChatMessage>) => {
    updateSession((current) => ({
      ...current,
      updatedAt: new Date().toISOString(),
      messages: current.messages.map((message) => (message.id === messageId ? { ...message, ...patch } : message)),
    }));
  };

  const completeAssistant = (messageId: string, status: Parameters<typeof tutorAnswerFromWorkflowStatus>[0]) => {
    if (status.status !== 'succeeded') {
      setGenerating(false);
      patchMessage(messageId, {
        status: 'error',
        content: status.error?.message ?? `辅导任务终态为 ${status.status}`,
      });
      return;
    }
    try {
      patchMessage(messageId, { content: tutorAnswerFromWorkflowStatus(status), status: 'done' });
    } catch (error) {
      patchMessage(messageId, {
        status: 'error',
        content: error instanceof Error ? error.message : '辅导结果无法展示，请重试该问题。',
      });
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    const pending = [...session.messages].reverse().find((message) => (
      message.role === 'assistant' && message.status === 'generating' && message.workflowRunId
    ));
    if (!pending?.workflowRunId || recoveryAttemptedRef.current === pending.workflowRunId) return undefined;
    recoveryAttemptedRef.current = pending.workflowRunId;
    setGenerating(true);
    cancelRef.current = resumeCourseTask(
      pending.workflowRunId,
      createCourseTaskLifecycle('ask_tutor', courseDispatch, {
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onWorkflowTerminal(status) {
          completeAssistant(pending.id, status);
        },
        onError(error) {
          if (error.recoverable) return;
          setGenerating(false);
          patchMessage(pending.id, { status: 'error', content: error.message });
        },
      }),
    );
    return () => cancelRef.current?.();
    // Recovery is intentionally keyed by its durable message root, not token events.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseDispatch, evidence, session.messages, traceDispatch]);

  const send = (questionOverride?: string) => {
    const question = (questionOverride ?? draft).trim();
    if (!question || generating) return;
    if (isPreview) {
      const userMessage = createMessage(session.id, 'user', question, 'sent');
      const notice = createMessage(session.id, 'assistant', '当前课程仅开放预置内容预览，辅导工作流尚未就绪，因此不会创建运行记录或调用模型。', 'done');
      setDraft('');
      updateSession((current) => ({ ...current, messages: [...current.messages, userMessage, notice], updatedAt: new Date().toISOString() }));
      return;
    }
    cancelRef.current?.();
    const userMessage = createMessage(session.id, 'user', question, 'sent');
    const assistantMessage = createMessage(session.id, 'assistant', '', 'generating');
    setDraft('');
    setGenerating(true);
    updateSession((current) => ({
      ...current,
      messages: [...current.messages, userMessage, assistantMessage],
      updatedAt: new Date().toISOString(),
    }));

    cancelRef.current = startCourseTask({
      intent: 'ask_tutor',
      context: taskContext,
      payload: { question },
    }, createCourseTaskLifecycle('ask_tutor', courseDispatch, {
        onWorkflowStart(start) {
          recoveryAttemptedRef.current = start.run_id;
          patchMessage(assistantMessage.id, { workflowRunId: start.run_id });
        },
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onWorkflowTerminal(status) {
          completeAssistant(assistantMessage.id, status);
        },
        onError(error) {
          if (error.code === 'sse_reconnecting') {
            return;
          }
          setGenerating(false);
          const copy = getLLMErrorCopy(error.code, error.message);
          patchMessage(assistantMessage.id, {
            status: 'error',
            content: `${copy.title}：${error.message || copy.message}`,
          });
        },
    }));
  };

  const resetSession = () => {
    cancelRef.current?.();
    setGenerating(false);
    recoveryAttemptedRef.current = null;
    updateSession(() => createSession());
  };

  const retry = (message: ChatMessage) => {
    const index = session.messages.findIndex((item) => item.id === message.id);
    const previous = session.messages.slice(0, index).reverse().find((item) => item.role === 'user');
    if (previous) send(previous.content);
  };

  return (
    <div className="space-y-4">
      <div className={`rounded-xl px-4 py-3 text-sm ${isPreview ? 'border border-amber-200 bg-amber-50 text-amber-900' : 'border border-blue-100 bg-blue-50 text-blue-900'}`}>
        当前学习：{isPreview ? '预置内容预览（辅导不可用）' : '当前课程知识点'}
        <span className="ml-2 text-xs text-blue-700">知识点 ID：{taskContext.kpId}</span>
      </div>
      <ConversationPane
        agent={tutorAgent}
        session={session}
        draft={draft}
        isGenerating={generating}
        onCreateSession={resetSession}
        onDraftChange={setDraft}
        onSend={send}
        onStop={() => {
          cancelRef.current?.();
          setGenerating(false);
          const pending = [...session.messages].reverse().find((message) => message.status === 'generating');
          if (pending) patchMessage(pending.id, { status: 'stopped', content: pending.content || '已停止查看本次回答。' });
        }}
        onRetry={retry}
        onRegenerate={retry}
        onToggleFavorite={() => undefined}
        onHelpful={() => undefined}
        onInsertToWriting={() => undefined}
        onAddToTask={() => undefined}
        onMockLink={() => undefined}
      />
    </div>
  );
}
