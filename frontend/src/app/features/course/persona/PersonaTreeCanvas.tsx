// Status: mock
// 画像树生长可视化：径向 SVG，从中心头像向 6 主分支展开，再到 2-3 子节点。
// 状态映射：unknown 灰虚 / detected 实色 / verified 实色光晕 / challenged 红边抖动 / recently-updated 蓝光脉冲。

import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import type { PersonaDimensionNode } from '@/lib/types/persona.types';

export type PersonaTreeCanvasProps = {
  studentName: string;
  studentInitial: string;
  branches: PersonaDimensionNode[];
  highlightKey?: string;
  onDimensionClick?: (node: PersonaDimensionNode) => void;
  reducedMotion?: boolean;
};

const SIZE = 520;
const CENTER = SIZE / 2;
const RING_BRANCH = 168;
const RING_LEAF = 230;

function polar(angle: number, radius: number): [number, number] {
  return [CENTER + Math.cos(angle) * radius, CENTER + Math.sin(angle) * radius];
}

function tone(status: PersonaDimensionNode['status']): {
  fill: string;
  stroke: string;
  strokeDash?: string;
  text: string;
} {
  switch (status) {
    case 'unknown':
      return { fill: 'rgba(148,163,184,0.18)', stroke: '#94a3b8', strokeDash: '4 4', text: '#64748b' };
    case 'detected':
      return { fill: 'rgba(37,99,235,0.16)', stroke: '#2563eb', text: '#1d4ed8' };
    case 'verified':
      return { fill: 'rgba(16,185,129,0.22)', stroke: '#10b981', text: '#047857' };
    case 'challenged':
      return { fill: 'rgba(244,114,182,0.18)', stroke: '#ec4899', strokeDash: '6 3', text: '#be185d' };
    case 'recently-updated':
      return { fill: 'rgba(37,99,235,0.32)', stroke: '#1d4ed8', text: '#1e3a8a' };
    default:
      return { fill: 'rgba(148,163,184,0.18)', stroke: '#94a3b8', text: '#64748b' };
  }
}

