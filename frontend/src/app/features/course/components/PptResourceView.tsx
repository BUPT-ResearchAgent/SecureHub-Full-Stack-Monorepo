import { Download, Presentation } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface PptResourceViewProps {
  resource: ResourceItem;
}

export function PptResourceView({ resource }: PptResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="演示大纲预览">
      <div className="rounded-lg border border-slate-200 bg-slate-950 p-5 text-slate-100">
        <Presentation className="mb-3 h-5 w-5 text-blue-300" />
        <pre className="whitespace-pre-wrap text-sm">{resource.content || '生成后将在这里展示课堂演示大纲。'}</pre>
      </div>
      <button className="mt-4 inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">
        <Download className="h-4 w-4" />
        下载大纲
      </button>
    </Card>
  );
}
