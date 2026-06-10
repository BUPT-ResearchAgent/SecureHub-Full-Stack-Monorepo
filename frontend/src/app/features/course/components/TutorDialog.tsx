// Status: partial-real
import { useRef, useState } from 'react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { ConversationPane } from '@/app/features/chat/components/ConversationPane';
import type { ChatAgent, ChatMessage, ChatSession } from '@/app/features/chat/types';
import { streamTutorAsk } from '../api';
import { useCourseState } from '../store';

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
    title: 'SQL 注入基础辅导',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    pinned: false,
    archived: false,
    tags: ['课程学习', 'SQL 注入'],
  };
}

export function TutorDialog() {
  const { currentKpId } = useCourseState();
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const cancelRef = useRef<() => void>();
  const [session, setSession] = useState<ChatSession>(() => createSession());
  const [draft, setDraft] = useState('联合查询注入为什么要先判断列数？');
  const [generating, setGenerating] = useState(false);

  const appendToken = (messageId: string, content: string) => {
    setSession((current) => ({
      ...current,
      updatedAt: new Date().toISOString(),
      messages: current.messages.map((message) => (
        message.id === messageId ? { ...message, content: `${message.content}${content}` } : message
      )),
    }));
  };

  const patchMessage = (messageId: string, patch: Partial<ChatMessage>) => {
    setSession((current) => ({
      ...current,
      updatedAt: new Date().toISOString(),
      messages: current.messages.map((message) => (message.id === messageId ? { ...message, ...patch } : message)),
    }));
  };

  const send = (questionOverride?: string) => {
    const question = (questionOverride ?? draft).trim();
    if (!question || generating) return;
    cancelRef.current?.();
    const userMessage = createMessage(session.id, 'user', question, 'sent');
    const assistantMessage = createMessage(session.id, 'assistant', '', 'generating');
    setDraft('');
    setGenerating(true);
    setSession((current) => ({
      ...current,
      messages: [...current.messages, userMessage, assistantMessage],
      updatedAt: new Date().toISOString(),
    }));

    cancelRef.current = streamTutorAsk(
      '00000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000101',
      question,
      currentKpId,
      {
        onToken(token) {
          appendToken(assistantMessage.id, token.content);
        },
        onEvidence(chunk) {
          evidence.pushEvidence([chunk]);
        },
        onTrace(run) {
          traceDispatch({ type: 'upsertRun', run });
        },
        onDone() {
          setGenerating(false);
          patchMessage(assistantMessage.id, { status: 'done' });
        },
        onError(error) {
          setGenerating(false);
          patchMessage(assistantMessage.id, {
            status: 'error',
            content: error.code === 'InsufficientEvidence' ? '证据不足，请切换知识点或补充资料后重试。' : error.message,
          });
        },
      },
    );
  };

  const resetSession = () => {
    cancelRef.current?.();
    setGenerating(false);
    setSession(createSession());
  };

  const retry = (message: ChatMessage) => {
    const index = session.messages.findIndex((item) => item.id === message.id);
    const previous = session.messages.slice(0, index).reverse().find((item) => item.role === 'user');
    if (previous) send(previous.content);
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        当前学习：SQL 注入基础
        <span className="ml-2 text-xs text-blue-700">知识点 ID：{currentKpId}</span>
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
