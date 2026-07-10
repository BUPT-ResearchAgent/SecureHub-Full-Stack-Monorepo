// Status: mock
// 同伴对比：不显示排名，显示相对位置 + 短板诊断；雷达图叠加班级中位数。

import { Award, ShieldAlert, ShieldCheck, TrendingUp } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { PeerComparison } from '@/lib/types/assessment.types';

export function PeerComparisonCard({ comparison }: { comparison: PeerComparison }) {
  const overallPct = Math.round(comparison.overallPercentile * 100);

  return (
    <Card title="同伴对比 · 你在班级中的位置" subtitle="不是排名，是相对位置 + 短板诊断">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-slate-500">综合相对位置</p>
          <p className="mt-0.5 flex items-center gap-2 text-2xl font-semibold text-slate-900">
            <Award className="h-5 w-5 text-amber-500" />
            前 {Math.max(0, 100 - overallPct)}%
          </p>
          <p className="mt-1 text-xs text-slate-500">{comparison.summary}</p>
        </div>
        <div className="rounded-xl bg-brand-blue-50 px-3 py-2 text-[11px] text-brand-blue-700">
          <p>👍 不焦虑式对比</p>
          <p>📈 重在找短板和优势</p>
        </div>
      </div>

      <ul className="mt-3 space-y-2">
        {comparison.dimensions.map((dim) => {
          const better = dim.betterThanRatio;
          const isStrong = better >= 0.65;
          return (
            <li
              key={dim.dimension}
              className="rounded-xl border border-slate-100 bg-slate-50 p-3"
            >
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{dim.label}</span>
                <span
                  className={`flex items-center gap-1 text-xs ${
                    isStrong ? 'text-emerald-700' : better >= 0.45 ? 'text-slate-600' : 'text-rose-600'
                  }`}
                >
                  {isStrong ? <ShieldCheck className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
                  {isStrong
                    ? `你比 ${Math.round(better * 100)}% 同学强 🎉`
                    : better >= 0.45
                    ? '与班级中位数持平'
                    : `${Math.round((1 - better) * 100)}% 同学比你强 💪`}
                </span>
              </div>
              <div className="relative mt-2 h-2 rounded-full bg-white ring-1 ring-slate-100">
                <span
                  className="absolute left-0 top-0 h-full rounded-full bg-brand-blue-500"
                  style={{ width: `${dim.selfScore * 100}%` }}
                />
                <span
                  className="absolute top-[-2px] h-3 w-0.5 rounded bg-slate-400"
                  style={{ left: `${dim.classMedian * 100}%` }}
                  title="班级中位数"
                />
              </div>
              <p className="mt-1 flex items-center gap-3 text-[10px] text-slate-500">
                <span>我：{Math.round(dim.selfScore * 100)}%</span>
                <span>班级中位：{Math.round(dim.classMedian * 100)}%</span>
                {isStrong && (
                  <span className="inline-flex items-center gap-0.5 text-emerald-700">
                    <TrendingUp className="h-2.5 w-2.5" />
                    +{Math.round((dim.selfScore - dim.classMedian) * 100)}%
                  </span>
                )}
              </p>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
