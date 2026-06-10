import { useEffect, useRef, useState } from 'react';
import { MessageSquareText, Send } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { ErrorState, InsufficientEvidenceState, LoadingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { streamPersonaChat } from '../api';
import { mockPersona } from '../mockData';
import { useCourseDispatch } from '../store';

export interface PersonaBuilderProps {
  userId?: string;
}

type DialogueTurn = {
  role: 'user' | 'assistant';
  content: string;
};

const dimensionLabels: Record<string, string> = {
  base_knowledge: '基础水平',
  cognitive_style: '认知方式',
  weak_points: '薄弱点',
  preferred_modality: '偏好资源',
  time_budget: '时间预算',
  target_direction: '目标方向',
  motivation: '学习动机',
};

export function PersonaBuilder({ userId = mockPersona.userId }: PersonaBuilderProps) {
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const courseDispatch = useCourseDispatch();
  const cancelRef = useRef<() => void>();
  const [input, setInput] = useState('我学过一点 Python，想入门 Web 安全');
  const [turns, setTurns] = useState<DialogueTurn[]>([
    { role: 'assistant', content: '我会通过几轮对话确认你的基础、目标和学习偏好，再启动个性化学习路径。' },
  ]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<{ code?: string; message: string }>();

  useEffect(() => () => cancelRef.current?.(), []);

  const submit = () => {
    const message = input.trim();
    if (!message || streaming) return;
    setInput('');
    setError(undefined);
    setStreaming(true);
    setTurns((current) => [...current, { role: 'user', content: message }, { role: 'assistant', content: '' }]);

    cancelRef.current?.();
    cancelRef.current = streamPersonaChat(userId, message, [], {
      onToken(token) {
        setTurns((current) => current.map((turn, index) => (
          index === current.length - 1 ? { ...turn, content: `${turn.content}${token.content}` } : turn
        )));
      },
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
      },
      onDone() {
        setStreaming(false);
        courseDispatch({ type: 'setPersona', persona: { ...mockPersona, updatedAt: new Date().toISOString() } });
      },
      onError(event) {
        setStreaming(false);
        setError({ code: event.code, message: event.message });
      },
    });
  };

  const dimensions = Object.entries(mockPersona.dimensions);
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
      <Card title="画像对话" subtitle={`用户：${userId}`}>
        <div className="space-y-3">
          <div className="max-h-72 space-y-3 overflow-y-auto rounded-lg bg-slate-50 p-3">
            {turns.map((turn, index) => (
              <div
                key={`${turn.role}-${index}`}
                className={`rounded-lg p-3 text-sm leading-6 ${
                  turn.role === 'user' ? 'bg-white text-slate-700' : 'bg-blue-50 text-blue-900'
                }`}
              >
                {turn.role === 'assistant' && <MessageSquareText className="mr-2 inline h-4 w-4" />}
                {turn.content || '正在组织问题…'}
              </div>
            ))}
          </div>

          {streaming && <LoadingState text="画像智能体正在追问…" />}
          {error?.code === 'InsufficientEvidence' && <InsufficientEvidenceState onRetry={submit} />}
          {error && error.code !== 'InsufficientEvidence' && <ErrorState message={error.message} onRetry={submit} />}

          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
              placeholder="补充你的基础、目标或学习偏好"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') submit();
              }}
            />
            <button
              type="button"
              onClick={submit}
              disabled={streaming}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-[#003399] text-white disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="发送画像对话"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Card>
      <Card title="画像维度" subtitle="来自 user_profiles 的 6+ 维画像">
        <div className="grid gap-2">
          {dimensions.map(([key, value]) => (
            <div key={key} className="flex items-start justify-between gap-3 rounded-md border border-slate-100 p-2">
              <Tag tone="blue">{dimensionLabels[key] ?? key}</Tag>
              <span className="text-right text-sm text-slate-600">{value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
