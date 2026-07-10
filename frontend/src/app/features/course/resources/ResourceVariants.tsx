// Status: mock
// 三变体生成：深入版 / 浅显版 / 案例版 并排展示，选一个后其他淡出但保留入口。

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, Clock3, Compass, RotateCw, Sparkles, Target } from 'lucide-react';
import type { ResourceVariant, ResourceVariantKind } from '@/lib/types/resource-variant.types';

export type ResourceVariantsProps = {
  variants: ResourceVariant[];
  selectedKind?: ResourceVariantKind;
  onSelect: (variant: ResourceVariant) => void;
  onReopen?: (variant: ResourceVariant) => void;
};

const kindMeta: Record<ResourceVariantKind, { label: string; tone: string; icon: typeof Target }> = {
  deep: { label: '深入版', tone: 'border-violet-200 bg-violet-50 text-violet-700', icon: Target },
  easy: { label: '浅显版', tone: 'border-emerald-200 bg-emerald-50 text-emerald-700', icon: Compass },
  case: { label: '案例版', tone: 'border-amber-200 bg-amber-50 text-amber-700', icon: Sparkles },
};

export function ResourceVariants({ variants, selectedKind, onSelect, onReopen }: ResourceVariantsProps) {
  const [previewKind, setPreviewKind] = useState<ResourceVariantKind | undefined>(selectedKind);
  const active = previewKind ?? selectedKind;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <Sparkles className="h-3.5 w-3.5 text-brand-blue-600" />
            AI 为你准备了 3 个版本
          </h3>
          <p className="text-xs text-slate-500">选一个最适合你的开始学，其他两个仍可"回头看"。</p>
        </div>
        {active && (
          <button
            type="button"
            onClick={() => {
              setPreviewKind(undefined);
            }}
            className="text-[11px] text-slate-500 hover:text-brand-blue-600"
          >
            重新对比 3 版本
          </button>
        )}
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        {variants.map((variant) => {
          const meta = kindMeta[variant.kind];
          const Icon = meta.icon;
          const isSelected = selectedKind === variant.kind;
          const isFaded = selectedKind && selectedKind !== variant.kind;
          return (
            <motion.article
              key={variant.id}
              layout
              initial={false}
              animate={{
                opacity: isFaded ? 0.55 : 1,
                scale: isSelected ? 1.02 : 1,
              }}
              transition={{ duration: 0.28 }}
              className={`relative flex flex-col gap-2 rounded-xl border p-3 ${meta.tone} ${
                isSelected ? 'ring-2 ring-offset-1 ring-brand-blue-400' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1 rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-semibold">
                  <Icon className="h-3 w-3" />
                  {meta.label}
                </span>
                <span className="inline-flex items-center gap-0.5 text-[10px] text-slate-500">
                  <Clock3 className="h-3 w-3" />
                  {variant.estimateMinutes} 分钟
                </span>
              </div>
              <h4 className="text-sm font-semibold leading-5 text-slate-900">{variant.title}</h4>
              <p className="text-[11px] font-medium text-slate-700">{variant.tagline}</p>
              <p className="text-[11px] leading-5 text-slate-600">{variant.description}</p>
              <ul className="mt-1 flex flex-wrap gap-1">
                {variant.highlights.map((highlight) => (
                  <li
                    key={highlight}
                    className="rounded-full bg-white/60 px-1.5 py-0.5 text-[10px] text-slate-600"
                  >
                    {highlight}
                  </li>
                ))}
              </ul>
              <div className="mt-1 text-[10px] text-slate-500">推荐给：{variant.preferredFor.join(' / ')}</div>
              <div className="mt-2 flex items-center gap-2">
                {isSelected ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    已选定
                  </span>
                ) : isFaded ? (
                  <button
                    type="button"
                    onClick={() => onReopen?.(variant)}
                    className="inline-flex items-center gap-1 rounded-full border border-white/80 bg-white/60 px-2 py-1 text-[11px] text-slate-600 hover:bg-white"
                  >
                    <RotateCw className="h-3 w-3" />
                    回头看
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onSelect(variant)}
                    onMouseEnter={() => setPreviewKind(variant.kind)}
                    onMouseLeave={() => setPreviewKind(undefined)}
                    className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-brand-blue-700"
                  >
                    选用此版本
                  </button>
                )}
              </div>
            </motion.article>
          );
        })}
      </div>

      <AnimatePresence>
        {selectedKind && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="mt-3 rounded-md bg-brand-blue-50 px-3 py-2 text-[11px] text-brand-blue-700"
          >
            ✅ 已记录你的偏好：本次选择会写入"偏好学习方式"维度，后续资源会朝同方向倾斜。
          </motion.p>
        )}
      </AnimatePresence>
    </section>
  );
}
