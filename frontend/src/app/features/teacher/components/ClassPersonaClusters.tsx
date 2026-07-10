// Status: mock
// 班级画像聚类气泡图：散点图风格，每个气泡 = 一类学生，
// 大小 = 人数，颜色 = 主导画像维度，位置 = 二维空间（知识深度 × 学习目标）。

import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { buildClassPersonaClusters } from '@/lib/mock/persona.mock';
import type { ClassPersonaClusterPoint } from '@/lib/types/persona.types';

const WIDTH = 540;
const HEIGHT = 280;
const PADDING = 32;

function radiusForCount(count: number): number {
  return 14 + Math.sqrt(count) * 5.4;
}

export function ClassPersonaClusters({ onClusterPick }: { onClusterPick?: (cluster: ClassPersonaClusterPoint) => void }) {
  const clusters = useMemo(() => buildClassPersonaClusters(), []);
  const [active, setActive] = useState<ClassPersonaClusterPoint | null>(null);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <Sparkles className="h-3.5 w-3.5 text-brand-blue-500" />
            班级画像聚类
          </h2>
          <p className="text-xs text-slate-400">基于 60 名学生画像，AI 在二维特征空间聚成 5 类</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {clusters.map((cluster) => (
            <button
              key={cluster.id}
              type="button"
              onClick={() => {
                setActive(cluster);
                onClusterPick?.(cluster);
              }}
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] transition-colors ${
                active?.id === cluster.id ? 'ring-2 ring-offset-1' : ''
              }`}
              style={{
                background: `${cluster.color}1a`,
                color: cluster.color,
              }}
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: cluster.color }} />
              {cluster.label} · {cluster.studentCount}
            </button>
          ))}
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(220px,1fr)]">
        <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="班级画像聚类气泡图">
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={`hx-${ratio}`}
              x1={PADDING}
              y1={PADDING + (HEIGHT - PADDING * 2) * (1 - ratio)}
              x2={WIDTH - PADDING}
              y2={PADDING + (HEIGHT - PADDING * 2) * (1 - ratio)}
              stroke="#e2e8f0"
              strokeDasharray="3 3"
            />
          ))}
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={`vy-${ratio}`}
              x1={PADDING + (WIDTH - PADDING * 2) * ratio}
              y1={PADDING}
              x2={PADDING + (WIDTH - PADDING * 2) * ratio}
              y2={HEIGHT - PADDING}
              stroke="#e2e8f0"
              strokeDasharray="3 3"
            />
          ))}
          <line x1={PADDING} y1={HEIGHT - PADDING} x2={WIDTH - PADDING} y2={HEIGHT - PADDING} stroke="#94a3b8" />
          <line x1={PADDING} y1={PADDING} x2={PADDING} y2={HEIGHT - PADDING} stroke="#94a3b8" />
          <text x={WIDTH - PADDING} y={HEIGHT - 8} textAnchor="end" style={{ fontSize: 10, fill: '#64748b' }}>
            学习目标 · 实战 →
          </text>
          <text
            x={PADDING - 16}
            y={PADDING + 4}
            textAnchor="end"
            style={{ fontSize: 10, fill: '#64748b' }}
            transform={`rotate(-90 ${PADDING - 16} ${PADDING + 4})`}
          >
            知识深度 ↑
          </text>

          {clusters.map((cluster) => {
            const cx = PADDING + cluster.axisX * (WIDTH - PADDING * 2);
            const cy = PADDING + (1 - cluster.axisY) * (HEIGHT - PADDING * 2);
            const r = radiusForCount(cluster.studentCount);
            const isActive = active?.id === cluster.id;
            return (
              <g
                key={cluster.id}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  setActive(cluster);
                  onClusterPick?.(cluster);
                }}
              >
                <motion.circle
                  initial={{ r: 0, opacity: 0 }}
                  animate={{ r, opacity: 0.85 }}
                  transition={{ duration: 0.5, ease: 'backOut' }}
                  cx={cx}
                  cy={cy}
                  fill={cluster.color}
                  fillOpacity={isActive ? 0.4 : 0.25}
                  stroke={cluster.color}
                  strokeWidth={isActive ? 2.2 : 1.4}
                />
                <text x={cx} y={cy + 3} textAnchor="middle" style={{ fontSize: 11, fontWeight: 600, fill: cluster.color }}>
                  {cluster.studentCount}
                </text>
                <text x={cx} y={cy + r + 14} textAnchor="middle" style={{ fontSize: 11, fill: '#475569' }}>
                  {cluster.label}
                </text>
              </g>
            );
          })}
        </svg>

        <aside className="rounded-xl bg-slate-50 p-3 text-xs">
          {active ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: active.color }} />
                <p className="text-sm font-semibold text-slate-800">{active.label}</p>
                <Tag tone="blue">{active.studentCount} 人</Tag>
              </div>
              <p className="text-slate-500">
                主导维度：{dimensionLabel(active.dominantDimension)} · 平均掌握度 {Math.round(active.axisY * 100)}%
              </p>
              <div>
                <p className="mb-1 text-[11px] text-slate-400">代表学生（节选 6 名）</p>
                <ul className="grid grid-cols-2 gap-1 text-slate-600">
                  {active.studentIds.slice(0, 6).map((id) => (
                    <li key={id} className="truncate rounded bg-white px-2 py-1 text-[11px]">
                      {id}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-slate-400">点击任一聚类气泡查看该组学生列表</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function dimensionLabel(key: string): string {
  return (
    {
      base_knowledge: '知识基础',
      cognitive_style: '认知风格',
      weak_points: '易错点',
      preferred_modality: '偏好学习方式',
      time_budget: '时间预算',
      target_direction: '目标方向',
      motivation: '学习动机',
    } as Record<string, string>
  )[key] ?? key;
}
