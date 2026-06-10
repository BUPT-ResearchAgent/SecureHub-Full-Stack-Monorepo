// Status: partial-real
import { ScrollText } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export function ReadingsResourceView({ resource }: { resource: ResourceItem }) {
  const lines = resource.content.split('\n').filter(Boolean);
  return (
    <Card title={resource.title} subtitle="拓展阅读清单">
      <div className="space-y-3">
        {lines.length ? lines.map((line) => (
          <div key={line} className="flex gap-3 rounded-lg border border-slate-100 p-3 text-sm text-slate-700">
            <ScrollText className="mt-0.5 h-4 w-4 shrink-0 text-[#003399]" />
            <span>{line}</span>
          </div>
        )) : (
          <p className="text-sm text-slate-500">生成后将展示多平台拓展阅读材料。</p>
        )}
      </div>
    </Card>
  );
}
