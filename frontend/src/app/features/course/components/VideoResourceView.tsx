import { Video } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface VideoResourceViewProps {
  resource: ResourceItem;
}

export function VideoResourceView({ resource }: VideoResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="分镜脚本与语音合成预览">
      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <pre className="min-h-[220px] whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-slate-100">
          {resource.content || 'graph LR\nA[概念] --> B[案例] --> C[练习]'}
        </pre>
        <div className="rounded-lg border border-slate-200 p-4">
          <Video className="mb-3 h-5 w-5 text-[#003399]" />
          <p className="text-sm text-slate-600">生成后可关联讯飞语音合成音频，并同步分镜进度。</p>
          <audio className="mt-4 w-full" controls />
        </div>
      </div>
    </Card>
  );
}
