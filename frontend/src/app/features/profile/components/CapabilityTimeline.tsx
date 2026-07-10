// Status: mock
// 能力演变史：底部时间轴 scrubber，拖到任意时间点重绘雷达图；
// 旁边显示该时间段的"关键事件"。

import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { CalendarRange, History } from 'lucide-react';
import { Card } from '@/app/components/PageShell';
import type { CapabilityTimeline as CapabilityTimelineData } from '@/lib/types/assessment.types';

export type CapabilityTimelineProps = {
  timeline: CapabilityTimelineData;
};

const SIZE = 240;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R = 88;

const dimensionLabels: Record<string, string> = {
  web_security: 'Web 安全',
  crypto: '密码学',
  system_security: '系统安全',
  pentest: '渗透',
  governance: '安全治理',
  ai_security: 'AI 安全',
};

export function CapabilityTimeline({ timeline }: CapabilityTimelineProps) {
  const [pointIdx, setPointIdx] = useState(timeline.points.length - 1);
  const point = timeline.points[pointIdx];
  const dimensions = timeline.dimensions;

  const angles = useMemo(
    () => dimensions.map((_, idx) => -Math.PI / 2 + (idx * Math.PI * 2) / dimensions.length),
    [dimensions],
  );

  const polygonPoints = dimensions
    .map((dim, idx) => {
      const value = point.dimensions[dim] ?? 0;
      const radius = R * Math.max(0.05, value);
      return `${CX + Math.cos(angles[idx]) * radius},${CY + Math.sin(angles[idx]) * radius}`;
    })
    .join(' ');

  return (
    <Card title="能力演变史" subtitle="拖动时间轴查看历史时刻的雷达">
      <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="能力演变雷达">
          {[0.25, 0.5, 0.75, 1].map((ratio) => (
            <polygon
              key={ratio}
              fill="none"
              stroke="#e2e8f0"
              points={angles
                .map((angle) => `${CX + Math.cos(angle) * R * ratio},${CY + Math.sin(angle) * R * ratio}`)
                .join(' ')}
            />
          ))}
          {angles.map((angle, idx) => (
            <line
              key={idx}
              x1={CX}
              y1={CY}
              x2={CX + Math.cos(angle) * R}
              y2={CY + Math.sin(angle) * R}
              stroke="#e2e8f0"
            />
          ))}
          <motion.polygon
            points={polygonPoints}
            fill="rgba(29,78,216,0.22)"
            stroke="#1d4ed8"
            strokeWidth={1.8}
            initial={false}
            animate={{ points: polygonPoints }}
            transition={{ duration: 0.4 }}
          />
          {dimensions.map((dim, idx) => {
            const lx = CX + Math.cos(angles[idx]) * (R + 14);
            const ly = CY + Math.sin(angles[idx]) * (R + 14);
            return (
              <text
                key={dim}
                x={lx}
                y={ly}
                textAnchor={Math.abs(Math.cos(angles[idx])) < 0.2 ? 'middle' : Math.cos(angles[idx]) > 0 ? 'start' : 'end'}
                style={{ fontSize: 10, fill: '#475569' }}
              >
                {dimensionLabels[dim] ?? dim}
              </text>
            );
          })}
        </svg>
        <div className="space-y-3">
          <div className="rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3 text-xs text-brand-blue-800">
            <p className="flex items-center gap-1 font-semibold">
              <CalendarRange className="h-3 w-3" />
              {new Date(point.recordedAt).toLocaleDateString('zh-CN', { dateStyle: 'long' })}
            </p>
            <ul className="mt-2 space-y-1 text-[11px]">
              {point.highlightEvents.map((event) => (
                <li key={event.title}>
                  <span className="font-medium">{event.title}</span>
                  <span className="ml-1 text-brand-blue-700/70">— {event.description}</span>
                  <span
                    className={`ml-1 inline-flex rounded-full px-1.5 py-0 text-[10px] ${
                      event.delta >= 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}
                  >
                    {event.delta >= 0 ? '+' : ''}
                    {Math.round(event.delta * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
            <p className="flex items-center gap-1 text-xs font-semibold text-slate-700">
              <History className="h-3 w-3" />
              时间轴拖动条
            </p>
            <input
              type="range"
              min={0}
              max={timeline.points.length - 1}
              value={pointIdx}
              onChange={(event) => setPointIdx(Number(event.target.value))}
              className="mt-2 w-full accent-brand-blue-600"
            />
            <div className="mt-1 flex justify-between text-[10px] text-slate-500">
              {timeline.points.map((p, idx) => (
                <button
                  type="button"
                  key={p.recordedAt}
                  onClick={() => setPointIdx(idx)}
                  className={`rounded px-1 ${pointIdx === idx ? 'font-semibold text-brand-blue-700' : ''}`}
                >
                  {new Date(p.recordedAt).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-1 text-[11px] md:grid-cols-2 lg:grid-cols-7">
        {timeline.points.map((p, idx) => (
          <div
            key={p.recordedAt}
            className="rounded-md border border-slate-100 p-2"
            style={{
              background: `rgba(29,78,216,${Math.min(0.35, p.dimensions.web_security ?? 0.1) + 0.05})`,
            }}
            title={new Date(p.recordedAt).toLocaleString('zh-CN')}
            onClick={() => setPointIdx(idx)}
          >
            <span className="font-mono text-[10px] text-slate-500">
              {new Date(p.recordedAt).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
            </span>
            <p className="mt-0.5 text-slate-700">
              {Math.round((p.dimensions.web_security ?? 0) * 100)}%
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
