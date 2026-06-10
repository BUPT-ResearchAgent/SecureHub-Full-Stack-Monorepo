import { GitBranch } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface MindmapResourceViewProps {
  resource: ResourceItem;
}

export function MindmapResourceView({ resource }: MindmapResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="思维导图预览">
      <div className="flex min-h-[260px] items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50">
        <div className="text-center">
          <GitBranch className="mx-auto mb-3 h-8 w-8 text-[#003399]" />
          <p className="text-sm font-medium text-slate-700">生成后将在这里渲染知识结构。</p>
          <pre className="mt-3 max-w-xl whitespace-pre-wrap text-left text-xs text-slate-500">{resource.content}</pre>
        </div>
      </div>
    </Card>
  );
}
