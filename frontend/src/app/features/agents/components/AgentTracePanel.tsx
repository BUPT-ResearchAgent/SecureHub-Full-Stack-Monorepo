// Status: real
import { useEffect, useMemo, useState } from 'react';
import {
  BadgeCheck,
  CircleAlert,
  ExternalLink,
  FileOutput,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Square,
} from 'lucide-react';
import { useEvidence } from '@/app/components/EvidenceDrawer';
import { Card } from '@/app/components/PageShell';
import { EmptyState, ErrorState, LoadingState } from '@/app/components/StateView';
import {
  createWorkflowRunViewState,
  type WorkflowRunControlResponse,
  type WorkflowRunStatus,
  type WorkflowRunStatusResponse,
  type WorkflowRunViewState,
} from '@/lib/workflow-run.types';
import { WorkflowRunClient, WorkflowRunClientError } from '@/lib/workflow-run-client';
import { listAgentRuns } from '../api';
import { useAgentTraceDispatch, useAgentTraceState } from '../store';
import { AgentRunRow } from './AgentRunRow';

type RootControl = 'pause' | 'resume' | 'retry' | 'cancel' | 'approve' | 'reject';

function rootStatusLabel(status?: string): string {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '运行中',
    reworking: '正在返工',
    pausing: '正在暂停',
    paused: '已暂停',
    waiting_approval: '等待审批',
    cancelling: '正在取消',
    cancelled: '已取消',
    succeeded: '已完成',
    failed: '执行失败',
    blocked: '已阻断',
    pending: '待执行',
    ready: '就绪',
    skipped: '已跳过',
  };
  return labels[status ?? ''] ?? '未标注';
}

function statusTone(status?: string): string {
  if (status === 'succeeded') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (status === 'failed' || status === 'blocked') return 'border-rose-200 bg-rose-50 text-rose-700';
  if (status === 'cancelled' || status === 'cancelling') return 'border-slate-200 bg-slate-100 text-slate-600';
  if (status === 'waiting_approval' || status === 'paused' || status === 'pausing') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (status === 'running' || status === 'reworking' || status === 'queued') return 'border-blue-200 bg-blue-50 text-blue-700';
  return 'border-slate-200 bg-slate-50 text-slate-600';
}

