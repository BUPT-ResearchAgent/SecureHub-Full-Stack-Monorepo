// Status: mock
// 错题病灶分析：评估完成后 AI 自动诊断"共同根因"，并提供针对性资源 + 练习推荐。

import { Stethoscope, Sparkles, Plus, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Tag } from '@/app/components/PageShell';
import { toast } from 'sonner';
import type { WeaknessDiagnosis } from '@/lib/types/assessment.types';

export type WeaknessDiagnosisDrawerProps = {
  diagnosis?: WeaknessDiagnosis;
  open: boolean;
  onClose: () => void;
};

export function WeaknessDiagnosisDrawer({ diagnosis, open, onClose }: WeaknessDiagnosisDrawerProps) {
  return (
    <AnimatePresence>
      {open && diagnosis && (
        <motion.aside
          initial={{ x: 380, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 380, opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed right-0 top-16 z-30 h-[calc(100vh-5rem)] w-[400px] overflow-y-auto border-l border-slate-200 bg-white p-5 shadow-2xl"
          role="dialog"
          aria-label="错题病灶分析"
        >
          <header className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] text-slate-400">错题病灶分析</p>
              <h3 className="mt-0.5 flex items-center gap-1.5 text-base font-semibold text-slate-900">
                <Stethoscope className="h-4 w-4 text-rose-600" />
                共 {diagnosis.meta.incorrectCount} 道错题，归纳 {diagnosis.rootCauses.length} 个根因
              </h3>
              <p className="mt-1 text-[11px] text-slate-500">
                AI 找的不是单题对错，而是共同病灶；推荐资源已为你定制。
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭"
              className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <ul className="mt-4 space-y-3">
            {diagnosis.rootCauses.map((cause) => (
              <li key={cause.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                  <Sparkles className="h-3.5 w-3.5 text-brand-blue-500" />
                  {cause.topic}
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  涉及题目：{cause.affectedItemIds.join(' / ')}
                </p>
                <blockquote className="mt-2 rounded-md bg-white px-3 py-2 text-[11px] italic leading-5 text-slate-600 ring-1 ring-slate-100">
                  「{cause.evidenceSnippet}」
                </blockquote>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Tag tone="blue">推荐资源：{cause.suggestedResource.title}</Tag>
                  <Tag tone="amber">{cause.suggestedResource.agent}</Tag>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    💪 配套练习：{cause.exerciseTitle}（{cause.exerciseCount} 题）
                  </span>
                  <button
                    type="button"
                    onClick={() => toast.success(`已加入学习计划：${cause.suggestedResource.title} + ${cause.exerciseTitle}`)}
                    className="inline-flex items-center gap-1 rounded-full bg-brand-blue-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-brand-blue-700"
                  >
                    <Plus className="h-3 w-3" />
                    加入学习计划
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
