import { AlertCircle, CheckCircle2, Clock3, FileText, Sparkles } from 'lucide-react';

import { Card, Tag } from '@/app/components/PageShell';

import type { WorkspaceDashboard } from '../types';
import { autosaveLabels, formatDateTime, getDashboardStats } from '../utils';

const saveTone: Record<WorkspaceDashboard['autosaveStatus'], 'green' | 'blue' | 'amber' | 'red'> = {
  saved: 'green',
  saving: 'blue',
  unsaved: 'amber',
  error: 'red',
};

export function WorkspaceSummaryBar({ dashboard }: { dashboard: WorkspaceDashboard }) {
  const stats = getDashboardStats(dashboard);
  const items = [
    {
      label: '待完成任务',
      value: stats.unfinishedTaskCount,
      sub: `高优 ${stats.highPriorityTaskCount} 项`,
      icon: CheckCircle2,
    },
    {
      label: '截止提醒',
      value: stats.activeDeadlineCount,
      sub: '活跃提醒',
      icon: Clock3,
    },
    {
      label: '推荐行动',
      value: stats.activeActionCount,
      sub: '待处理',
      icon: Sparkles,
    },
    {
      label: '最近生成物',
      value: stats.assetCount,
      sub: `收藏 ${stats.favoriteAssetCount} 个`,
      icon: FileText,
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {items.map((item) => (
        <Card key={item.label} className="min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs text-slate-500">{item.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{item.value}</p>
              <p className="mt-1 text-xs text-slate-600">{item.sub}</p>
            </div>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-blue-50 text-brand-blue-600">
              <item.icon className="h-4 w-4" />
            </div>
          </div>
        </Card>
      ))}

      <Card className="min-w-0">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-slate-500">保存状态</p>
            <div className="mt-2">
              <Tag tone={saveTone[dashboard.autosaveStatus]}>
                {autosaveLabels[dashboard.autosaveStatus]}
              </Tag>
            </div>
            <p className="mt-2 truncate text-xs text-slate-600">
              {dashboard.savedAt ? `上次 ${formatDateTime(dashboard.savedAt)}` : '等待首次保存'}
            </p>
          </div>
          <AlertCircle className="h-5 w-5 shrink-0 text-slate-300" />
        </div>
      </Card>
    </div>
  );
}
