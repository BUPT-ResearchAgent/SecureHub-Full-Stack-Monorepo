import { useEffect, useRef, useState } from 'react';
import { GitBranch, RefreshCw } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';

export interface MindmapResourceViewProps {
  resource: ResourceItem;
}

type MarkmapInstance = {
  fit: () => void;
  destroy?: () => void;
};

export function MindmapResourceView({ resource }: MindmapResourceViewProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const markmapRef = useRef<MarkmapInstance | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;

    async function renderMindmap() {
      const svg = svgRef.current;
      if (!svg) return;
      setError(null);
      svg.replaceChildren();
      markmapRef.current?.destroy?.();

      try {
        const [{ Transformer }, { Markmap }] = await Promise.all([
          import('markmap-lib'),
          import('markmap-view'),
        ]);
        if (disposed) return;
        const transformer = new Transformer();
        const { root } = transformer.transform(resource.content || '# SQL 注入基础\n\n## 等待生成');
        markmapRef.current = Markmap.create(svg, {
          autoFit: true,
          duration: 220,
          fitRatio: 0.92,
          paddingX: 24,
        }, root) as MarkmapInstance;
        window.setTimeout(() => markmapRef.current?.fit(), 80);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '思维导图渲染失败');
      }
    }

    void renderMindmap();
    const fit = () => markmapRef.current?.fit();
    window.addEventListener('resize', fit);

    return () => {
      disposed = true;
      window.removeEventListener('resize', fit);
      markmapRef.current?.destroy?.();
      markmapRef.current = null;
    };
  }, [resource.content]);

  return (
    <Card
      title={resource.title}
      subtitle="markmap 知识结构图"
      right={
        <button
          type="button"
          onClick={() => markmapRef.current?.fit()}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          适配视图
        </button>
      }
    >
      <div className="relative min-h-[460px] overflow-hidden rounded-xl border border-slate-200 bg-white">
        <svg ref={svgRef} className="h-[460px] w-full" role="img" aria-label="SQL 注入知识结构思维导图" />
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90 p-6 text-center">
            <div>
              <GitBranch className="mx-auto mb-3 h-8 w-8 text-amber-600" />
              <p className="text-sm font-medium text-slate-900">思维导图渲染失败</p>
              <p className="mt-1 text-xs text-slate-500">{error}</p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
