// Status: mock
// 班级路径完成率热力图：横轴节点 / 纵轴学生 / 单元格颜色 = 完成度。
// 视觉类似 GitHub contribution graph。

import { useMemo, useState } from 'react';
import { Activity, Flame } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { buildClassCompletionMatrix } from '@/lib/mock/learning-path.mock';

function cellColor(completion: number): string {
  if (completion >= 0.9) return '#1d4ed8';
  if (completion >= 0.7) return '#3b82f6';
  if (completion >= 0.5) return '#93c5fd';
  if (completion >= 0.25) return '#dbeafe';
  return '#f1f5f9';
}

export function PathCompletionHeatmap() {
  const matrix = useMemo(() => buildClassCompletionMatrix(), []);
  const [hover, setHover] = useState<{ studentName: string; nodeLabel: string; completion: number } | null>(null);

  const columnAvg = useMemo(() => {
    return matrix.nodeIds.map((nodeId) => {
      const cells = matrix.cells.filter((cell) => cell.nodeId === nodeId);
      const avg = cells.reduce((sum, c) => sum + c.completion, 0) / cells.length;
      return { nodeId, avg };
    });
  }, [matrix]);

  const struggleColumns = columnAvg.filter((col) => col.avg < 0.4);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <Flame className="h-3.5 w-3.5 text-rose-500" />
            学习路径完成率热力图
          </h3>
          <p className="text-xs text-slate-500">
            {matrix.cells.length / matrix.nodeIds.length} 名学生 × {matrix.nodeIds.length} 个节点 ·
            一眼定位班级普遍卡点
          </p>
        </div>
        {struggleColumns.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {struggleColumns.map((col) => {
              const idx = matrix.nodeIds.indexOf(col.nodeId);
              return (
                <Tag key={col.nodeId} tone="red">
                  普遍卡点 · {matrix.nodeLabels[idx]}（均值 {Math.round(col.avg * 100)}%）
                </Tag>
              );
            })}
          </div>
        )}
      </header>

      <div className="overflow-x-auto">
        <div className="inline-block">
          <div className="flex">
            <div className="w-20 shrink-0" />
            {matrix.nodeLabels.map((label) => (
              <div key={label} className="w-12 text-center text-[10px] text-slate-500" title={label}>
                {label}
              </div>
            ))}
          </div>
          {Array.from(new Set(matrix.cells.map((cell) => cell.studentId))).map((studentId) => {
            const row = matrix.cells.filter((cell) => cell.studentId === studentId);
            const name = row[0]?.studentName ?? studentId;
            return (
              <div key={studentId} className="flex items-center">
                <div className="w-20 shrink-0 truncate pr-2 text-right text-[10px] text-slate-500" title={name}>
                  {name}
                </div>
                {matrix.nodeIds.map((nodeId, nIdx) => {
                  const cell = row.find((c) => c.nodeId === nodeId);
                  const completion = cell?.completion ?? 0;
                  return (
                    <div key={nodeId} className="w-12 px-0.5">
                      <button
                        type="button"
                        onMouseEnter={() =>
                          setHover({ studentName: name, nodeLabel: matrix.nodeLabels[nIdx], completion })
                        }
                        onMouseLeave={() => setHover(null)}
                        className="h-3 w-full rounded-sm transition-transform hover:scale-110"
                        style={{ background: cellColor(completion) }}
                        aria-label={`${name} · ${matrix.nodeLabels[nIdx]} · ${Math.round(completion * 100)}%`}
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
        <span>0%</span>
        <div className="flex h-2 flex-1 overflow-hidden rounded-full">
          {[0, 0.25, 0.5, 0.7, 0.9].map((v) => (
            <span key={v} className="h-full flex-1" style={{ background: cellColor(v) }} />
          ))}
        </div>
        <span>100%</span>
      </div>

      {hover && (
        <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-1.5 text-[11px] text-slate-700">
          <Activity className="h-3 w-3 text-brand-blue-500" />
          {hover.studentName} · {hover.nodeLabel} · 完成度 {Math.round(hover.completion * 100)}%
        </div>
      )}
    </section>
  );
}
