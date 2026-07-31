// Status: real

import {
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  Boxes,
  Network,
  Sigma,
} from 'lucide-react';

export type KnowledgeNodeStats = {
  resourceCount: number;
  quizCount: number;
  inDegree: number;
  outDegree: number;
  degree: number;
  pageRank: number;
};

export type ChapterGraphStats = {
  chapter: string;
  color: string;
  nodeCount: number;
  resourceCount: number;
  quizCount: number;
  averageDifficulty: number;
};

export function GraphStatistics({
  selectedStats,
  chapters,
  difficultyDistribution,
}: {
  selectedStats?: KnowledgeNodeStats;
  chapters: readonly ChapterGraphStats[];
  difficultyDistribution: readonly number[];
}) {
  const maxChapterActivity = Math.max(
    1,
    ...chapters.map((chapter) => chapter.resourceCount + chapter.quizCount),
  );
  const maxDifficulty = Math.max(1, ...difficultyDistribution);

  return (
    <section className="space-y-4" aria-label="知识网络统计">
      {selectedStats && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Network className="h-3.5 w-3.5 text-brand-blue-600" />
            <h4 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
              节点网络指标
            </h4>
          </div>
          <dl className="grid grid-cols-2 gap-2">
            <Metric
              icon={ArrowDownToLine}
              label="入度"
              value={selectedStats.inDegree}
            />
            <Metric
              icon={ArrowUpFromLine}
              label="出度"
              value={selectedStats.outDegree}
            />
            <Metric
              icon={Sigma}
              label="连接度"
              value={selectedStats.degree}
            />
            <Metric
              icon={Boxes}
              label="PageRank"
              value={selectedStats.pageRank.toFixed(3)}
              hint="基于先修关系的近似值"
            />
          </dl>
        </div>
      )}

      <div>
        <div className="mb-2 flex items-center gap-2">
          <BarChart3 className="h-3.5 w-3.5 text-brand-blue-600" />
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            章节学习密度
          </h4>
        </div>
        <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-700 dark:bg-slate-950/60">
          {chapters.map((chapter) => {
            const activity = chapter.resourceCount + chapter.quizCount;
            return (
              <div key={chapter.chapter}>
                <div className="flex items-center justify-between gap-2 text-[10px]">
                  <span className="min-w-0 truncate font-medium text-slate-600 dark:text-slate-300">
                    {chapter.chapter}
                  </span>
                  <span className="shrink-0 tabular-nums text-slate-400">
                    {chapter.nodeCount} 点 · {chapter.resourceCount} 资源 · {chapter.quizCount} 题
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-slate-800">
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${Math.max(5, activity / maxChapterActivity * 100)}%`,
                      backgroundColor: chapter.color,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            难度分布
          </h4>
          <span className="text-[9px] text-slate-400">1 级 → 5 级</span>
        </div>
        <div className="flex h-20 items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50/70 px-3 pb-2.5 pt-3 dark:border-slate-700 dark:bg-slate-950/60">
          {difficultyDistribution.map((count, index) => (
            <div key={index} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[9px] font-medium tabular-nums text-slate-400">{count}</span>
              <span
                className="w-full rounded-t-md bg-gradient-to-t from-brand-blue-700 to-cyan-400"
                style={{ height: `${Math.max(8, count / maxDifficulty * 42)}px` }}
              />
              <span className="text-[9px] text-slate-400">{index + 1}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Network;
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-slate-700 dark:bg-slate-900"
      title={hint}
    >
      <dt className="flex items-center gap-1.5 text-[9px] text-slate-400">
        <Icon className="h-3 w-3" />
        {label}
      </dt>
      <dd className="mt-1 text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
        {value}
      </dd>
    </div>
  );
}
