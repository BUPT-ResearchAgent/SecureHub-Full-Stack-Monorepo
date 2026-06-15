// Status: partial-real
// 4-B-3 升级：在原有"画像对话 + 六维卡片"基础上叠加：
//   1) PersonaTreeCanvas — 径向画像树（替代静态卡片视觉）
//   2) PersonaNarrative — 80-120 字人物简介，关键词高亮
//   3) PersonaChallenger — 学生自陈触发挑战问题（mock：在 mock 模式下学生第一轮回答后自动触发一次）
//   4) PersonaDimensionDrawer — 点击树节点查看证据片段
//   5) 维度置信度由 challenge 结果驱动（accepted +0.2 / rejected -0.3）

import { useEffect, useMemo, useRef, useState } from 'react';
import { ShieldCheck, MessageSquareText, Send } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { ErrorState, InsufficientEvidenceState, LoadingState, ReconnectingState } from '@/app/components/StateView';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { useAgentTraceDispatch } from '@/app/features/agents/store';
import { isMockMode } from '@/lib/mock';
import { streamPersonaChat } from '../api';
import { mockPersona } from '../mockData';
import { useCourseDispatch } from '../store';
import type { LearningPersona, PersonaDimensionKey } from '../types';
import { PersonaTreeCanvas } from '../persona/PersonaTreeCanvas';
import { PersonaNarrative } from '../persona/PersonaNarrative';
import { PersonaDimensionDrawer } from '../persona/PersonaDimensionDrawer';
import {
  pickChallengeForClaim,
  evaluateChallengeAnswer,
} from '../persona/PersonaChallenger';
import {
  buildPersonaTree,
  generatePersonaNarrative,
  personaDimensionLabels,
} from '@/lib/mock/persona.mock';
import type {
  PersonaChallengeQuestion,
  PersonaDimensionNode,
} from '@/lib/types/persona.types';

export interface PersonaBuilderProps {
  userId?: string;
}

