// Status: mock
// 智能体辩论可视化：doc_archivist vs outcome_evaluator 对话气泡，底部 diff 高亮。

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GitCompare, MessagesSquare } from 'lucide-react';
import type { AgentDebate } from '@/lib/types/resource-variant.types';

export type AgentDebatePanelProps = {
  debate: AgentDebate;
  autoPlay?: boolean;
};

export function AgentDebatePanel({ debate, autoPlay = true }: AgentDebatePanelProps) {
  const [visibleCount, setVisibleCount] = useState(autoPlay ? 0 : debate.exchanges.length);

  useEffect(() => {
    if (!autoPlay) return;
    const timers: number[] = [];
    debate.exchanges.forEach((exchange, idx) => {
      timers.push(
        window.setTimeout(() => setVisibleCount(idx + 1), exchange.emittedAt * 1000),
      );
    });
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [debate, autoPlay]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <MessagesSquare className="h-3.5 w-3.5 text-brand-blue-600" />
            智能体辩论 · {debate.topic}
          </h3>
          <p className="text-xs text-slate-500">
            {debate.versionFrom} → {debate.versionTo} 的内容质量在此辩论中收敛。
          </p>
        </div>
      </header>

      <div className="space-y-2">
        <AnimatePresence>
          {debate.exchanges.slice(0, visibleCount).map((exchange) => {
            const isChallenger = exchange.side === 'challenger';
            return (
              <motion.div
                key={exchange.id}
                initial={{ opacity: 0, x: isChallenger ? -10 : 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.28 }}
                className={`flex gap-2 ${isChallenger ? 'flex-row' : 'flex-row-reverse'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-5 ${
                    isChallenger ? 'bg-rose-50 text-rose-900' : 'bg-emerald-50 text-emerald-900'
                  }`}
                >
                  <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider opacity-75">
                    {exchange.speakerLabel}
                  </p>
                  {exchange.message}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {visibleCount >= debate.exchanges.length && (
        <div className="mt-4 rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-blue-700">
            <GitCompare className="h-3.5 w-3.5" />
            {debate.resolution}
          </p>
          <div className="mt-2 max-h-44 overflow-y-auto rounded-lg bg-white p-2 font-mono text-[11px] leading-5">
            {debate.diff.map((segment, idx) => (
              <span
                key={idx}
                className={
                  segment.type === 'add'
                    ? 'block bg-emerald-50 text-emerald-800'
                    : segment.type === 'remove'
                    ? 'block bg-rose-50 text-rose-700 line-through'
                    : 'block text-slate-600'
                }
              >
                {segment.type === 'add' ? '+ ' : segment.type === 'remove' ? '- ' : '  '}
                {segment.text}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
