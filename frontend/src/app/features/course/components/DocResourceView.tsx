import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, Tag } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface DocResourceViewProps {
  resource: ResourceItem;
}

export function DocResourceView({ resource }: DocResourceViewProps) {
  return (
    <Card title={resource.title} subtitle="Markdown resource with evidence">
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{resource.content}</ReactMarkdown>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {resource.evidenceRefs.map((evidence) => (
          <Tag key={evidence.chunkId} tone="green">
            {evidence.source} · {Math.round(evidence.reliability * 100)}%
          </Tag>
        ))}
      </div>
    </Card>
  );
}
