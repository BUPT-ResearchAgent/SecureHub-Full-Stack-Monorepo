// Status: real
import { useEffect, useRef, useState } from 'react';
import { ExternalLink, RefreshCw, ShieldCheck } from 'lucide-react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { AgentTracePanel } from '@/app/features/agents/components/AgentTracePanel';
import { Progress } from '@/app/components/ui/progress';
import {
  isTerminalWorkflowStatus,
  type WorkflowRunStatusResponse,
  type WorkflowRunViewState,
} from '@/lib/workflow-run.types';
import { createWorkflowRunStateFromStart, WorkflowRunClient, type WorkflowSubscription } from '@/lib/workflow-run-client';
import { startFundRecommendation } from '../api';
import type { FundRecommendationCommand, FundWorkflowRecommendation, FundWorkflowResult } from '../types';
import { StateBlock } from './StateBlock';

type Props = {
  courseContext?: FundRecommendationCommand['course_context'];
};

function decodeResult(status: WorkflowRunStatusResponse): FundWorkflowResult {
  const candidate = status.final_output?.output ?? status.final_output;
  if (!candidate || typeof candidate !== 'object') throw new Error('基金推荐工作流未返回可展示的终态结果。');
  const value = candidate as Record<string, unknown>;
  if (!Array.isArray(value.recommendations)) throw new Error('基金推荐终态缺少推荐列表。');
  const recommendations = value.recommendations.map((item, index) => decodeRecommendation(item, index));
  return {
    recommendations,
    landscape_summary: typeof value.landscape_summary === 'string' ? value.landscape_summary : '',
    profile_dimensions_used: stringList(value.profile_dimensions_used),
    evidence_snapshot_ids: stringList(value.evidence_snapshot_ids),
  };
}

function decodeRecommendation(value: unknown, index: number): FundWorkflowRecommendation {
  if (!value || typeof value !== 'object') throw new Error(`第 ${index + 1} 条基金推荐不是有效对象。`);
  const item = value as Record<string, unknown>;
  const required = ['fund_name', 'source_name', 'source_url', 'deadline', 'level', 'direction', 'reason', 'next_action'] as const;
  for (const key of required) {
    if (typeof item[key] !== 'string' || !item[key].trim()) throw new Error(`第 ${index + 1} 条基金推荐缺少 ${key}。`);
  }
  if (typeof item.fit_score !== 'number' || item.fit_score < 0 || item.fit_score > 1) {
    throw new Error(`第 ${index + 1} 条基金推荐的契合度无效。`);
  }
  return {
    fund_name: item.fund_name as string,
    source_name: item.source_name as string,
    source_url: item.source_url as string,
    deadline: item.deadline as string,
    level: item.level as string,
    direction: item.direction as string,
    fit_score: item.fit_score,
    matched_profile_dimensions: stringList(item.matched_profile_dimensions),
    reason: item.reason as string,
    gaps_or_risks: stringList(item.gaps_or_risks),
    next_action: item.next_action as string,
    evidence_snapshot_ids: stringList(item.evidence_snapshot_ids),
  };
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : [];
}

