import { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronLeft, ChevronRight, Maximize2, Presentation } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { PptDeckSlide, ResourceItem } from '../types';
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

const swissSlideBase = 'relative flex aspect-[16/9] min-h-[360px] overflow-hidden bg-[#fafaf8] text-[#0a0a0a]';
const accent = '#ff6b35';

function EvidenceLine({ refs, tone = 'dark' }: { refs: string[]; tone?: 'dark' | 'light' }) {
  return (
    <p className={`font-mono text-[11px] font-semibold uppercase tracking-[0.12em] ${tone === 'light' ? 'text-white/75' : 'text-slate-500'}`}>
      Evidence · {refs.map((item) => `[${item}]`).join(' ')}
    </p>
  );
}

function Chrome({ index, total, refs, tone = 'dark' }: { index: number; total: number; refs: string[]; tone?: 'dark' | 'light' }) {
  return (
    <div className={`mb-5 flex items-center justify-between gap-4 font-mono text-[11px] font-semibold uppercase tracking-[0.16em] ${tone === 'light' ? 'text-white/80' : 'text-slate-500'}`}>
      <span>SecureHub Swiss · {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</span>
      <span>{refs.map((item) => `[${item}]`).join(' ')}</span>
    </div>
  );
}

function BulletList({ slide, className = '' }: { slide: PptDeckSlide; className?: string }) {
  return (
    <ul className={`grid gap-2.5 ${className}`}>
      {slide.bullets.map((bullet) => (
        <li key={bullet} className="border-t border-slate-300 pt-2 text-sm font-medium leading-relaxed text-slate-700">
          {bullet}
        </li>
      ))}
    </ul>
  );
}

function CodeCompare({ slide }: { slide: PptDeckSlide }) {
  const before = slide.code_demo?.before ?? slide.bullets[0] ?? '拼接查询结构';
  const after = slide.code_demo?.after ?? slide.bullets[1] ?? '参数化查询结构';
  return (
    <div className="grid min-h-0 grid-cols-[1fr_1px_1fr] gap-5">
      <div className="flex min-w-0 flex-col gap-3 bg-[#111] p-4 text-white">
        <h3 className="text-lg font-normal">脆弱形态</h3>
        <pre className="min-h-[150px] overflow-hidden whitespace-pre-wrap break-words bg-transparent font-mono text-xs leading-relaxed text-slate-100">
          {before}
        </pre>
      </div>
      <div className="bg-slate-300" />
      <div className="flex min-w-0 flex-col gap-3 p-4 text-white" style={{ backgroundColor: accent }}>
        <h3 className="text-lg font-normal">安全形态</h3>
        <pre className="min-h-[150px] overflow-hidden whitespace-pre-wrap break-words bg-transparent font-mono text-xs leading-relaxed text-white">
          {after}
        </pre>
      </div>
    </div>
  );
}

function SwissSlide({ slide, index, total }: { slide: PptDeckSlide; index: number; total: number }) {
  if (slide.layout_id === 'cover') {
    return (
      <section className={`${swissSlideBase} items-stretch text-white`} style={{ backgroundColor: accent }}>
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,.16)_1px,transparent_1px),linear-gradient(0deg,rgba(255,255,255,.16)_1px,transparent_1px)] bg-[length:32px_32px] opacity-80" />
        <div className="relative z-10 flex flex-1 flex-col p-9">
          <div className="mb-8 flex items-center justify-between gap-4 font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-white/80">
            <span>SecureHub · Course PPT</span>
            <span>{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</span>
          </div>
          <div className="mt-auto grid gap-5">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-white/80">Web Security Learning</p>
            <h2 className="max-w-4xl break-words text-6xl font-extralight leading-[0.98] tracking-normal">{slide.title}</h2>
            <div className="grid grid-cols-[1fr_auto] items-end gap-6 border-t border-white/35 pt-5">
              <p className="max-w-2xl text-xl leading-relaxed text-white/90">{slide.claim}</p>
              <EvidenceLine refs={slide.evidence_refs} tone="light" />
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (slide.layout_id === 'statement') {
    return (
      <section className={`${swissSlideBase} grid grid-cols-[0.92fr_1.08fr]`}>
        <div className="flex flex-col p-9 text-white" style={{ backgroundColor: accent }}>
          <Chrome index={index} total={total} refs={slide.evidence_refs} tone="light" />
          <h2 className="my-auto break-words text-6xl font-extralight leading-[0.96] tracking-normal">{slide.title}</h2>
        </div>
        <div className="flex flex-col p-9">
          <p className="my-auto text-2xl font-normal leading-snug text-slate-950">{slide.claim}</p>
          <div className="mt-6">
            <BulletList slide={slide} />
          </div>
        </div>
      </section>
    );
  }

  if (slide.layout_id === 'timeline') {
    return (
      <section className={`${swissSlideBase} flex-col p-9`}>
        <Chrome index={index} total={total} refs={slide.evidence_refs} tone="light" />
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Timeline</p>
        <h2 className="mt-2 text-5xl font-extralight tracking-normal">{slide.title}</h2>
        <p className="mt-3 max-w-3xl text-lg leading-relaxed text-slate-700">{slide.claim}</p>
        <div className="relative mt-10 grid flex-1 grid-cols-4 gap-4">
          <div className="absolute left-0 right-0 top-3 h-px bg-slate-300" />
          {slide.bullets.slice(0, 4).map((bullet, bulletIndex) => (
            <div key={bullet} className="relative z-10 flex min-w-0 flex-col gap-4">
              <span className="h-6 w-6" style={{ backgroundColor: accent }} />
              <span className="font-mono text-sm font-semibold text-[#ff6b35]">{String(bulletIndex + 1).padStart(2, '0')}</span>
              <p className="break-words text-lg font-medium leading-snug text-slate-900">{bullet}</p>
            </div>
          ))}
        </div>
        <EvidenceLine refs={slide.evidence_refs} />
      </section>
    );
  }

  if (slide.layout_id === 'compare') {
    return (
      <section className={`${swissSlideBase} flex-col p-9`}>
        <Chrome index={index} total={total} refs={slide.evidence_refs} />
        <div className="grid grid-rows-[auto_1fr_auto] gap-5">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Compare</p>
            <h2 className="mt-2 text-5xl font-extralight tracking-normal">{slide.title}</h2>
            <p className="mt-3 max-w-3xl text-lg leading-relaxed text-slate-700">{slide.claim}</p>
          </div>
          <CodeCompare slide={slide} />
          {slide.code_demo?.caption && <p className="text-xs font-medium text-slate-500">{slide.code_demo.caption}</p>}
        </div>
      </section>
    );
  }

  if (slide.layout_id === 'cards') {
    return (
      <section className={`${swissSlideBase} flex-col p-9`}>
        <Chrome index={index} total={total} refs={slide.evidence_refs} />
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Cards</p>
        <h2 className="mt-2 text-5xl font-extralight tracking-normal">{slide.title}</h2>
        <p className="mt-3 max-w-3xl text-lg leading-relaxed text-slate-700">{slide.claim}</p>
        <div className="mt-8 grid flex-1 grid-cols-3 gap-4">
          {slide.bullets.slice(0, 6).map((bullet, bulletIndex) => (
            <div
              key={bullet}
              className={`flex min-h-[96px] flex-col justify-between p-4 ${bulletIndex === 2 ? 'text-white' : 'bg-[#efefed] text-slate-950'}`}
              style={bulletIndex === 2 ? { backgroundColor: accent } : undefined}
            >
              <span className="font-mono text-xs font-semibold opacity-70">{String(bulletIndex + 1).padStart(2, '0')}</span>
              <p className="break-words text-lg font-normal leading-snug">{bullet}</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className={`${swissSlideBase} grid grid-cols-[0.9fr_1.1fr]`}>
      <div className="flex flex-col p-9 text-white" style={{ backgroundColor: accent }}>
        <Chrome index={index} total={total} refs={slide.evidence_refs} />
        <h2 className="my-auto break-words text-6xl font-extralight leading-[0.96] tracking-normal">{slide.title}</h2>
      </div>
      <div className="flex flex-col p-9">
        <p className="text-xl leading-relaxed text-slate-800">{slide.claim}</p>
        <div className="mt-8 grid flex-1 grid-rows-3 gap-3">
          {slide.bullets.slice(0, 3).map((bullet, bulletIndex) => (
            <div key={bullet} className="grid grid-cols-[48px_1fr] gap-4 border-t border-slate-300 pt-4">
              <span className="font-mono text-lg font-semibold text-[#ff6b35]">{String(bulletIndex + 1).padStart(2, '0')}</span>
              <p className="break-words text-lg font-medium leading-snug text-slate-900">{bullet}</p>
            </div>
          ))}
        </div>
        <EvidenceLine refs={slide.evidence_refs} />
      </div>
    </section>
  );
}

function SwissDeckView({ resource }: { resource: ResourceItem }) {
  const deckSpec = resource.deckSpec;
  const [current, setCurrent] = useState(0);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const total = deckSpec?.slides.length ?? 0;
  if (!deckSpec || !total) return null;
  const slide = deckSpec.slides[Math.min(current, total - 1)];
  const go = (next: number) => setCurrent(Math.max(0, Math.min(total - 1, next)));

  return (
    <Card
      title={resource.title}
      subtitle="SecureHub Swiss v1 结构化预览"
      right={
        <button
          type="button"
          onClick={() => void frameRef.current?.requestFullscreen()}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          全屏放映
        </button>
      }
    >
      <div ref={frameRef} className="overflow-hidden rounded-xl border border-slate-200 bg-slate-950 p-3">
        <div className="mx-auto max-w-5xl">
          <SwissSlide slide={slide} index={current} total={total} />
        </div>
        <div className="mt-3 flex items-center justify-between gap-3 text-white">
          <button
            type="button"
            onClick={() => go(current - 1)}
            disabled={current === 0}
            aria-label="上一页"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/20 text-white hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0 text-center">
            <p className="truncate text-sm font-medium">{deckSpec.title}</p>
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-white/60">
              {String(current + 1).padStart(2, '0')} / {String(total).padStart(2, '0')} · {deckSpec.theme}
            </p>
          </div>
          <button
            type="button"
            onClick={() => go(current + 1)}
            disabled={current === total - 1}
            aria-label="下一页"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/20 text-white hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Card>
  );
}

export function PptResourceView({ resource }: PptResourceViewProps) {
  const deckRef = useRef<HTMLDivElement | null>(null);
  const useSwissDeck = Boolean(resource.deckSpec && resource.renderMode === 'securehub_swiss_v1');
  const slides = useMemo(() => parseSlides(resource.content), [resource.content]);

  useEffect(() => {
    if (useSwissDeck) return undefined;
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
  }, [slides, useSwissDeck]);

  const requestFullscreen = () => {
    void deckRef.current?.requestFullscreen();
  };

  if (useSwissDeck) {
    return <SwissDeckView resource={resource} />;
  }

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
