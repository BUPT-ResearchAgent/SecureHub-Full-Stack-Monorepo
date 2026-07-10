// Status: mock
// 隐式评估：在 AssessmentPanel 显式评估旁展示隐式评估，含 5 个信号 + 解读。

import { motion } from 'motion/react';
import { Activity, BookOpen, BrainCircuit, Clock, FlaskConical, Repeat } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import type { ImplicitAssessment, ImplicitSignalKind } from '@/lib/types/assessment.types';

const signalMeta: Record<ImplicitSignalKind, { icon: typeof Activity; color: string }> = {
  question_depth: { icon: BrainCircuit, color: '#2563eb' },
  dwell_time: { icon: Clock, color: '#10b981' },
  reading_order: { icon: BookOpen, color: '#f59e0b' },
  revisit_count: { icon: Repeat, color: '#7c3aed' },
  lab_attempts: { icon: FlaskConical, color: '#ec4899' },
};

export type ImplicitAssessmentCardProps = {
  assessment: ImplicitAssessment;
  explicitScore: number;
};

export function ImplicitAssessmentCard({ assessment, explicitScore }: ImplicitAssessmentCardProps) {
  const explicitPct = Math.round(explicitScore * 100);
  const implicitPct = Math.round(assessment.totalScore * 100);
  const diffPct = Math.round(assessment.diffFromExplicit * 100);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <Activity className="h-3.5 w-3.5 text-brand-blue-500" />
            隐式评估 · AI 通过你的行为推断真实掌握度
          </h3>
          <p className="text-xs text-slate-500">不依赖做题，从提问 / 停留 / 顺序等行为信号综合分析。</p>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-slate-400">显式 vs 隐式</p>
          <p className="text-base font-semibold text-slate-800">
            {explicitPct}% / {implicitPct}%
          </p>
          <Tag tone={diffPct > 0 ? 'green' : diffPct < 0 ? 'amber' : 'default'}>
            {diffPct > 0 ? `隐式高 ${diffPct}%` : diffPct < 0 ? `隐式低 ${-diffPct}%` : '基本一致'}
          </Tag>
        </div>
      </header>

      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-5">
        {assessment.signals.map((signal) => {
          const meta = signalMeta[signal.kind];
          const Icon = meta.icon;
          return (
            <motion.div
              key={signal.kind}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-xl border border-slate-100 bg-slate-50 p-2.5"
            >
              <div className="flex items-center gap-1.5 text-xs">
                <span
                  className="grid h-6 w-6 place-items-center rounded-full"
                  style={{ background: `${meta.color}22`, color: meta.color }}
                >
                  <Icon className="h-3 w-3" />
                </span>
                <span className="font-medium text-slate-800">{signal.label}</span>
                <span className="ml-auto text-[11px] font-semibold text-slate-700">
                  {Math.round(signal.score * 100)}%
                </span>
              </div>
              <p className="mt-1.5 text-[10px] leading-4 text-slate-500">{signal.description}</p>
              <div className="mt-1.5 h-1.5 rounded-full bg-white">
                <span className="block h-full rounded-full" style={{ width: `${signal.score * 100}%`, background: meta.color }} />
              </div>
              <p className="mt-1 text-[10px] text-slate-400">权重 {Math.round(signal.weight * 100)}%</p>
            </motion.div>
          );
        })}
      </div>

      <p className="mt-3 rounded-md bg-brand-blue-50 px-3 py-2 text-[11px] leading-5 text-brand-blue-800">
        💡 AI 判断：
        {diffPct > 5
          ? '你的显式分被低估了，实际掌握度比做题更高，可以进入更深层节点。'
          : diffPct < -5
          ? '你的做题分高于实际行为信号，AI 建议补一次实操而非继续做题。'
          : '显式与隐式分基本一致，路径与节奏可以维持。'}
      </p>
    </section>
  );
}