export function PersonaTreeCanvas({
  studentName,
  studentInitial,
  branches,
  highlightKey,
  onDimensionClick,
  reducedMotion,
}: PersonaTreeCanvasProps) {
  const [hoverKey, setHoverKey] = useState<string | null>(null);

  const layout = useMemo(() => {
    const branchCount = branches.length || 1;
    return branches.map((branch, idx) => {
      const angle = (-Math.PI / 2) + (idx * (Math.PI * 2)) / branchCount;
      const [bx, by] = polar(angle, RING_BRANCH);
      const children = (branch.children ?? []).map((child, childIdx) => {
        const totalLeaves = (branch.children ?? []).length || 1;
        const spread = Math.PI / 4;
        const leafAngle = angle + (childIdx - (totalLeaves - 1) / 2) * (spread / Math.max(1, totalLeaves - 1));
        const [lx, ly] = polar(leafAngle, RING_LEAF);
        return { node: child, x: lx, y: ly };
      });
      return { branch, x: bx, y: by, angle, children };
    });
  }, [branches]);

  const animateDuration = reducedMotion ? 0 : 0.6;

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[520px]">
      <svg
        className="block h-full w-full"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="学习画像树"
      >
        <defs>
          <radialGradient id="persona-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#dbeafe" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0.05} />
          </radialGradient>
        </defs>
        <circle cx={CENTER} cy={CENTER} r={RING_BRANCH + 70} fill="url(#persona-core)" />

        {layout.map(({ branch, x, y, children }, idx) => {
          const t = tone(branch.status);
          const isHighlight = highlightKey === branch.key;
          return (
            <g key={branch.key}>
              <motion.line
                initial={reducedMotion ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: animateDuration, delay: idx * 0.08, ease: 'easeOut' }}
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                stroke={branch.status === 'unknown' ? '#cbd5f5' : t.stroke}
                strokeOpacity={branch.status === 'unknown' ? 0.55 : 0.7}
                strokeWidth={branch.status === 'unknown' ? 1.2 : 2}
                strokeDasharray={t.strokeDash}
              />
              {children.map((leaf, leafIdx) => {
                const lt = tone(leaf.node.status);
                return (
                  <g key={leaf.node.key}>
                    <motion.line
                      initial={reducedMotion ? false : { pathLength: 0 }}
                      animate={{ pathLength: 1 }}
                      transition={{ duration: animateDuration * 0.8, delay: 0.2 + idx * 0.08 + leafIdx * 0.05 }}
                      x1={x}
                      y1={y}
                      x2={leaf.x}
                      y2={leaf.y}
                      stroke={leaf.node.status === 'unknown' ? '#cbd5f5' : lt.stroke}
                      strokeOpacity={leaf.node.status === 'unknown' ? 0.4 : 0.5}
                      strokeWidth={1.4}
                      strokeDasharray={lt.strokeDash}
                    />
                    <motion.circle
                      initial={reducedMotion ? false : { scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.45, delay: 0.3 + idx * 0.08 + leafIdx * 0.05, ease: 'backOut' }}
                      cx={leaf.x}
                      cy={leaf.y}
                      r={14}
                      fill={lt.fill}
                      stroke={lt.stroke}
                      strokeWidth={leaf.node.status === 'unknown' ? 1 : 1.6}
                      style={{ cursor: onDimensionClick ? 'pointer' : 'default' }}
                      onClick={() => onDimensionClick?.(leaf.node)}
                      onMouseEnter={() => setHoverKey(leaf.node.key)}
                      onMouseLeave={() => setHoverKey(null)}
                    />
                    <text x={leaf.x} y={leaf.y + 28} textAnchor="middle" style={{ fontSize: 10, fill: lt.text }}>
                      {leaf.node.label}
                    </text>
                  </g>
                );
              })}

              <motion.circle
                initial={reducedMotion ? false : { scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.5, delay: idx * 0.08, ease: 'backOut' }}
                cx={x}
                cy={y}
                r={26}
                fill={t.fill}
                stroke={t.stroke}
                strokeWidth={branch.status === 'unknown' ? 1.4 : 2}
                strokeDasharray={t.strokeDash}
                style={{ cursor: onDimensionClick ? 'pointer' : 'default' }}
                onClick={() => onDimensionClick?.(branch)}
                onMouseEnter={() => setHoverKey(branch.key)}
                onMouseLeave={() => setHoverKey(null)}
              />
              {isHighlight && !reducedMotion && (
                <motion.circle
                  cx={x}
                  cy={y}
                  r={32}
                  fill="none"
                  stroke="#1d4ed8"
                  strokeWidth={2}
                  initial={{ opacity: 0.8, scale: 1 }}
                  animate={{ opacity: [0.8, 0, 0.7, 0], scale: [1, 1.4, 1.1, 1.5] }}
                  transition={{ duration: 2.6, repeat: Infinity, repeatDelay: 1.5, ease: 'easeOut' }}
                />
              )}
              {branch.status === 'challenged' && !reducedMotion && (
                <motion.circle
                  cx={x}
                  cy={y}
                  r={28}
                  fill="none"
                  stroke="#ec4899"
                  strokeWidth={1.6}
                  initial={{ x: 0 }}
                  animate={{ x: [0, -3, 3, -2, 2, 0] }}
                  transition={{ duration: 0.8, repeat: 1 }}
                />
              )}
              <text x={x} y={y + 4} textAnchor="middle" style={{ fontSize: 12, fontWeight: 600, fill: t.text }}>
                {branch.label}
              </text>
            </g>
          );
        })}

        <circle cx={CENTER} cy={CENTER} r={50} fill="#1d4ed8" />
        <text x={CENTER} y={CENTER - 4} textAnchor="middle" style={{ fontSize: 22, fontWeight: 700, fill: 'white' }}>
          {studentInitial}
        </text>
        <text x={CENTER} y={CENTER + 18} textAnchor="middle" style={{ fontSize: 11, fill: 'rgba(255,255,255,0.85)' }}>
          {studentName}
        </text>
      </svg>

      {hoverKey && (
        <div className="pointer-events-none absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-white/90 px-3 py-1 text-[11px] text-slate-600 shadow ring-1 ring-slate-200">
          <Sparkles className="mr-1 inline h-3 w-3 text-brand-blue-500" />
          点击节点查看证据片段
        </div>
      )}
    </div>
  );
}