function formatDuration(value?: number | null): string {
  if (value == null) return '未标注';
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(1)} 秒`;
}

function errorAction(code?: string, status?: string): string {
  const normalized = (code ?? '').toUpperCase();
  if (normalized.includes('INSUFFICIENT_EVIDENCE')) return '补充可引用资料，或缩小问题范围后重新发起。';
  if (normalized.includes('BUDGET')) return '当前额度已受限，请等待额度恢复或联系管理员。';
  if (normalized.includes('PERMISSION') || normalized.includes('AUTH') || normalized.includes('FORBIDDEN')) {
    return '当前账号没有执行该动作的权限，请联系管理员。';
  }
  if (normalized.includes('PROVIDER') || normalized.includes('LLM') || normalized.includes('TIMEOUT')) {
    return '模型服务暂不可用，请稍后使用显式重试。';
  }
  if (normalized.includes('CANCEL') || status === 'cancelled') return '任务已取消，可重新发起该学习任务。';
  if (status === 'blocked' || normalized.includes('BLOCK')) return '任务被阻断，请处理审批或联系管理员。';
  return '请检查任务上下文后重试；问题持续时联系管理员。';
}

function rootStatusFromView(status: WorkflowRunStatusResponse | undefined, view: WorkflowRunViewState): WorkflowRunStatus {
  // `status()` is the initial durable snapshot. Once replay has observed a
  // terminal/root state transition, it is newer than that snapshot and must
  // drive controls and the visible terminal state.
  if (view.terminalEvent || view.status !== 'queued') return view.status;
  return status?.status ?? view.status;
}

function RootLineagePanel({ rootRunId }: { rootRunId: string }) {
  const evidence = useEvidence();
  const [status, setStatus] = useState<WorkflowRunStatusResponse>();
  const [view, setView] = useState<WorkflowRunViewState>(() => createWorkflowRunViewState(rootRunId));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [controlError, setControlError] = useState<string>();
  const [pendingControl, setPendingControl] = useState<RootControl>();
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    const client = new WorkflowRunClient();
    const initialState = createWorkflowRunViewState(rootRunId);
    setView(initialState);
    setStatus(undefined);
    setLoading(true);
    setError(undefined);
    setControlError(undefined);

    void client.status(rootRunId)
      .then((next) => {
        if (!disposed) setStatus(next);
      })
      .catch((reason: unknown) => {
        if (!disposed) setError(reason instanceof Error ? reason.message : '无法读取当前 root 状态');
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });

    // Start from cursor zero deliberately. This replays the durable event log
    // for the selected root and then follows it if it is still non-terminal.
    const subscription = client.subscribe(rootRunId, {
      initialState,
      replayFromStart: true,
      onState: (next) => {
        if (!disposed) setView(next);
      },
      onError: (reason) => {
        if (!disposed) setError(reason.message);
      },
    });

    return () => {
      disposed = true;
      subscription.unsubscribe();
    };
  }, [reloadKey, rootRunId]);

  const rootStatus = rootStatusFromView(status, view);
  const requestedProvider = status?.requested_provider ?? view.requestedProvider;
  const requestedModel = status?.requested_model ?? view.requestedModel;
  const actualProvider = status?.actual_provider ?? view.actualProvider;
  const actualModel = status?.actual_model ?? view.actualModel;
  const traceRows = useMemo(() => Object.values(view.traces), [view.traces]);
  const providerSwitches = useMemo(
    () => traceRows.filter((trace) => Boolean(trace.provider_switch)),
    [traceRows],
  );
  const streamAttempts = useMemo(
    () => [...new Set(Object.values(view.tokenDrafts).map((draft) => draft.streamAttempt).filter((value): value is number => value != null))],
    [view.tokenDrafts],
  );
  const nodes = status?.child_runs ?? [];
  const qualityNodes = nodes.filter((node) => node.agent_name === 'outcome_evaluator' && node.skill_name?.includes('QualityCheck'));
  const evidenceItems = Object.values(view.evidence);
  const artifactItems = Object.values(view.artifacts);
  const mode = status?.mode ?? view.mode;
  const canPause = rootStatus === 'running';
  const canResume = rootStatus === 'paused';
  const canRetry = rootStatus === 'waiting_approval' && view.approvalKind === 'provider_retry';
  const canApprove = rootStatus === 'waiting_approval' && Boolean(view.approvalId) && view.approvalKind !== 'provider_retry';
  const canCancel = ['queued', 'running', 'reworking', 'pausing', 'paused', 'waiting_approval'].includes(rootStatus);

  const refresh = () => setReloadKey((value) => value + 1);
  const runControl = async (control: RootControl) => {
    const client = new WorkflowRunClient();
    setControlError(undefined);
    setPendingControl(control);
    try {
      let response: WorkflowRunControlResponse | undefined;
      if (control === 'pause') response = await client.pause(rootRunId);
      if (control === 'resume') response = await client.resume(rootRunId);
      if (control === 'retry') response = await client.retry(rootRunId);
      if (control === 'cancel') response = await client.cancel(rootRunId);
      if (control === 'approve' && view.approvalId) {
        await client.decideApproval(rootRunId, view.approvalId, true);
      }
      if (control === 'reject' && view.approvalId) {
        await client.decideApproval(rootRunId, view.approvalId, false);
      }
      if (response) setStatus((previous) => (previous ? { ...previous, status: response.status } : previous));
      refresh();
    } catch (reason) {
      const clientError = reason instanceof WorkflowRunClientError ? reason : undefined;
      setControlError(clientError?.message ?? (reason instanceof Error ? reason.message : '任务控制操作失败'));
    } finally {
      setPendingControl(undefined);
    }
  };

  if (loading) return <LoadingState text="正在重建当前 root 的运行链路…" />;
  if (error && !status) return <ErrorState message={error} onRetry={refresh} />;

  return (
    <Card
      title="当前任务运行链路"
      subtitle={mode === 'fixture' ? 'PresenterMode fixture root，不能作为真实运行证据。' : '当前 root 的 durable events、AgentRun 与状态投影'}
      right={
        <button
          type="button"
          onClick={refresh}
          title="重新读取当前 root"
          aria-label="重新读取当前 root"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      }
    >
      <div className="space-y-4">
        <section className="grid gap-3 border-b border-slate-100 pb-4 text-xs sm:grid-cols-2">
          <div>
            <p className="text-slate-500">任务 root</p>
            <p className="mt-1 break-all font-mono text-slate-800">{rootRunId}</p>
          </div>
          <div>
            <p className="text-slate-500">当前状态</p>
            <span className={`mt-1 inline-flex rounded-md border px-2 py-1 font-medium ${statusTone(rootStatus)}`}>
              {rootStatusLabel(rootStatus)}
            </span>
          </div>
          <div>
            <p className="text-slate-500">请求的 Provider / Model</p>
            <p className="mt-1 text-slate-800">{requestedProvider ?? '未标注'} / {requestedModel ?? '未标注'}</p>
          </div>
          <div>
            <p className="text-slate-500">实际 Provider / Model</p>
            <p className="mt-1 text-slate-800">{actualProvider ?? '未标注'} / {actualModel ?? '未标注'}</p>
            <p className="mt-1 text-slate-500">
              {actualProvider === 'deepseek' && providerSwitches.length === 0
                ? '直接 DeepSeek 调用，未发生 replacement。'
                : providerSwitches.length
                  ? `已记录 ${providerSwitches.length} 次 provider replacement。`
                  : '未记录 provider replacement。'}
              {streamAttempts.length ? ` Stream attempt：${streamAttempts.join(', ')}。` : ''}
            </p>
          </div>
        </section>

        <section className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-slate-900">执行谱系</h4>
              <p className="text-xs text-slate-500">root → step attempt → Agent / Skill → Evidence → QualityCheck → Artifact / Action</p>
            </div>
            <span className="text-xs text-slate-500">{nodes.length} 个 step attempt</span>
          </div>
          {nodes.length ? (
            <ol className="space-y-2">
              {nodes.map((node) => (
                <li key={`${node.step_attempt_id ?? node.node_id}-${node.attempt ?? 0}`} className="border-l-2 border-slate-200 pl-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-md border px-1.5 py-0.5 ${statusTone(node.status)}`}>{rootStatusLabel(node.status)}</span>
                    <span className="font-medium text-slate-800">{node.agent_name ?? 'Runtime Action'} · {node.skill_name ?? node.node_id}</span>
                    {node.attempt != null && <span className="text-slate-500">尝试 {node.attempt}</span>}
                    {node.quality_score != null && <span className="text-slate-500">质量 {Math.round(node.quality_score * 100)}%</span>}
                  </div>
                  <p className="mt-1 text-slate-500">耗时 {formatDuration(node.duration_ms)}{node.error_code ? ` · ${node.error_code}` : ''}</p>
                  <details className="mt-1 text-slate-500">
                    <summary className="cursor-pointer">诊断关联</summary>
                    <p className="mt-1 break-all font-mono">step {node.step_attempt_id ?? '未标注'} · AgentRun {node.agent_run_id ?? '未标注'}</p>
                  </details>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState text="该 root 尚未产生 step attempt。" />
          )}
        </section>

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="border border-slate-200 p-3">
            <div className="flex items-center gap-2 text-slate-800"><BadgeCheck className="h-4 w-4 text-emerald-600" />QualityCheck</div>
            {qualityNodes.length ? qualityNodes.map((node) => (
              <p key={`${node.node_id}-${node.attempt ?? 0}`} className="mt-2 text-xs text-slate-600">
                {rootStatusLabel(node.status)}{node.quality_score == null ? '' : ` · ${Math.round(node.quality_score * 100)}%`}
              </p>
            )) : <p className="mt-2 text-xs text-slate-500">当前 root 未记录显式 QualityCheck。</p>}
          </div>
          <div className="border border-slate-200 p-3">
            <div className="flex items-center gap-2 text-slate-800"><FileOutput className="h-4 w-4 text-brand-blue-600" />Artifact / Action</div>
            <p className="mt-2 text-xs text-slate-600">已持久化 {artifactItems.length} 个 Artifact</p>
            {artifactItems.slice(0, 2).map((artifact) => <p key={artifact.resource_id} className="mt-1 truncate text-xs text-slate-500">{artifact.resource_type} · {artifact.title}</p>)}
          </div>
          <div className="border border-slate-200 p-3">
            <div className="flex items-center gap-2 text-slate-800"><ExternalLink className="h-4 w-4 text-amber-600" />Evidence</div>
            <p className="mt-2 text-xs text-slate-600">{evidenceItems.length} 条可追溯来源</p>
            <button
              type="button"
              disabled={!evidenceItems.length}
              onClick={(event) => evidence.showEvidenceForRoot(rootRunId, evidenceItems, event.currentTarget)}
              className="mt-2 text-xs font-medium text-brand-blue-700 hover:text-brand-blue-800 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              查看证据与来源
            </button>
          </div>
        </section>

        {evidenceItems.length > 0 && (
          <details className="border border-slate-200 p-3 text-xs text-slate-600">
            <summary className="cursor-pointer font-medium text-slate-800">证据快照关联</summary>
            <ul className="mt-2 space-y-1">
              {evidenceItems.map((item) => {
                const lineage = view.evidenceLineage[item.chunk_id];
                return <li key={item.chunk_id} className="break-all">{item.title ?? item.chunk_id} · snapshot {lineage?.evidenceSnapshotIds.join(', ') || '未标注'} · step {lineage?.stepAttemptId ?? '未标注'}</li>;
              })}
            </ul>
          </details>
        )}

        {(status?.error || view.error || controlError) && (
          <div className="border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
            <div className="flex items-start gap-2">
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">{controlError ?? status?.error?.message ?? view.error?.message}</p>
                <p className="mt-1 text-xs leading-5">{errorAction(status?.error?.code ?? view.error?.code, rootStatus)}</p>
              </div>
            </div>
          </div>
        )}

        <section className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          {canPause && <ControlButton control="pause" pending={pendingControl} onClick={runControl} icon={<Pause className="h-3.5 w-3.5" />}>暂停</ControlButton>}
          {canResume && <ControlButton control="resume" pending={pendingControl} onClick={runControl} icon={<Play className="h-3.5 w-3.5" />}>恢复</ControlButton>}
          {canRetry && <ControlButton control="retry" pending={pendingControl} onClick={runControl} icon={<RotateCcw className="h-3.5 w-3.5" />}>重试</ControlButton>}
          {canApprove && <ControlButton control="approve" pending={pendingControl} onClick={runControl} icon={<BadgeCheck className="h-3.5 w-3.5" />}>批准</ControlButton>}
          {canApprove && <ControlButton control="reject" pending={pendingControl} onClick={runControl} icon={<Square className="h-3.5 w-3.5" />}>拒绝</ControlButton>}
          {canCancel && <ControlButton control="cancel" pending={pendingControl} onClick={runControl} icon={<Square className="h-3.5 w-3.5" />} danger>取消</ControlButton>}
          {!canPause && !canResume && !canRetry && !canApprove && !canCancel && (
            <p className="text-xs text-slate-500">当前状态没有可执行的任务控制操作。</p>
          )}
        </section>
      </div>
    </Card>
  );
}

