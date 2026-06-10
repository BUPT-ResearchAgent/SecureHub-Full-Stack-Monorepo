// Status: real
import type { AgentRunDTO } from './types';

export const getRunId = (r: AgentRunDTO) => r.id ?? r.run_id ?? '';

export function formatDuration(duration?: number | null): string {
  if (duration == null) return '等待中';
  if (duration < 1000) return `${duration} ms`;
  return `${(duration / 1000).toFixed(1)} s`;
}

export function statusLabel(status?: string): string {
  const labels: Record<string, string> = {
    success: '成功',
    running: '运行中',
    failed: '失败',
  };
  return labels[status ?? ''] ?? '未知';
}

export function statusBadgeClass(status?: string): string {
  if (status === 'success') return 'bg-emerald-50 text-emerald-700 border-emerald-100';
  if (status === 'running') return 'bg-blue-50 text-blue-700 border-blue-100';
  if (status === 'failed') return 'bg-red-50 text-red-700 border-red-100';
  return 'bg-slate-50 text-slate-600 border-slate-100';
}

export function formatQuality(score?: number | null): string {
  if (score == null) return '待评估';
  return `${Math.round(score * 100)}%`;
}

export function formatCreatedAt(value?: string): string {
  if (!value) return '刚刚';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '刚刚';
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
