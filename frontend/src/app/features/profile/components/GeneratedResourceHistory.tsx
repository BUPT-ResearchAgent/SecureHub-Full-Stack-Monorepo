// Status: partial-real
import { useEffect, useState } from 'react';
import { Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { EmptyState, ErrorState, LoadingState } from '@/app/components/StateView';
import { listGeneratedResources } from '../api';
import type { GeneratedResourceDTO, ResourceType } from '@/lib/sse.types';

const resourceLabels: Record<ResourceType, string> = {
  doc: '讲解文档',
  ppt: '演示课件',
  mindmap: '思维导图',
  quiz: '练习题',
  lab: '实操实验',
  video: '视频脚本',
  readings: '扩展阅读',
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '刚刚';
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function qualityClass(score?: number | null): string {
  if (score == null) return 'bg-slate-100 text-slate-500';
  if (score >= 0.85) return 'bg-emerald-50 text-emerald-700';
  if (score >= 0.7) return 'bg-amber-50 text-amber-700';
  return 'bg-red-50 text-red-700';
}

export function GeneratedResourceHistory({ userId }: { userId: string }) {
  const navigate = useNavigate();
  const [resources, setResources] = useState<GeneratedResourceDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    setError('');
    listGeneratedResources(userId)
      .then(setResources)
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : '资源历史加载失败');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [userId]);

  if (loading) return <LoadingState text="正在加载资源历史…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!resources.length) return <EmptyState text="暂无生成资源，完成课程资源生成后会自动沉淀到这里" />;

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="grid grid-cols-[110px_minmax(0,1fr)_120px_100px_80px] gap-3 border-b border-slate-100 px-4 py-3 text-xs font-medium text-slate-500">
        <span>资源类型</span>
        <span>标题</span>
        <span>生成时间</span>
        <span>质量分</span>
        <span className="text-right">操作</span>
      </div>
      <div className="divide-y divide-slate-100">
        {resources.map((resource) => {
          const qualityLabel = resource.quality_score == null
            ? '待评估'
            : `${Math.round(resource.quality_score * 100)}%`;
          return (
            <div
              key={resource.id}
              className="grid grid-cols-[110px_minmax(0,1fr)_120px_100px_80px] items-center gap-3 px-4 py-3 text-sm"
            >
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">
                {resourceLabels[resource.resource_type]}
              </span>
              <span className="min-w-0 truncate font-medium text-slate-900">{resource.title}</span>
              <span className="text-xs text-slate-500">{formatDate(resource.created_at)}</span>
              <span
                className={`inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-medium ${qualityClass(resource.quality_score)}`}
                aria-label={`质量分 ${qualityLabel}`}
              >
                {qualityLabel}
              </span>
              <button
                type="button"
                onClick={() => navigate('/course?tab=workbench')}
                className="inline-flex items-center justify-end gap-1 text-xs font-medium text-brand-blue-600 hover:text-brand-blue-700"
              >
                <Eye className="h-3.5 w-3.5" />
                查看
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
