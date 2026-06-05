import { Activity } from 'lucide-react';
import { progressColor } from '@/app/features/course/utils';

export interface StreamingProgressProps {
  percentage: number;
  label?: string;
}

export function StreamingProgress({ percentage, label = 'Workflow progress' }: StreamingProgressProps) {
  const safePercentage = Math.max(0, Math.min(100, percentage));
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="inline-flex items-center gap-2 font-medium text-slate-700">
          <Activity className="h-4 w-4 text-[#003399]" />
          {label}
        </span>
        <span className="text-slate-500">{safePercentage}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full ${progressColor(safePercentage)}`} style={{ width: `${safePercentage}%` }} />
      </div>
    </div>
  );
}
