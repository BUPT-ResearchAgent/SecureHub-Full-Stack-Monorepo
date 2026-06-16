// Status: partial-real
//
// 4-B-3 升级：
//   1) 顶部新增雷达多边形 SVG，score 实线 + confidence 虚线两层叠加。
//   2) 支持 `classMedian` 比对线，用于教师端「班级 vs 个体」对照视图。
//   3) 原始能力列表 + 高亮脉冲保留，作为下半部分细节。

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Activity, ShieldCheck } from 'lucide-react';
import { Card, Tag } from '@/app/components/PageShell';
import { EmptyState } from '@/app/components/StateView';
import { normalizePersonaDimension, personaDimensionMatches } from '@/lib/persona-dimension-map';
import type { CapabilityDTO } from '@/lib/sse.types';

function percent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

export type RadarOverlay = {
  label: string;
  scores: Record<string, number>; // dimension -> 0-1
  color: string;
  dashed?: boolean;
};

export type CapabilityRadarCardProps = {
  capabilities: CapabilityDTO[];
  highlightDimension?: string;
  overlay?: RadarOverlay;
  showRadar?: boolean;
};

export function CapabilityRadarCard({
  capabilities,
  highlightDimension,
  overlay,
  showRadar = true,
}: CapabilityRadarCardProps) {
  const [activeHighlight, setActiveHighlight] = useState<string | undefined>(() => normalizePersonaDimension(highlightDimension));
  useEffect(() => {
    setActiveHighlight(normalizePersonaDimension(highlightDimension));
    if (!highlightDimension) return;
    const timer = window.setTimeout(() => setActiveHighlight(undefined), 4500);
    return () => window.clearTimeout(timer);
  }, [highlightDimension]);

  return (
    <Card title="能力雷达" subtitle="基于 user_capabilities 的课程学习能力画像">
      {!capabilities.length ? (
        <EmptyState text="完成画像对话以解锁能力雷达" />
      ) : (
        <>
          {showRadar && capabilities.length >= 3 && (
            <RadarPolygon capabilities={capabilities} overlay={overlay} />
          )}
          <ul className="mt-3 space-y-4">
            {capabilities.map((capability) => {
              const score = percent(capability.score);
              const confidence = percent(capability.confidence);
              const isActive = personaDimensionMatches(activeHighlight, capability.dimension);
              return (
                <li key={capability.dimension} className="relative">
                  {isActive && (
                    <motion.span
                      aria-hidden
                      className="pointer-events-none absolute -inset-2 rounded-xl ring-2 ring-brand-blue-400"
                      initial={{ opacity: 0.6, scale: 1 }}
                      animate={{ opacity: [0.6, 0, 0.55, 0], scale: [1, 1.04, 1.02, 1.05] }}
                      transition={{ duration: 2.4, ease: 'easeOut', repeat: 1 }}
                    />
                  )}
                  <div className="mb-1.5 flex items-center justify-between gap-3">
                    <div>
                      <p className="flex items-center gap-1.5 text-sm font-medium text-slate-800">
                        {capability.dimension}
                        {isActive && (
                          <motion.span
                            initial={{ opacity: 0, x: -4 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-0.5 rounded-full bg-brand-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-blue-700"
                          >
                            <Activity className="h-2.5 w-2.5" />
                            刚更新
                          </motion.span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        证据 {capability.evidence_count} 条 · 置信度 {confidence}%
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Tag tone={confidence >= 70 ? 'green' : confidence >= 45 ? 'blue' : 'amber'}>
                        <ShieldCheck className="mr-1 h-3 w-3" />
                        {confidence}%
                      </Tag>
                      <span className="w-10 text-right text-sm font-semibold text-slate-900">{score}%</span>
                    </div>
                  </div>
                  <div className="relative h-2 rounded-full bg-slate-100">
                    <motion.div
                      className={`h-full rounded-full ${isActive ? 'bg-brand-blue-500' : 'bg-brand-blue-600'}`}
                      initial={false}
                      animate={{ width: `${score}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                    />
                    <span
                      className="pointer-events-none absolute top-0 h-2 rounded-full border border-dashed border-brand-blue-300/70"
                      style={{ width: `${confidence}%` }}
                      aria-hidden
                    />
                  </div>
                </li>
              );
            })}
          </ul>
          {overlay && (
            <div className="mt-3 flex items-center gap-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-brand-blue-500" />
                我的能力
              </span>
              <span className="inline-flex items-center gap-1">
                <span
                  className="inline-block h-0.5 w-3"
                  style={{ borderBottom: `2px ${overlay.dashed ? 'dashed' : 'solid'} ${overlay.color}` }}
                />
                {overlay.label}
              </span>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function RadarPolygon({
  capabilities,
  overlay,
}: {
  capabilities: CapabilityDTO[];
  overlay?: RadarOverlay;
}) {
  const SIZE = 220;
  const CX = SIZE / 2;
  const CY = SIZE / 2;
  const R = 86;
  const count = capabilities.length;

  const angles = useMemo(
    () => capabilities.map((_, idx) => (-Math.PI / 2) + (idx * (Math.PI * 2)) / count),
    [capabilities, count],
  );

  const scorePoints = capabilities
    .map((cap, idx) => {
      const r = R * Math.max(0.05, Math.min(1, cap.score));
      return `${CX + Math.cos(angles[idx]) * r},${CY + Math.sin(angles[idx]) * r}`;
    })
    .join(' ');

  const confidencePoints = capabilities
    .map((cap, idx) => {
      const r = R * Math.max(0.05, Math.min(1, cap.confidence));
      return `${CX + Math.cos(angles[idx]) * r},${CY + Math.sin(angles[idx]) * r}`;
    })
    .join(' ');

  const overlayPoints = overlay
    ? capabilities
        .map((cap, idx) => {
          const r = R * Math.max(0.05, Math.min(1, overlay.scores[cap.dimension] ?? 0));
          return `${CX + Math.cos(angles[idx]) * r},${CY + Math.sin(angles[idx]) * r}`;
        })
        .join(' ')
    : null;

  return (
    <div className="grid place-items-center">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="能力雷达图">
        {[0.25, 0.5, 0.75, 1].map((ratio) => (
          <polygon
            key={ratio}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={1}
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
            strokeWidth={1}
          />
        ))}

        {overlayPoints && (
          <polygon
            points={overlayPoints}
            fill={`${overlay!.color}33`}
            stroke={overlay!.color}
            strokeWidth={1.5}
            strokeDasharray={overlay!.dashed ? '4 3' : undefined}
          />
        )}

        <polygon
          points={confidencePoints}
          fill="none"
          stroke="#60a5fa"
          strokeWidth={1.4}
          strokeDasharray="3 3"
        />

        <polygon
          points={scorePoints}
          fill="rgba(29,78,216,0.22)"
          stroke="#1d4ed8"
          strokeWidth={1.8}
        />

        {capabilities.map((cap, idx) => {
          const lx = CX + Math.cos(angles[idx]) * (R + 14);
          const ly = CY + Math.sin(angles[idx]) * (R + 14);
          return (
            <text
              key={cap.dimension}
              x={lx}
              y={ly}
              textAnchor={Math.abs(Math.cos(angles[idx])) < 0.2 ? 'middle' : Math.cos(angles[idx]) > 0 ? 'start' : 'end'}
              style={{ fontSize: 10, fill: '#475569' }}
            >
              {cap.dimension}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