function ControlButton({
  control,
  pending,
  onClick,
  icon,
  danger = false,
  children,
}: {
  control: RootControl;
  pending?: RootControl;
  onClick: (control: RootControl) => void;
  icon: React.ReactNode;
  danger?: boolean;
  children: React.ReactNode;
}) {
  const busy = pending === control;
  return (
    <button
      type="button"
      disabled={Boolean(pending)}
      onClick={() => onClick(control)}
      className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-60 ${
        danger ? 'border-rose-200 text-rose-700 hover:bg-rose-50' : 'border-slate-200 text-slate-700 hover:bg-slate-50'
      }`}
    >
      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
      {children}
    </button>
  );
}

function HistoryTracePanel({ workflow, userId }: { workflow: string; userId?: string }) {
  const state = useAgentTraceState();
  const dispatch = useAgentTraceDispatch();
  const averageQuality = useMemo(() => {
    const scoredRuns = state.runs.filter((run) => run.quality_score != null);
    if (!scoredRuns.length) return null;
    return Math.round((scoredRuns.reduce((sum, run) => sum + (run.quality_score ?? 0), 0) / scoredRuns.length) * 100);
  }, [state.runs]);

  useEffect(() => {
    let cancelled = false;
    dispatch({ type: 'setLoading', loading: true });
    listAgentRuns(workflow, userId, 20)
      .then((runs) => {
        if (!cancelled) dispatch({ type: 'replaceRuns', runs });
      })
      .catch((reason) => {
        if (!cancelled) dispatch({ type: 'setError', error: reason instanceof Error ? reason.message : '智能体运行记录加载失败' });
      });
    return () => { cancelled = true; };
  }, [dispatch, userId, workflow]);

  return (
    <Card title="历史智能体运行记录" subtitle="历史列表不与当前 root 的完整谱系混合">
      <div className="space-y-3">
        <div className="border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          平均质量分 <span className="font-semibold text-slate-900">{averageQuality == null ? '待评估' : `${averageQuality}%`}</span>
        </div>
        {state.loading && <LoadingState text="正在加载历史运行记录…" />}
        {state.error && <ErrorState message={state.error} onRetry={() => dispatch({ type: 'setError', error: undefined })} />}
        {!state.loading && !state.error && !state.runs.length && <EmptyState text="暂无历史运行记录" />}
        {state.runs.map((run) => <AgentRunRow key={run.id ?? run.run_id} run={run} />)}
      </div>
    </Card>
  );
}

export function AgentTracePanel({
  workflow = 'course_learning',
  userId,
  rootRunId,
}: {
  workflow?: string;
  userId?: string;
  rootRunId?: string | null;
}) {
  return rootRunId ? <RootLineagePanel rootRunId={rootRunId} /> : <HistoryTracePanel workflow={workflow} userId={userId} />;
}
