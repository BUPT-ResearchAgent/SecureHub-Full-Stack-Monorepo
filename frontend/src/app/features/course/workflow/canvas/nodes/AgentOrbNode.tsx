import { Handle, Position, type NodeProps } from 'reactflow';
import { Check, Loader2, Pause, SkipForward, X } from 'lucide-react';
import type { AgentMeta, NodeStatus, WorkflowNode, WorkflowNodeRun } from '../../types';
import { ORB_DIAMETER, ORB_DIAMETER_COMPACT } from '../layout';

export type AgentOrbNodeData = {
  node: WorkflowNode;
  run: WorkflowNodeRun;
  meta: AgentMeta;
  compact?: boolean;
};

const ringStyle: Record<NodeStatus, { ring: string; fill: string; text: string; subtle: string }> = {
  idle: {
    ring: 'ring-1 ring-slate-200',
    fill: 'bg-white',
    text: 'text-slate-700',
    subtle: 'text-slate-400',
  },
  queued: {
    ring: 'ring-1 ring-sky-300',
    fill: 'bg-sky-50',
    text: 'text-sky-700',
    subtle: 'text-sky-500',
  },
  running: {
    ring: 'ring-2 ring-brand-blue-500 workflow-orb-running',
    fill: 'bg-white',
    text: 'text-brand-blue-700',
    subtle: 'text-brand-blue-500',
  },
  success: {
    ring: 'ring-2 ring-emerald-400/80',
    fill: 'bg-emerald-50',
    text: 'text-emerald-700',
    subtle: 'text-emerald-600',
  },
  failed: {
    ring: 'ring-2 ring-red-400/80',
    fill: 'bg-red-50',
    text: 'text-red-700',
    subtle: 'text-red-500',
  },
  skipped: {
    ring: 'ring-1 ring-amber-300/80',
    fill: 'bg-amber-50/60',
    text: 'text-amber-700',
    subtle: 'text-amber-500',
  },
};

const statusLabel: Record<NodeStatus, string> = {
  idle: '空闲',
  queued: '排队',
  running: '运行中',
  success: '完成',
  failed: '失败',
  skipped: '跳过',
};

function StatusIcon({ status, size = 'sm' }: { status: NodeStatus; size?: 'sm' | 'xs' }) {
  const dim = size === 'xs' ? 'h-2.5 w-2.5' : 'h-3 w-3';
  if (status === 'running') return <Loader2 className={`${dim} animate-spin`} />;
  if (status === 'success') return <Check className={dim} />;
  if (status === 'failed') return <X className={dim} />;
  if (status === 'queued') return <Pause className={dim} />;
  if (status === 'skipped') return <SkipForward className={dim} />;
  return null;
}

export function AgentOrbNode({ data, selected }: NodeProps<AgentOrbNodeData>) {
  const { node, run, meta, compact = false } = data;
  const status = run.status;
  const style = ringStyle[status];
  const skillName = run.skillId ?? node.skillId ?? '等待调度';
  const durationText = run.durationMs ? `${(run.durationMs / 1000).toFixed(1)} 秒` : meta.role;
  const qualityText = run.qualityScore == null ? null : `质量 ${Math.round(run.qualityScore * 100)}%`;

  const tooltip = [
    `${meta.label}${node.skillId ? ` · ${node.skillId}` : ''}`,
    `状态：${statusLabel[status]}`,
    skillName ? `当前 skill：${skillName}` : null,
    durationText ? `耗时/职责：${durationText}` : null,
    qualityText,
  ]
    .filter(Boolean)
    .join('\n');

  const diameter = compact ? ORB_DIAMETER_COMPACT : ORB_DIAMETER;
  const labelSize = compact ? 'text-[10px]' : 'text-[11px]';
  const labelWidth = compact ? 'max-w-[78px]' : 'max-w-[110px]';
  const shortLabelSize = compact ? 'text-[10px]' : 'text-[12px]';
  const statusTextSize = compact ? 'text-[8px]' : 'text-[9px]';

  return (
    <div className="flex flex-col items-center" title={tooltip}>
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-slate-300" />
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-slate-300" />

      <div
        className={`relative flex items-center justify-center rounded-full transition-all ${style.ring} ${style.fill} ${
          compact ? 'shadow-[0_4px_14px_-10px_rgba(15,23,42,0.35)]' : 'shadow-[0_10px_28px_-16px_rgba(15,23,42,0.45)]'
        } ${selected ? 'ring-offset-2 ring-offset-white' : ''}`}
        style={{ width: diameter, height: diameter }}
      >
        <div className="flex flex-col items-center justify-center px-1 text-center">
          <span className={`${shortLabelSize} font-semibold leading-none ${style.text}`}>
            {meta.shortLabel}
          </span>
          <span className={`mt-0.5 inline-flex items-center gap-0.5 ${statusTextSize} ${style.subtle}`}>
            <StatusIcon status={status} size={compact ? 'xs' : 'sm'} />
            {statusLabel[status]}
          </span>
        </div>

        {qualityText && status === 'success' && !compact && (
          <span className="absolute -bottom-1.5 right-0 rounded-full bg-white px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 shadow-sm ring-1 ring-emerald-200">
            {Math.round((run.qualityScore ?? 0) * 100)}%
          </span>
        )}
      </div>

      <div className={`mt-1.5 ${labelWidth} truncate text-center ${labelSize} font-medium leading-tight text-slate-700`}>
        {meta.label}
      </div>
      {status === 'running' && !compact && (
        <div className="mt-0.5 max-w-[110px] truncate text-center text-[10px] text-slate-400">
          {skillName}
        </div>
      )}
    </div>
  );
}
