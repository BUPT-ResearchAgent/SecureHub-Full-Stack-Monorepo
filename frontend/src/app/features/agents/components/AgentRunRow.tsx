// Status: real
import { Activity } from 'lucide-react';
import { Progress } from '@/app/components/ui/progress';
import type { AgentRunDTO } from '../types';
import { formatCreatedAt, formatDuration, formatQuality, getRunId, statusBadgeClass, statusLabel } from '../utils';

export function AgentRunRow({ run }: { run: AgentRunDTO }) {
  const running = run.status === 'running';
  const statusText = statusLabel(run.status);
  const qualityValue = run.quality_score == null ? 0 : Math.round(run.quality_score * 100);
  const qualityText = formatQuality(run.quality_score);
  return (
    <div
      className={`grid gap-2 rounded-lg border p-3 text-xs transition-colors ${
        running ? 'border-blue-200 bg-blue-50/80 shadow-sm' : 'border-slate-100 bg-white'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">{run.workflow_name ?? 'course_learning'}</p>
          <p className="mt-0.5 truncate text-slate-500">
            {run.agent_name} · {run.skill_name}
          </p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 ${statusBadgeClass(run.status)}`}
          aria-label={statusText}
        >
          {running && <Activity className="h-3 w-3 animate-pulse" />}
          {statusText}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-slate-500">
        <span>耗时 {formatDuration(run.duration_ms)}</span>
        <span>质量 {qualityText}</span>
        <span className="text-right">{formatCreatedAt(run.created_at)}</span>
      </div>
      <div className="flex items-center gap-2" aria-label={`质量分 ${qualityText}`}>
        <Progress value={qualityValue} className="h-1.5 bg-slate-100" />
        <span className="w-10 text-right text-[11px] text-slate-500">{qualityText}</span>
      </div>
      <p className="truncate text-[11px] text-slate-400">运行 ID：{getRunId(run)}</p>
    </div>
  );
}
