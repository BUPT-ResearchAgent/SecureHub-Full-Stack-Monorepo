import { Card, Tag } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

export interface DocResourceViewProps {
  resource: ResourceItem;
}

export function DocResourceView({ resource }: DocResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="证据驱动的讲解文档">
      <MarkdownRenderer content={resource.content} />
      <div className="mt-4 flex flex-wrap gap-2">
        {resource.evidenceRefs.map((evidence) => (
          <Tag key={evidence.chunk_id} tone="green">
            {evidence.platform ?? '来源'} · {Math.round((evidence.reliability ?? 0) * 100)}%
          </Tag>
        ))}
      </div>
    </Card>
  );
}
