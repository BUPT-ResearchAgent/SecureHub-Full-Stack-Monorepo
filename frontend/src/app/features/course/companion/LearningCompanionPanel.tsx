import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, PanelRightOpen } from 'lucide-react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { cn } from '@/app/components/ui/utils';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { isMockMode } from '@/lib/mock';
import { mockEvidenceChunks } from '@/lib/mock/evidence.mock';
import type { AgentRunDTO } from '@/lib/sse.types';
import type { CourseCatalogItem } from '../catalog/courseCatalog.types';
import { streamPersonaChat } from '../api';
import { CompanionComposer } from './CompanionComposer';
import { CompanionMessageList, type CompanionMessage } from './CompanionMessageList';
import { getCompanionPreset } from './companionPresets';

const userId = '00000000-0000-0000-0000-000000000001';

function messageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function splitTokens(content: string): string[] {
  const size = Math.max(1, Math.ceil(content.length / 72));
  return Array.from({ length: Math.ceil(content.length / size) }, (_, index) =>
    content.slice(index * size, (index + 1) * size),
  );
}

export function LearningCompanionPanel({
  course,
  onMockWorkflowRun,
  onExternalWorkflowBegin,
  onWorkflowTrace,
  onShowWorkflow,
  workflowCollapsed,
  className,
}: {
  course: CourseCatalogItem;
  onMockWorkflowRun: () => void;
  onExternalWorkflowBegin: () => void;
  onWorkflowTrace: (run: AgentRunDTO) => void;
  /** Chat-first：右侧编排图折叠时，header 显示「显示编排图」入口。 */
  onShowWorkflow?: () => void;
  workflowCollapsed?: boolean;
  className?: string;
}) {
  const preset = useMemo(() => getCompanionPreset(course), [course]);
  const [draft, setDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const streamCancelRef = useRef<(() => void) | undefined>();
  const timersRef = useRef<number[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<CompanionMessage[]>(() => [
    {
      id: 'assistant-intro',
      role: 'assistant',
      content: preset.greeting,
      status: 'done',
      evidence: [],
    },
  ]);

  // 课程切换：重置消息流 + 清理已排程的 mock 步骤。
  useEffect(() => {
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    setIsGenerating(false);
    setDraft('');
    setMessages([
      {
        id: `assistant-intro-${course.id}`,
        role: 'assistant',
        content: preset.greeting,
        status: 'done',
        evidence: [],
      },
    ]);
  }, [course.id, preset.greeting]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isGenerating]);

  useEffect(
    () => () => {
      streamCancelRef.current?.();
      timersRef.current.forEach((timer) => window.clearTimeout(timer));
    },
    [],
  );

  const updateAssistant = (
    assistantId: string,
    update: (message: CompanionMessage) => CompanionMessage,
  ) => {
    setMessages((current) =>
      current.map((message) => (message.id === assistantId ? update(message) : message)),
    );
  };

  const runMockAnswer = (assistantId: string) => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    onMockWorkflowRun();

    const evidenceTimer = window.setTimeout(() => {
      evidence.pushEvidence(mockEvidenceChunks);
      updateAssistant(assistantId, (message) => ({ ...message, evidence: mockEvidenceChunks }));
    }, 1400);
    timersRef.current.push(evidenceTimer);

    const tokens = splitTokens(preset.mockAnswer);
    tokens.forEach((token, index) => {
      const timer = window.setTimeout(() => {
        updateAssistant(assistantId, (message) => ({
          ...message,
          content: `${message.content}${token}`,
          status: index === tokens.length - 1 ? 'done' : 'generating',
        }));
        if (index === tokens.length - 1) setIsGenerating(false);
      }, 1900 + index * 140);
      timersRef.current.push(timer);
    });
  };

  const submitQuestion = (rawQuestion: string) => {
    const question = rawQuestion.trim();
    if (!question || isGenerating) return;
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];

    const assistantId = messageId('assistant');
    setDraft('');
    setIsGenerating(true);
    setMessages((current) => [
      ...current,
      { id: messageId('user'), role: 'user', content: question, status: 'done', evidence: [] },
      { id: assistantId, role: 'assistant', content: '', status: 'generating', evidence: [] },
    ]);

    if (isMockMode()) {
      runMockAnswer(assistantId);
      return;
    }

    onExternalWorkflowBegin();
    streamCancelRef.current = streamPersonaChat(userId, question, [], {
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
        updateAssistant(assistantId, (message) => ({
          ...message,
          evidence: message.evidence.some((item) => item.chunk_id === chunk.chunk_id)
            ? message.evidence
            : [...message.evidence, chunk],
        }));
      },
      onToken(token) {
        updateAssistant(assistantId, (message) => ({
          ...message,
          content: `${message.content}${token.content}`,
        }));
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
        onWorkflowTrace(run);
      },
      onDone() {
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({ ...message, status: 'done' }));
      },
      onError(error) {
        setIsGenerating(false);
        updateAssistant(assistantId, (message) => ({
          ...message,
          status: 'error',
          content: error.message || '学习助手暂时无法完成本次回答。',
        }));
      },
    });
  };

  const stop = () => {
    streamCancelRef.current?.();
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
    setIsGenerating(false);
    setMessages((current) =>
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
              {course.title} · {course.currentKnowledgePoint}
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
          onChange={setDraft}
          onSend={() => submitQuestion(draft)}
          onStop={stop}
        />
      </div>
    </section>
  );
}