export function FundRecommendationPanel({ courseContext }: Props) {
  const evidence = useEvidence();
  const subscriptionRef = useRef<WorkflowSubscription>();
  const startInFlightRef = useRef(false);
  const [rootRunId, setRootRunId] = useState<string>();
  const [result, setResult] = useState<FundWorkflowResult>();
  const [view, setView] = useState<WorkflowRunViewState>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const start = async () => {
    // React StrictMode replays the initial effect in development. A product
    // entry must create one durable root, not two concurrent real workflows.
    if (startInFlightRef.current) return;
    startInFlightRef.current = true;
    subscriptionRef.current?.unsubscribe();
    setRootRunId(undefined);
    setLoading(true);
    setError(undefined);
    setResult(undefined);
    setView(undefined);
    try {
      const root = await startFundRecommendation({ course_context: courseContext });
      const client = new WorkflowRunClient();
      const initialState = createWorkflowRunStateFromStart(root);
      setRootRunId(root.run_id);
      subscriptionRef.current = client.subscribe(root.run_id, {
        eventsUrl: root.events_url,
        initialState,
        onState: (next) => {
          setView(next);
          if (isTerminalWorkflowStatus(next.status)) {
            void client.status(root.run_id)
              .then((status) => {
                if (status.status !== 'succeeded') {
                  setError(status.error?.message ?? `推荐任务以 ${status.status} 结束。`);
                  return;
                }
                setResult(decodeResult(status));
              })
              .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '无法读取基金推荐终态。'))
              .finally(() => setLoading(false));
          }
        },
        onError: (reason) => {
          setError(reason.message);
          setLoading(false);
        },
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法创建基金推荐任务。');
      setLoading(false);
    } finally {
      startInFlightRef.current = false;
    }
  };

  useEffect(() => {
    void start();
    return () => subscriptionRef.current?.unsubscribe();
    // A route hand-off creates one independent root on mount. It never uses a
    // course root as input or identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rootEvidence = view ? Object.values(view.evidence) : [];
  const running = loading && Boolean(rootRunId);

  return (
    <div className="space-y-5">
      {loading && !rootRunId && <StateBlock state="loading" message="正在创建真实基金推荐任务…" />}
      {running && <StateBlock state="loading" message="正在从官方来源和个人能力画像生成推荐…" />}
      {error && <StateBlock state="error" message={error} onRetry={() => void start()} />}

      {result && (
        <>
          <section className="border-b border-slate-200 pb-4">
            <div className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
              <div>
                <p className="text-sm font-semibold text-slate-900">已通过 QualityCheck 的可核验推荐</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {result.landscape_summary || '结果基于本次 root 的证据快照、能力画像和官方来源整理。'}
                </p>
                {result.profile_dimensions_used.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">本次排序使用的画像维度：{result.profile_dimensions_used.join('、')}</p>
                )}
              </div>
            </div>
          </section>

          {result.recommendations.length === 0 ? (
            <StateBlock state="empty" message="本次证据未支持形成可推荐的基金机会。" />
          ) : (
            <div className="grid gap-4 xl:grid-cols-3">
              {result.recommendations.map((item) => <RecommendationCard key={`${item.fund_name}-${item.source_url}`} item={item} rootRunId={rootRunId} evidenceCount={rootEvidence.length} onShowEvidence={(trigger) => rootRunId && evidence.showEvidenceForRoot(rootRunId, rootEvidence, trigger)} />)}
            </div>
          )}
        </>
      )}

      {rootRunId && <AgentTracePanel workflow="fund_recommendation_v1" rootRunId={rootRunId} />}

      {rootRunId && !loading && (
        <button
          type="button"
          onClick={() => void start()}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" />
          创建新的推荐任务
        </button>
      )}
    </div>
  );
}

function RecommendationCard({
  item,
  rootRunId,
  evidenceCount,
  onShowEvidence,
}: {
  item: FundWorkflowRecommendation;
  rootRunId?: string;
  evidenceCount: number;
  onShowEvidence: (trigger: HTMLElement) => void;
}) {
  const percent = Math.round(item.fit_score * 100);
  return (
    <article className="flex min-h-[360px] flex-col border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-brand-blue-700">{item.level} · {item.direction}</p>
          <h3 className="mt-1 text-base font-semibold leading-6 text-slate-900">{item.fund_name}</h3>
          <p className="mt-1 text-xs text-slate-500">{item.source_name} · 截止：{item.deadline}</p>
        </div>
        <span className="rounded-md bg-emerald-50 px-2 py-1 text-sm font-semibold text-emerald-700">{percent}%</span>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500"><span>画像契合度</span><span>{percent}%</span></div>
        <Progress value={percent} className="bg-slate-100 [&>div]:bg-brand-blue-600" />
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-700">{item.reason}</p>
      <p className="mt-3 text-xs leading-5 text-slate-500">匹配画像：{item.matched_profile_dimensions.join('、') || '未标注'}</p>
      {item.gaps_or_risks.length > 0 && <p className="mt-2 text-xs leading-5 text-amber-800">差距与风险：{item.gaps_or_risks.join('；')}</p>}
      <p className="mt-2 text-xs leading-5 text-slate-600">下一步：{item.next_action}</p>

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
          <ExternalLink className="h-3.5 w-3.5" />
          打开官方来源
        </a>
        {rootRunId && evidenceCount > 0 && (
          <button type="button" onClick={(event) => onShowEvidence(event.currentTarget)} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
            查看本次证据
          </button>
        )}
      </div>
    </article>
  );
}
