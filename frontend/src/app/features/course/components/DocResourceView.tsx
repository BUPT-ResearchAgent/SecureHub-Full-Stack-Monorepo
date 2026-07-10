import { useEffect, useReducer, useRef } from 'react';
import { Card, Tag } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

export interface DocResourceViewProps {
  resource: ResourceItem;
}

type DocContentState = {
  resourceId: string;
  content: string;
};

type DocContentAction =
  | { type: 'reset'; resourceId: string; content: string }
  | { type: 'setContent'; content: string };

function docContentReducer(state: DocContentState, action: DocContentAction): DocContentState {
  if (action.type === 'reset') {
    return { resourceId: action.resourceId, content: action.content };
  }
  return { ...state, content: action.content };
}

export function DocResourceView({ resource }: DocResourceViewProps) {
  const [{ content }, dispatch] = useReducer(docContentReducer, {
    resourceId: resource.id,
    content: resource.content,
  });
  const latestContentRef = useRef(resource.content);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    latestContentRef.current = resource.content;
    if (frameRef.current != null) return undefined;
    frameRef.current = window.requestAnimationFrame(() => {
      frameRef.current = null;
      dispatch({ type: 'setContent', content: latestContentRef.current });
    });
    return undefined;
  }, [resource.content]);

  useEffect(() => {
    dispatch({ type: 'reset', resourceId: resource.id, content: resource.content });
  }, [resource.id]);

  useEffect(() => () => {
    if (frameRef.current != null) window.cancelAnimationFrame(frameRef.current);
  }, []);

  return (
    <Card title={resource.title} subtitle="证据驱动的讲解文档">
      <MarkdownRenderer content={content} />
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
