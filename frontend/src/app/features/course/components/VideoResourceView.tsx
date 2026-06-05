import { Video } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface VideoResourceViewProps {
  resource: ResourceItem;
}

export function VideoResourceView({ resource }: VideoResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="Mermaid storyboard + XFYun TTS skeleton">
      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <pre className="min-h-[220px] whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-slate-100">
          {resource.content || 'graph LR\nA[Concept] --> B[Example] --> C[Practice]'}
        </pre>
        <div className="rounded-lg border border-slate-200 p-4">
          <Video className="mb-3 h-5 w-5 text-[#003399]" />
          <p className="text-sm text-slate-600">TODO: attach XFYun TTS audio URL and sync storyboard progress.</p>
          <audio className="mt-4 w-full" controls />
        </div>
      </div>
    </Card>
  );
}
