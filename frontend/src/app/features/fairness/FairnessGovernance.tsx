// Status: real

import { useCallback, useEffect, useState } from 'react';
import { BarChart3, Loader2, RefreshCw, Scale, ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  fetchBenchmarkDatasets,
  fetchFairnessAppeals,
  fetchFairnessDashboard,
  type BenchmarkDataset,
  type BenchmarkRun,
  type FairnessAppeal,
  type FairnessDashboard,
  resolveFairnessAppeal,
  reviewFairnessAlert,
  runBenchmark,
} from './api';

const runStatusLabel: Record<string, string> = {
  completed: '已完成',
  insufficient_sample: '样本不足',
  rejected: '安全拒绝',
  pending: '待运行',
};

export function FairnessGovernance() {
  const [dashboard, setDashboard] = useState<FairnessDashboard | null>(null);
  const [datasets, setDatasets] = useState<BenchmarkDataset[]>([]);
  const [appeals, setAppeals] = useState<FairnessAppeal[]>([]);
  const [benchmarkRuns, setBenchmarkRuns] = useState<Record<string, BenchmarkRun>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fairness, benchmark, appealResponse] = await Promise.all([
        fetchFairnessDashboard(),
        fetchBenchmarkDatasets(),
        fetchFairnessAppeals(),
      ]);
      setDashboard(fairness);
      setDatasets(benchmark.items);
      setAppeals(appealResponse.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '无法读取公平治理数据');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const reviewAlert = async (alertId: string) => {
    const reason = window.prompt('请输入启动人工复核的理由');
    if (!reason?.trim()) return;
    try {
      await reviewFairnessAlert(alertId, reason.trim());
      toast.success('已转入人工复核；不会自动影响任何个人成绩');
      await load();
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '启动复核失败');
    }
  };

  const resolveAppeal = async (appealId: string) => {
    const response = window.prompt('请输入申诉处理说明');
    if (!response?.trim()) return;
    try {
      await resolveFairnessAppeal(appealId, response.trim());
      toast.success('申诉已记录人工说明；成绩不会被自动重写');
      await load();
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '处理申诉失败');
    }
  };

  const executeBenchmark = async (dataset: BenchmarkDataset) => {
    try {
      const result = await runBenchmark(dataset.id);
      setBenchmarkRuns((current) => ({ ...current, [dataset.id]: result }));
      toast.success(`${dataset.kind} 冻结基准已运行`);
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : '基准运行失败');
    }
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex gap-3">
          <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-amber-300 shadow-sm"><Scale className="h-5 w-5" /></div>
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-amber-700">FAIRNESS GOVERNANCE</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">公平监控与可复现基准</h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">仅展示经同意的聚合指标；样本不足不会给出结论，告警必须人工复核，绝不自动惩罚个人。</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link to="/fairness/appeals" className="inline-flex h-9 items-center rounded-lg border border-slate-300 px-3 text-sm text-slate-700 hover:bg-slate-50">学生申诉入口</Link>
          <button type="button" onClick={() => void load()} aria-label="刷新公平治理数据" title="刷新公平治理数据" className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"><RefreshCw className="h-4 w-4" /></button>
        </div>
      </header>

      {loading ? (
        <div className="flex min-h-72 items-center justify-center text-sm text-slate-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取真实聚合数据</div>
      ) : error ? (
        <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>
      ) : (
        <div className="space-y-8 py-6">
          <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 text-sm leading-6 text-amber-950">
            <div className="flex gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" /><p>{dashboard?.policy_note}</p></div>
          </section>

          <section>
            <div className="flex items-center gap-2"><BarChart3 className="h-4 w-4 text-slate-700" /><h2 className="text-sm font-semibold text-slate-900">版本化公平指标</h2></div>
            <div className="mt-3 space-y-4">
              {dashboard?.items.length ? dashboard.items.map((run) => (
                <article key={run.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-4 py-3">
                    <div><p className="font-medium text-slate-900">{run.policy_version} · {run.formula_version}</p><p className="mt-1 text-xs text-slate-500">样本 {run.sample_size} · 数据指纹 {run.dataset_fingerprint.slice(0, 16)}…</p></div>
                    <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700">{runStatusLabel[run.status] ?? run.status}</span>
                  </div>
                  {run.status === 'completed' ? (
                    <div className="divide-y divide-slate-100">
                      {run.cells.map((cell) => <div key={cell.id} className="grid gap-3 px-4 py-3 sm:grid-cols-[1.1fr_repeat(3,minmax(0,1fr))]">
                        <div><p className="text-sm font-medium text-slate-800">{cell.group_key}: {cell.group_value}</p><p className="mt-1 text-xs text-slate-500">n={cell.sample_size} · {String(cell.confidence_interval.method ?? '95% 不确定性')}</p></div>
                        <Metric label="均值" value={cell.mean_score.toFixed(2)} />
                        <Metric label="通过率" value={`${(cell.pass_rate * 100).toFixed(1)}%`} />
                        <Metric label="限制" value="仅聚合，非因果结论" />
                      </div>)}
                      {run.alerts.map((alert) => <div key={alert.id} className="flex flex-wrap items-center justify-between gap-3 bg-amber-50/40 px-4 py-3"><p className="text-sm text-amber-950">阈值告警：{alert.alert_kind} · {alert.severity}</p><button type="button" onClick={() => void reviewAlert(alert.id)} className="h-8 rounded-lg border border-amber-300 px-2.5 text-xs font-medium text-amber-900 hover:bg-amber-100">人工复核</button></div>)}
                    </div>
                  ) : <div className="px-4 py-4 text-sm text-slate-600">{run.rejection_code ? `${run.rejection_code}：未展示群体结论。` : '当前运行未形成可展示结论。'}</div>}
                </article>
              )) : <p className="rounded-xl border border-dashed border-slate-300 p-7 text-center text-sm text-slate-500">暂无已运行的公平指标。只有已发布成绩、有效同意和最小样本同时满足时才会出现结果。</p>}
            </div>
          </section>

          <section className="grid gap-5 lg:grid-cols-[1.35fr_0.85fr]">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">冻结基准</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">每次运行校验 manifest / 数据哈希；失败样本只保留 case key，绝不把评测样本宣传为用户效果。</p>
              <div className="mt-4 space-y-3">
                {datasets.map((dataset) => {
                  const result = benchmarkRuns[dataset.id];
                  return <div key={dataset.id} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-medium text-slate-800">{dataset.kind} · v{dataset.semantic_version}</p><p className="mt-1 text-xs text-slate-500">{dataset.source_note}</p></div><button type="button" onClick={() => void executeBenchmark(dataset)} className="h-8 rounded-lg border border-slate-300 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">运行</button></div>
                    {result ? <p className="mt-2 text-xs text-slate-600">TP {result.summary.confusion_matrix?.tp ?? 0} · TN {result.summary.confusion_matrix?.tn ?? 0} · FP {result.summary.confusion_matrix?.fp ?? 0} · FN {result.summary.confusion_matrix?.fn ?? 0}</p> : null}
                  </div>;
                })}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">申诉人工处理</h2>
              <div className="mt-3 space-y-3">
                {appeals.length ? appeals.map((appeal) => <div key={appeal.id} className="rounded-lg border border-slate-200 p-3"><p className="text-sm text-slate-800">{appeal.reason}</p><p className="mt-1 text-xs text-slate-500">状态：{appeal.status}</p>{appeal.status === 'submitted' || appeal.status === 'reviewing' ? <button type="button" onClick={() => void resolveAppeal(appeal.id)} className="mt-2 h-8 rounded-lg border border-slate-300 px-2.5 text-xs text-slate-700 hover:bg-slate-50">写入人工说明</button> : <p className="mt-2 text-xs text-slate-500">{appeal.response_note || '已处理'}</p>}</div>) : <p className="text-sm text-slate-500">暂无待处理申诉</p>}
              </div>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold text-slate-800">{value}</p></div>;
}
