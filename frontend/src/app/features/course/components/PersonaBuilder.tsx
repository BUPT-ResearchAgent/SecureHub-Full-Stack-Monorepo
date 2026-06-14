// Status: partial-real
import { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, MessageSquareText, Send } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { ErrorState, InsufficientEvidenceState, LoadingState, ReconnectingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { isMockMode } from '@/lib/mock';
import { streamPersonaChat } from '../api';
import { mockPersona } from '../mockData';
import { useCourseDispatch } from '../store';
import type { LearningPersona, PersonaDimensionKey } from '../types';

export interface PersonaBuilderProps {
  userId?: string;
}

type DialogueTurn = {
  role: 'user' | 'assistant';
  content: string;
};

const requiredDimensions: PersonaDimensionKey[] = [
  'base_knowledge',
  'cognitive_style',
  'weak_points',
  'preferred_modality',
  'time_budget',
  'target_direction',
];

const dimensionLabels: Record<PersonaDimensionKey, string> = {
  base_knowledge: '知识基础',
  cognitive_style: '认知风格',
  weak_points: '易错点',
  preferred_modality: '偏好学习方式',
  time_budget: '时间预算',
  target_direction: '目标方向',
  motivation: '学习动机',
};

const demoDimensions: Record<PersonaDimensionKey, string> = {
  base_knowledge: '具备 Python 基础，了解 HTTP 请求与表单提交',
  cognitive_style: '先看攻击现象，再用修复案例反推原理',
  weak_points: 'SQL 注入判断流程、布尔盲注与参数化查询边界',
  preferred_modality: '讲解文档、实操靶场、错题回放组合学习',
  time_budget: '每周 6 小时，适合 2 周完成入门闭环',
  target_direction: 'Web 安全基础与竞赛演示能力',
  motivation: '围绕 A3 演示主线完成可验证学习成果',
};

const initialTurn: DialogueTurn = {
  role: 'assistant',
  content: '我会通过几轮对话确认你的基础、目标、薄弱点和学习偏好，再启动个性化学习路径。',
};

const mockRounds: Array<{
  user: string;
  assistant: string;
  dimensions: PersonaDimensionKey[];
}> = [
  {
    user: '我学过 Python，也能看懂简单 HTTP 请求。',
    assistant: '已识别你的知识基础：可以从 Web 请求、数据库查询和参数拼接的关系切入。',
    dimensions: ['base_knowledge'],
  },
  {
    user: '我希望先看案例，再做实操，不想一开始就堆概念。',
    assistant: '已识别认知风格与偏好学习方式：课程会先呈现可观察现象，再安排靶场验证。',
    dimensions: ['cognitive_style', 'preferred_modality'],
  },
  {
    user: '我最容易混淆布尔盲注和时间盲注，每周大概能学 6 小时。',
    assistant: '已识别易错点与时间预算：后续资源会把盲注判断和修复检查拆成短任务。',
    dimensions: ['weak_points', 'time_budget'],
  },
  {
    user: '目标是把 Web 安全基础学到能做比赛演示。',
    assistant: '已识别目标方向。画像已达到 6 维，可以生成 SQL 注入基础的学习路径与资源。',
    dimensions: ['target_direction'],
  },
];

function buildPersona(
  userId: string,
  dimensions: Partial<Record<PersonaDimensionKey, string>>,
): LearningPersona {
  return {
    userId,
    dimensions: { ...demoDimensions, ...dimensions },
    completeness: requiredDimensions.every((key) => dimensions[key]) ? 1 : 0.5,
    updatedAt: new Date().toISOString(),
  };
}

export function PersonaBuilder({ userId = mockPersona.userId }: PersonaBuilderProps) {
  const evidence = useEvidence();
  const traceDispatch = useAgentTraceDispatch();
  const courseDispatch = useCourseDispatch();
  const cancelRef = useRef<() => void>();
  const [input, setInput] = useState('我学过一点 Python，想入门 Web 安全');
  const [turns, setTurns] = useState<DialogueTurn[]>([initialTurn]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<{ code?: string; message: string }>();
  const [identified, setIdentified] = useState<Partial<Record<PersonaDimensionKey, string>>>({});
  const mockMode = isMockMode();

  useEffect(() => () => cancelRef.current?.(), []);

  useEffect(() => {
    if (!mockMode) return;

    const timers: number[] = [];
    setTurns([initialTurn]);
    setIdentified({});
    setError(undefined);

    mockRounds.forEach((round, index) => {
      const timer = window.setTimeout(() => {
        setTurns((current) => [
          ...current,
          { role: 'user', content: round.user },
          { role: 'assistant', content: round.assistant },
        ]);
        setIdentified((current) => {
          const next = { ...current };
          round.dimensions.forEach((key) => {
            next[key] = demoDimensions[key];
          });
          const finished = requiredDimensions.every((key) => next[key]);
          if (finished) {
            courseDispatch({ type: 'setPersona', persona: buildPersona(userId, next) });
          }
          return next;
        });
      }, 700 + index * 1200);
      timers.push(timer);
    });

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [courseDispatch, mockMode, userId]);

  const identifiedCount = useMemo(
    () => requiredDimensions.filter((key) => Boolean(identified[key])).length,
    [identified],
  );
  const isComplete = identifiedCount >= requiredDimensions.length;

  const submit = () => {
    const message = input.trim();
    if (!message || streaming) return;
    setInput('');
    setError(undefined);
    setStreaming(true);
    setTurns((current) => [
      ...current,
      { role: 'user', content: message },
      { role: 'assistant', content: '' },
    ]);

    cancelRef.current?.();
    cancelRef.current = streamPersonaChat(userId, message, [], {
      onToken(token) {
        setTurns((current) =>
          current.map((turn, index) =>
            index === current.length - 1
              ? { ...turn, content: `${turn.content}${token.content}` }
              : turn,
          ),
        );
      },
      onEvidence(chunk) {
        evidence.pushEvidence([chunk]);
      },
      onTrace(run) {
        traceDispatch({ type: 'upsertRun', run });
      },
      onDone() {
        const fullDimensions = requiredDimensions.reduce<Partial<Record<PersonaDimensionKey, string>>>(
          (next, key) => ({ ...next, [key]: demoDimensions[key] }),
          {},
        );
        setIdentified(fullDimensions);
        setStreaming(false);
        courseDispatch({ type: 'setPersona', persona: buildPersona(userId, fullDimensions) });
      },
      onError(event) {
        if (event.code === 'sse_reconnecting') {
          setError({ code: event.code, message: event.message });
          return;
        }
        setStreaming(false);
        setError({ code: event.code, message: event.message });
      },
    });
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)]">
      <Card title="画像对话" subtitle={`用户：${userId}`}>
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  已识别 {identifiedCount}/6 维
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  达到 6 维后自动启动个性化学习工作流
                </div>
              </div>
              <Tag tone={isComplete ? 'green' : 'blue'}>
                {isComplete ? '画像完整' : '收集中'}
              </Tag>
            </div>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all ${
                  isComplete ? 'bg-emerald-500' : 'bg-[#003399]'
                }`}
                style={{ width: `${Math.min(100, (identifiedCount / 6) * 100)}%` }}
              />
            </div>
          </div>

          <div className="max-h-72 space-y-3 overflow-y-auto rounded-lg bg-slate-50 p-3">
            {turns.map((turn, index) => (
              <div
                key={`${turn.role}-${index}`}
                className={`rounded-lg p-3 text-sm leading-6 ${
                  turn.role === 'user'
                    ? 'bg-white text-slate-700'
                    : 'bg-blue-50 text-blue-900'
                }`}
              >
                {turn.role === 'assistant' && (
                  <MessageSquareText className="mr-2 inline h-4 w-4" />
                )}
                {turn.content || '正在组织问题…'}
              </div>
            ))}
          </div>

          {error?.code === 'sse_reconnecting' && <ReconnectingState text={error.message} />}
          {streaming && error?.code !== 'sse_reconnecting' && <LoadingState text="画像智能体正在追问…" />}
          {error?.code === 'InsufficientEvidence' && <InsufficientEvidenceState onRetry={submit} />}
          {error && !['InsufficientEvidence', 'sse_reconnecting'].includes(error.code ?? '') && (
            <ErrorState message={error.message} onRetry={submit} />
          )}

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

      <Card title="六维画像" subtitle="A3 要求：对话式画像构建不少于 6 维">
        <div className="grid gap-3">
          {requiredDimensions.map((key) => {
            const value = identified[key];
            return (
              <div
                key={key}
                className={`rounded-lg border p-3 transition-colors ${
                  value
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-slate-200 bg-slate-50'
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900">
                    {dimensionLabels[key]}
                  </span>
                  {value ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-label="已识别" />
                  ) : (
                    <span className="text-xs text-slate-400">未识别</span>
                  )}
                </div>
                <p className={`text-sm leading-6 ${value ? 'text-slate-700' : 'text-slate-400'}`}>
                  {value || '等待对话补充'}
                </p>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
