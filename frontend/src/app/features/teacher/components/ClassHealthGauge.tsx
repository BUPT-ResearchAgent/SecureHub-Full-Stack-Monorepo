// Status: mock
// 班级学习健康度：综合 5 个指标 → 0-100 + 趋势线 + 仪表盘环形。

import { useMemo } from 'react';
import { motion } from 'motion/react';
import { Heart, Activity } from 'lucide-react';
import { Tag } from '@/app/components/PageShell';
import { buildClassHealth } from '@/lib/mock/assessment-product.mock';

const TONE: Record<'healthy' | 'attention' | 'risk', { color: string; label: string }> = {
  healthy: { color: '#10b981', label: '健康' },
  attention: { color: '#f59e0b', label: '需关注' },
  risk: { color: '#ef4444', label: '风险' },
};

export function ClassHealthGauge() {
  const health = useMemo(() => buildClassHealth(), []);
  const tone = TONE[health.classification];
  const arcAngle = (health.overall / 100) * 270;
  const RADIUS = 56;
  const CIRC = 2 * Math.PI * RADIUS;
  const dashOffset = CIRC - (arcAngle / 360) * CIRC;

  const trendWidth = 220;
  const trendHeight = 70;
  const trendPad = 8;
  const trendPath = useMemo(() => {
    return health.trend
      .map((point, idx) => {
        const x = trendPad + (idx / (health.trend.length - 1)) * (trendWidth - trendPad * 2);
        const y = trendHeight - trendPad - (point.score / 100) * (trendHeight - trendPad * 2);
        return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  }, [health.trend]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <Heart className="h-3.5 w-3.5 text-rose-500" />
            班级学习健康度
          </h2>
          <p className="text-xs text-slate-400">综合活跃度 / 完成率 / 评估均分 / 提问质量 / 资源使用</p>
        </div>
        <Tag tone={health.classification === 'healthy' ? 'green' : health.classification === 'attention' ? 'amber' : 'red'}>
          {tone.label}
        </Tag>
      </header>

      <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)]">
        <div className="relative grid h-[180px] place-items-center">
          <svg width={160} height={160} viewBox="0 0 160 160">
            <circle cx={80} cy={80} r={RADIUS} fill="none" stroke="#e2e8f0" strokeWidth={12} />
            <motion.circle
              cx={80}
              cy={80}
              r={RADIUS}
              fill="none"
              stroke={tone.color}
              strokeWidth={12}
              strokeLinecap="round"
              strokeDasharray={CIRC}
              initial={{ strokeDashoffset: CIRC }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              transform="rotate(135 80 80)"
            />
            <text x={80} y={80} textAnchor="middle" style={{ fontSize: 32, fontWeight: 700, fill: tone.color }}>
              {health.overall}
            </text>
            <text x={80} y={100} textAnchor="middle" style={{ fontSize: 11, fill: '#64748b' }}>
              健康度 / 100
            </text>
          </svg>
        </div>

        <div className="space-y-3">
          <ul className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {health.metrics.map((metric) => (
              <li
                key={metric.key}
                className="rounded-lg border border-slate-100 bg-slate-50 p-2 text-[11px]"
              >
                <p className="text-slate-500">{metric.label}</p>
                <p className="mt-1 text-lg font-semibold text-slate-800">{metric.score}</p>
                <div className="mt-1 h-1.5 rounded-full bg-white">
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${metric.score}%`,
                      background: metric.score >= 80 ? '#10b981' : metric.score >= 60 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>

          <div className="rounded-xl border border-slate-100 bg-slate-50 p-2.5">
            <p className="flex items-center gap-1 text-[11px] text-slate-500">
              <Activity className="h-3 w-3" />
              近 14 天趋势
            </p>
            <svg width={trendWidth} height={trendHeight} viewBox={`0 0 ${trendWidth} ${trendHeight}`} className="mt-1 w-full">
              <path d={trendPath} fill="none" stroke="#1d4ed8" strokeWidth={1.6} />
              {health.trend.map((point, idx) => {
                const x = trendPad + (idx / (health.trend.length - 1)) * (trendWidth - trendPad * 2);
                const y = trendHeight - trendPad - (point.score / 100) * (trendHeight - trendPad * 2);
                return <circle key={idx} cx={x} cy={y} r={1.6} fill="#1d4ed8" />;
              })}
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
