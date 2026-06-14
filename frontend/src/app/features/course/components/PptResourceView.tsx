import { useEffect, useMemo, useRef } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Maximize2, Presentation } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { ResourceItem } from '../types';
import 'reveal.js/dist/reveal.css';
import 'reveal.js/dist/theme/white.css';

export interface PptResourceViewProps {
  resource: ResourceItem;
}

type RevealDeck = {
  initialize: () => Promise<void> | void;
  destroy: () => void;
  sync?: () => void;
};

function parseSlides(content: string): string[] {
  const slides = content
    .split(/\n---\n/g)
    .map((slide) => slide.trim())
    .filter(Boolean);
  return slides.length ? slides : ['# 演示大纲\n\n生成后将在这里展示课堂演示页面。'];
}

const slideComponents: Components = {
  li({ children }) {
    return <li className="fragment">{children}</li>;
  },
};

export function PptResourceView({ resource }: PptResourceViewProps) {
  const deckRef = useRef<HTMLDivElement | null>(null);
  const slides = useMemo(() => parseSlides(resource.content), [resource.content]);

  useEffect(() => {
    let disposed = false;
    let deck: RevealDeck | null = null;

    async function setupDeck() {
      const element = deckRef.current;
      if (!element) return;
      const { default: Reveal } = await import('reveal.js');
      if (disposed) return;
      deck = new Reveal(element, {
        embedded: true,
        controls: true,
        progress: true,
        center: false,
        hash: false,
        width: 960,
        height: 540,
        margin: 0.08,
      }) as RevealDeck;
      await deck.initialize();
      deck.sync?.();
    }

    void setupDeck();
    return () => {
      disposed = true;
      deck?.destroy();
    };
  }, [slides]);

  const requestFullscreen = () => {
    void deckRef.current?.requestFullscreen();
  };

  return (
    <Card
      title={resource.title}
      subtitle="reveal.js 嵌入式放映预览"
      right={
        <button
          type="button"
          onClick={requestFullscreen}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          全屏放映
        </button>
      }
    >
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-950">
        <div className="reveal h-[460px] bg-white text-slate-900" ref={deckRef}>
          <div className="slides">
            {slides.map((slide, index) => (
              <section key={`${resource.id}-slide-${index}`} className="px-12 py-8 text-left">
                <div className="mb-4 flex items-center gap-2 text-sm font-medium text-brand-blue-600">
                  <Presentation className="h-4 w-4" />
                  第 {index + 1} 页 / 共 {slides.length} 页
                </div>
                <div className="prose prose-slate max-w-none prose-headings:text-slate-950 prose-li:my-1">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={slideComponents}>
                    {slide}
                  </ReactMarkdown>
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
