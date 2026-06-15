// Status: mock
// 画像叙事段：把 6 维度凝练为 80-120 字人物简介，关键词品牌蓝高亮。

import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import type { PersonaNarrativeSegment } from '@/lib/types/persona.types';

export type PersonaNarrativeProps = {
  segment: PersonaNarrativeSegment;
};

function renderHighlighted(text: string, highlights: string[]): JSX.Element[] {
  if (!highlights.length) {
    return [<span key="plain">{text.replace(/\*\*/g, '')}</span>];
  }
  const stripped = text.replace(/\*\*/g, '');
  const parts: JSX.Element[] = [];
  let cursor = 0;
  const sortedHighlights = [...highlights].sort((a, b) => b.length - a.length);
  while (cursor < stripped.length) {
    const next = sortedHighlights
      .map((kw) => ({ kw, idx: stripped.indexOf(kw, cursor) }))
      .filter((m) => m.idx !== -1)
      .sort((a, b) => a.idx - b.idx)[0];
    if (!next) {
      parts.push(<span key={`r-${cursor}`}>{stripped.slice(cursor)}</span>);
      break;
    }
    if (next.idx > cursor) {
      parts.push(<span key={`p-${cursor}`}>{stripped.slice(cursor, next.idx)}</span>);
    }
    parts.push(
      <span
        key={`h-${next.idx}`}
        className="rounded-md bg-brand-blue-50 px-1 py-0.5 font-semibold text-brand-blue-700"
      >
        {next.kw}
      </span>,
    );
    cursor = next.idx + next.kw.length;
  }
  return parts;
}

export function PersonaNarrative({ segment }: PersonaNarrativeProps) {
  return (
    <motion.div
      key={segment.generatedAt}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className="rounded-xl border border-brand-blue-100 bg-gradient-to-br from-white to-brand-blue-50/40 p-4"
    >
      <p className="flex items-center gap-1.5 text-xs font-medium text-brand-blue-700">
        <Sparkles className="h-3.5 w-3.5" />
        AI 画像叙事
      </p>
      <p className="mt-2 text-sm leading-7 text-slate-800">
        {renderHighlighted(segment.text, segment.highlights)}
      </p>
      <p className="mt-2 text-[11px] text-slate-400">
        基于 {segment.dimensionKeys.length} 维画像维度生成 · 实时刷新
      </p>
    </motion.div>
  );
}
