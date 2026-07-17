// Status: real
import { useEffect, useMemo, useRef, useState } from 'react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { getLLMErrorCopy } from '@/app/components/StateView';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { ConversationPane } from '@/app/features/chat/components/ConversationPane';
import type { ChatAgent, ChatMessage, ChatSession } from '@/app/features/chat/types';
import { resumeCourseTask, startCourseTask, tutorAnswerFromWorkflowStatus } from '../api';
import { useCourseDispatch, useCourseState } from '../store';
import { createCourseTaskLifecycle } from '../workflow/courseTaskLifecycle';
import { useSelectedCourse } from '../catalog/useSelectedCourse';
import type { StudentCourseExperienceTutorExchange } from '../studentExperience';
import { useStudentCourseExperience } from '../studentExperienceContext';

const tutorAgent: ChatAgent = {
  id: 'path',
  name: '课程辅导',
  description: '结合当前课程与知识点进行多智能体路由答疑。',
  iconName: 'Compass',
  color: '#003399',
  systemPrompt: '围绕当前知识点给出证据驱动的中文答疑。',
  starterQuestions: [
    '如何为课程作业的排序字段设计服务端白名单？',
    '输出上下文不同，为什么不能只做一次字符串替换？',
    'URL 预览功能应如何检查服务端出站访问边界？',
  ],
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

function tutorFailureMessage(code?: string, fallback?: string): string {
  return getLLMErrorCopy(code, fallback).message;
}

function quickReplyFor(
  exchanges: StudentCourseExperienceTutorExchange[] | undefined,
  question: string,
): StudentCourseExperienceTutorExchange | null {
  const normalized = question.trim();
  if (!normalized) return null;
  return exchanges?.find((exchange) => (
    exchange.quick_reply_available
    && exchange.source_kind === 'curated-demo'
    && exchange.question.trim() === normalized
  )) ?? null;
}

function curatedReplyContent(exchange: StudentCourseExperienceTutorExchange): string {
  const evidence = exchange.evidence_status === 'insufficient'
    ? '当前记录证据不足，因此不扩展为确定性结论或操作细节。'
    : exchange.evidence.length
      ? exchange.evidence.map((item) => `- ${item.label}：${item.excerpt}`).join('\n')
      : '该记录未返回可展示的 Evidence 摘要；不会将其补写为实时检索结果。';
  return [
    '**受控预置课程辅导记录（非本次实时模型回答）**',
    '',
    exchange.concept,
    '',
    `**防御性示例**：${exchange.defensive_example}`,
    '',
    '**Evidence / 来源**',
    evidence,
    '',
    `**下一步**：${exchange.next_step}`,
    '',
    `> ${exchange.source_boundary}`,
  ].join('\n');
}

export function TutorDialog() {
  const { taskContext, tutorSessions } = useCourseState();
  const { course } = useSelectedCourse();
  const { experience } = useStudentCourseExperience();
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
  const [draft, setDraft] = useState(tutorAgent.starterQuestions[0]);
  const [generating, setGenerating] = useState(false);
  const session = sessionState.session;
  const knowledgePointLabel = experience?.tasks.find((task) => task.status === 'active')?.knowledge_point
    ?? experience?.tasks.find((task) => task.status === 'todo')?.knowledge_point
    ?? course?.currentKnowledgePoint
    ?? '当前课程知识点';
  const quickReplies = useMemo(
    () => experience?.tutor_exchanges.filter((exchange) => (
      exchange.quick_reply_available && exchange.source_kind === 'curated-demo'
    )) ?? [],
    [experience?.tutor_exchanges],
  );
  const scopedTutorAgent = useMemo<ChatAgent>(() => ({
    ...tutorAgent,
    starterQuestions: quickReplies.length
      ? quickReplies.slice(0, 3).map((exchange) => exchange.question)
      : tutorAgent.starterQuestions,
  }), [quickReplies]);

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
        content: `本次辅导未能完成。${tutorFailureMessage(status.error?.code, status.error?.message)}`,
      });
      return;
    }
    try {
      patchMessage(messageId, { content: tutorAnswerFromWorkflowStatus(status), status: 'done' });
    } catch (error) {
      patchMessage(messageId, {
        status: 'error',
        content: '辅导结果暂时无法展示。请稍后重试该问题，或切换到相关课程资源继续学习。',
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
          patchMessage(pending.id, { status: 'error', content: `辅导连接未能恢复。${tutorFailureMessage(error.code, error.message)}` });
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
    const quickReply = quickReplyFor(experience?.tutor_exchanges, question);
    if (quickReply) {
      const userMessage = createMessage(session.id, 'user', question, 'sent');
      const assistantMessage = createMessage(
        session.id,
        'assistant',
        curatedReplyContent(quickReply),
        'done',
      );
      setDraft('');
      updateSession((current) => ({
        ...current,
        messages: [...current.messages, userMessage, assistantMessage],
        updatedAt: new Date().toISOString(),
      }));
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
            content: `${copy.title}：${copy.message}`,
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
        <span className="ml-2 text-xs text-blue-700">知识点：{knowledgePointLabel}</span>
      </div>
      {quickReplies.length > 0 && !isPreview && (
        <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-700">
          可直接选择受控预置课程辅导记录查看快速回答。它们来自当前 demo 学生的持久化记录，不是本次实时模型回答；其他问题仍会进入 RAG、Evidence 与 QualityCheck 链路。
        </div>
      )}
      <ConversationPane
        agent={scopedTutorAgent}
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