type DialogueTurn = {
  id: string;
  role: 'user' | 'assistant' | 'challenge' | 'challenge-answer' | 'challenge-result';
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
  id: 'turn-init',
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
  const [verifyStatus, setVerifyStatus] = useState<Record<string, 'verified' | 'challenged'>>({});
  const [challengeQueue, setChallengeQueue] = useState<PersonaChallengeQuestion[]>([]);
  const [activeChallenge, setActiveChallenge] = useState<PersonaChallengeQuestion | null>(null);
  const [challengeAnswer, setChallengeAnswer] = useState('');
  const [selectedNode, setSelectedNode] = useState<PersonaDimensionNode | undefined>();
  const [recentlyUpdated, setRecentlyUpdated] = useState<string | undefined>();
  const mockMode = isMockMode();

  useEffect(() => () => cancelRef.current?.(), []);

  useEffect(() => {
    if (!mockMode) return;

    const timers: number[] = [];
    setTurns([initialTurn]);
    setIdentified({});
    setVerifyStatus({});
    setError(undefined);

    mockRounds.forEach((round, index) => {
      const timer = window.setTimeout(() => {
        setTurns((current) => [
          ...current,
          { id: `turn-user-${index}`, role: 'user', content: round.user },
          { id: `turn-bot-${index}`, role: 'assistant', content: round.assistant },
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
        if (index === 0) {
          const claim = round.user;
          const pick = pickChallengeForClaim(claim);
          if (pick) {
            setChallengeQueue((current) => [...current, pick]);
          }
        }
      }, 700 + index * 1200);
      timers.push(timer);
    });

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [courseDispatch, mockMode, userId]);

  useEffect(() => {
    if (activeChallenge || challengeQueue.length === 0) return;
    const [next, ...rest] = challengeQueue;
    setActiveChallenge(next);
    setChallengeQueue(rest);
    setTurns((current) => [
      ...current,
      {
        id: `challenge-${next.id}`,
        role: 'challenge',
        content: `我用一道挑战题确认一下：${next.prompt}`,
      },
    ]);
  }, [activeChallenge, challengeQueue]);

  const identifiedCount = useMemo(
    () => requiredDimensions.filter((key) => Boolean(identified[key])).length,
    [identified],
  );
  const isComplete = identifiedCount >= requiredDimensions.length;

  const branches = useMemo(
    () => buildPersonaTree(identified, verifyStatus),
    [identified, verifyStatus],
  );

  const narrative = useMemo(
    () => generatePersonaNarrative('小李同学', identified),
    [identified],
  );

  const conversationLookup = useMemo(() => {
    const lookup: Record<string, string> = {};
    turns.forEach((turn) => {
      const value = identified;
      Object.keys(value).forEach((dim) => {
        lookup[`msg-${dim}-root`] = turn.role === 'user' ? turn.content : lookup[`msg-${dim}-root`] ?? turn.content;
      });
    });
    return lookup;
  }, [turns, identified]);

  const submit = () => {
    const message = input.trim();
    if (!message || streaming) return;

    if (activeChallenge) {
      finishChallenge(message);
      return;
    }

    setInput('');
    setError(undefined);
    setStreaming(true);
    setTurns((current) => [
      ...current,
      { id: `live-user-${current.length}`, role: 'user', content: message },
      { id: `live-bot-${current.length}`, role: 'assistant', content: '' },
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
        const pick = pickChallengeForClaim(message);
        if (pick) setChallengeQueue((current) => [...current, pick]);
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

  const finishChallenge = (answer: string) => {
    if (!activeChallenge) return;
    const outcome = evaluateChallengeAnswer(activeChallenge, answer);
    const dim = activeChallenge.dimension;
    setVerifyStatus((current) => ({
      ...current,
      [dim]: outcome.kind === 'accepted' ? 'verified' : outcome.kind === 'rejected' ? 'challenged' : current[dim] ?? 'verified',
    }));
    setRecentlyUpdated(String(dim));
    const summary =
      outcome.kind === 'accepted'
        ? `✅ 命中关键词，维度「${labelOf(dim)}」置信度 +20%，标记为已验证。`
        : outcome.kind === 'partial'
        ? `🟡 回答含部分关键词，维度「${labelOf(dim)}」置信度 +8%，仍需更多证据。`
        : `⚠️ 回答未命中预期关键词，维度「${labelOf(dim)}」回归到初始 30%，等待复核。`;
    setTurns((current) => [
      ...current,
      { id: `challenge-ans-${activeChallenge.id}`, role: 'challenge-answer', content: answer },
      { id: `challenge-res-${activeChallenge.id}`, role: 'challenge-result', content: summary },
    ]);
    setChallengeAnswer('');
    setInput('');
    setActiveChallenge(null);
    window.setTimeout(() => setRecentlyUpdated(undefined), 2400);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(420px,1fr)]">
      <Card title="画像对话" subtitle={`用户：${userId}`}>
        <div className="space-y-4">
          <PersonaNarrative segment={narrative} />

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-900">已识别 {identifiedCount}/6 维</div>
                <div className="mt-1 text-xs text-slate-500">达到 6 维后自动启动个性化学习工作流</div>
              </div>
              <Tag tone={isComplete ? 'green' : 'blue'}>{isComplete ? '画像完整' : '收集中'}</Tag>
            </div>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all ${isComplete ? 'bg-emerald-500' : 'bg-[#003399]'}`}
                style={{ width: `${Math.min(100, (identifiedCount / 6) * 100)}%` }}
              />
            </div>
          </div>

          <div className="max-h-72 space-y-3 overflow-y-auto rounded-lg bg-slate-50 p-3">
            {turns.map((turn) => (
              <div
                key={turn.id}
                className={`rounded-lg p-3 text-sm leading-6 ${turnTone(turn.role)}`}
              >
                {turn.role === 'assistant' && <MessageSquareText className="mr-2 inline h-4 w-4" />}
                {turn.role === 'challenge' && (
                  <span className="mr-2 inline-flex items-center gap-1 rounded-full bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold text-rose-600">
                    <ShieldCheck className="h-3 w-3" />
                    挑战
                  </span>
                )}
                {turn.role === 'challenge-result' && (
                  <span className="mr-2 inline-flex items-center gap-1 rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                    判定
                  </span>
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
              placeholder={activeChallenge ? '请回答挑战问题…' : '补充你的基础、目标或学习偏好'}
              value={activeChallenge ? challengeAnswer : input}
              onChange={(event) =>
                activeChallenge ? setChallengeAnswer(event.target.value) : setInput(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  if (activeChallenge) finishChallenge(challengeAnswer.trim() || '我不太确定');
                  else submit();
                }
              }}
            />
            <button
              type="button"
              onClick={() => (activeChallenge ? finishChallenge(challengeAnswer.trim() || '我不太确定') : submit())}
              disabled={streaming}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-[#003399] text-white disabled:cursor-not-allowed disabled:opacity-60"
              aria-label={activeChallenge ? '提交挑战答案' : '发送画像对话'}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Card>

      <Card title="画像树" subtitle="径向布局 · 节点状态实时随对话刷新">
        <PersonaTreeCanvas
          studentName="小李"
          studentInitial="李"
          branches={branches}
          highlightKey={recentlyUpdated}
          onDimensionClick={(node) => setSelectedNode(node)}
        />
        <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] text-slate-500">
          <LegendDot color="#94a3b8" dashed label="未识别" />
          <LegendDot color="#2563eb" label="已识别（中置信）" />
          <LegendDot color="#10b981" label="已验证（高置信）" />
          <LegendDot color="#ec4899" dashed label="待复核" />
        </div>
      </Card>

      <PersonaDimensionDrawer
        node={selectedNode}
        conversationLookup={conversationLookup}
        onClose={() => setSelectedNode(undefined)}
      />
    </div>
  );
}

function turnTone(role: DialogueTurn['role']): string {
  switch (role) {
    case 'user':
      return 'bg-white text-slate-700 border border-slate-100';
    case 'assistant':
      return 'bg-blue-50 text-blue-900';
    case 'challenge':
      return 'bg-rose-50 text-rose-900 border border-rose-100';
    case 'challenge-answer':
      return 'bg-white text-slate-700 border border-rose-100';
    case 'challenge-result':
      return 'bg-amber-50 text-amber-900 border border-amber-100';
    default:
      return 'bg-white text-slate-700';
  }
}

function labelOf(dim: string): string {
  return (personaDimensionLabels as Record<string, string>)[dim] ?? dim;
}

function LegendDot({ color, dashed, label }: { color: string; dashed?: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block h-3 w-3 rounded-full"
        style={{
          backgroundColor: `${color}33`,
          border: `1.5px ${dashed ? 'dashed' : 'solid'} ${color}`,
        }}
      />
      {label}
    </div>
  );
}
