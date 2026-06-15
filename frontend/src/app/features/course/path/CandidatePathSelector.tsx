// Status: mock
// 三路径并存 segmented control，其他两条以小窗预览展示。

import { motion } from 'motion/react';
import { Clock, Compass, Flame, Layers } from 'lucide-react';
import type { CandidatePath, PathStrategy } from '@/lib/types/learning-path.types';

const meta: Record<PathStrategy, { icon: typeof Compass; tone: string }> = {
  sprint: { icon: Flame, tone: 'border-rose-300 bg-rose-50 text-rose-700' },
  deep: { icon: Layers, tone: 'border-violet-300 bg-violet-50 text-violet-700' },
  practice: { icon: Compass, tone: 'border-amber-300 bg-amber-50 text-amber-700' },
};

export type CandidatePathSelectorProps = {
  paths: CandidatePath[];
  selectedId: string;
  onSelect: (id: string) => void;
};

export function CandidatePathSelector({ paths, selectedId, onSelect }: CandidatePathSelectorProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="mb-3 flex items-center gap-1 rounded-full bg-slate-100 p-1 text-xs">
        {paths.map((path) => {
          const m = meta[path.strategy];
          const Icon = m.icon;
          return (
            <button
              key={path.id}
              type="button"
              onClick={() => onSelect(path.id)}
              className={`flex-1 inline-flex items-center justify-center gap-1.5 rounded-full px-3 py-1 ${
                selectedId === path.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {path.label}
              <span className="text-[10px] text-slate-400">{path.totalDays}天</span>
            </button>
          );
        })}
      </div>

      <div className="grid gap-2 md:grid-cols-3">
        {paths.map((path) => {
          const m = meta[path.strategy];
          const Icon = m.icon;
          const isActive = selectedId === path.id;
          return (
            <motion.button
              key={path.id}
              type="button"
              layout
              onClick={() => onSelect(path.id)}
              animate={{ opacity: isActive ? 1 : 0.7, scale: isActive ? 1 : 0.97 }}
              className={`flex flex-col gap-1.5 rounded-xl border p-3 text-left transition-shadow ${m.tone} ${
                isActive ? 'ring-2 ring-offset-1 ring-brand-blue-400 shadow' : ''
              }`}
            >
              <div className="flex items-center gap-1.5">
                <Icon className="h-3.5 w-3.5" />
                <span className="text-sm font-semibold">{path.label}</span>
                {isActive && (
                  <span className="ml-auto rounded-full bg-white/80 px-1.5 py-0.5 text-[10px] font-medium">
                    当前路径
                  </span>
                )}
              </div>
              <p className="text-[11px] leading-5 opacity-90">{path.description}</p>
              <p className="flex items-center gap-1 text-[10px] opacity-75">
                <Clock className="h-2.5 w-2.5" />
                {path.daily}
              </p>
              <ul className="flex flex-wrap gap-1">
                {path.highlights.map((highlight) => (
                  <li
                    key={highlight}
                    className="rounded-full bg-white/70 px-1.5 py-0.5 text-[10px]"
                  >
                    {highlight}
                  </li>
                ))}
              </ul>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
