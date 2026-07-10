// Status: mock
// 剧本式台词卡：顶部"剧本标题"，agent 激活时浮现台词卡（头像 + 中文名 + 台词），3 秒淡出。
// 用 timer 队列驱动。

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Clapperboard } from 'lucide-react';
import type { ResourceScreenplay, ScreenplayCue } from '@/lib/types/resource-variant.types';

export type ScreenplayCueDeckProps = {
  screenplay: ResourceScreenplay;
  active: boolean;
  onActComplete?: (act: number) => void;
};

export function ScreenplayCueDeck({ screenplay, active, onActComplete }: ScreenplayCueDeckProps) {
  const [visibleCues, setVisibleCues] = useState<ScreenplayCue[]>([]);
  const [currentAct, setCurrentAct] = useState(0);

  useEffect(() => {
    if (!active) {
      setVisibleCues([]);
      setCurrentAct(0);
      return;
    }
    const enterTimers: number[] = [];
    const exitTimers: number[] = [];
    screenplay.cues.forEach((cue, idx) => {
      enterTimers.push(
        window.setTimeout(() => {
          setVisibleCues((current) => [...current, cue]);
          setCurrentAct(idx + 1);
          onActComplete?.(idx);
        }, cue.actAt * 1000),
      );
      exitTimers.push(
        window.setTimeout(
          () => setVisibleCues((current) => current.filter((c) => c.id !== cue.id)),
          cue.actAt * 1000 + cue.durationMs,
        ),
      );
    });
    return () => {
      enterTimers.forEach((t) => window.clearTimeout(t));
      exitTimers.forEach((t) => window.clearTimeout(t));
    };
  }, [active, screenplay, onActComplete]);

  if (!active) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-gradient-to-r from-brand-blue-50/60 to-white px-3 py-2">
        <Clapperboard className="h-4 w-4 text-brand-blue-600" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-900">{screenplay.title}</p>
          <p className="text-[11px] text-slate-500">{screenplay.subtitle}</p>
        </div>
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-500 ring-1 ring-slate-200">
          幕 {currentAct} / {screenplay.totalActs}
        </span>
      </div>

      <div className="relative min-h-[88px]">
        <AnimatePresence>
          {visibleCues.map((cue, idx) => (
            <motion.div
              key={cue.id}
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.96 }}
              transition={{ duration: 0.28, ease: 'easeOut' }}
              className="absolute left-0 right-0 flex gap-2 rounded-xl border border-brand-blue-100 bg-white p-2.5 shadow-md"
              style={{ top: idx * 24 }}
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-blue-50 text-lg">
                {cue.avatar}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-semibold text-brand-blue-700">
                  {cue.agentName}
                  <span className="ml-1.5 text-[10px] font-normal text-slate-400">{cue.agentId}</span>
                </p>
                <p className="mt-0.5 text-xs leading-5 text-slate-700">{cue.line}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
