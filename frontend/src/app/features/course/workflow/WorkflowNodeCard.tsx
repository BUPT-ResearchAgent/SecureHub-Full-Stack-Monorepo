import { Handle, Position, type NodeProps } from 'reactflow';
import { CheckCircle2, Clock3, CircleDashed, Loader2, SkipForward, XCircle } from 'lucide-react';
import type { AgentMeta, NodeStatus, WorkflowNode, WorkflowNodeRun } from './types';

export type WorkflowNodeData = {
  node: WorkflowNode;
  run: WorkflowNodeRun;
  meta: AgentMeta;
};

const statusLabel: Record<NodeStatus, string> = {
  idle: '空闲',
  queued: '排队',
  running: '运行中',
  success: '完成',
  failed: '失败',
  skipped: '跳过',
};

const statusClasses: Record<NodeStatus, string> = {
  idle: 'border-slate-200 bg-white text-slate-600',
  queued: 'border-sky-200 bg-sky-50 text-sky-700',
  running: 'workflow-node-running border-brand-blue-600 bg-white text-brand-blue-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
  skipped: 'border-amber-200 bg-amber-50 text-amber-700',
};

const statusDotClasses: Record<NodeStatus, string> = {
  idle: 'bg-slate-400',
  queued: 'bg-sky-400',
  running: 'bg-brand-blue-600',
  success: 'bg-emerald-500',
  failed: 'bg-red-500',
  skipped: 'bg-amber-500',
};

function StatusIcon({ status }: { status: NodeStatus }) {
  if (status === 'running') return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  if (status === 'success') return <CheckCircle2 className="h-3.5 w-3.5" />;
  if (status === 'failed') return <XCircle className="h-3.5 w-3.5" />;
  if (status === 'queued') return <Clock3 className="h-3.5 w-3.5" />;
  if (status === 'skipped') return <SkipForward className="h-3.5 w-3.5" />;
  return <CircleDashed className="h-3.5 w-3.5" />;
}

export function WorkflowNodeCard({ data, selected }: NodeProps<WorkflowNodeData>) {
  const { node, run, meta } = data;
  const status = run.status;

  return (
    <div
      className={`relative h-[86px] w-[172px] rounded-lg border px-3 py-2 shadow-sm transition-all ${statusClasses[status]} ${
        selected ? 'ring-2 ring-brand-blue-600/25' : ''
      }`}
    >
      <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !border-white !bg-slate-400" />
      <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !border-white !bg-brand-blue-600" />

      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className={`h-2.5 w-2.5 rounded-full ${statusDotClasses[status]}`} />
          <span className="truncate text-xs font-semibold text-slate-900">{node.label}</span>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
          <StatusIcon status={status} />
          {statusLabel[status]}
        </span>
      </div>

      <div className="mt-2 truncate rounded-md bg-white/70 px-2 py-1 text-[11px] font-medium text-slate-700">
        {run.skillId ?? node.skillId ?? '等待调度'}
      </div>

      <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-slate-500">
        <span>{run.durationMs ? `${(run.durationMs / 1000).toFixed(1)} 秒` : meta.shortLabel}</span>
        <span>{run.qualityScore == null ? '质量待评估' : `质量 ${Math.round(run.qualityScore * 100)}%`}</span>
      </div>
    </div>
  );
}
