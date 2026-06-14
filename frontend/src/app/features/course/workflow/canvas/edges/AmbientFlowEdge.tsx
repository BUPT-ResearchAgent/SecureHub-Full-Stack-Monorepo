import { useState } from 'react';
import { EdgeLabelRenderer, getBezierPath, type EdgeProps } from 'reactflow';
import type { EdgeStatus } from '../../types';

export type AmbientEdgeData = {
  status: EdgeStatus;
  label?: string;
  /** Chat-first compact 模式下，边标签默认不显示，仅 hover/激活时浮出。 */
  compact?: boolean;
};

export function AmbientFlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps<AmbientEdgeData>) {
  const [hovered, setHovered] = useState(false);
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.22,
  });

  const status = data?.status ?? 'idle';
  const isActive = status === 'active';
  const isDone = status === 'done';
  const stroke = isActive ? '#003399' : isDone ? '#10b981' : '#cbd5e1';
  const compact = data?.compact ?? false;
  const showLabel = data?.label && (compact ? hovered || isActive : true);

  return (
    <>
      {/* 用一条加粗透明路径捕获 hover，避免细线难以悬停 */}
      {compact && data?.label && (
        <path
          d={edgePath}
          fill="none"
          stroke="transparent"
          strokeWidth={16}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        />
      )}

      <path
        id={id}
        d={edgePath}
        fill="none"
        markerEnd={markerEnd}
        style={{
          stroke,
          strokeOpacity: isActive ? 0.92 : isDone ? 0.55 : 0.35,
          strokeWidth: isActive ? (compact ? 1.5 : 1.8) : compact ? 0.9 : 1.1,
          strokeDasharray: status === 'idle' ? '3 8' : undefined,
          strokeLinecap: 'round',
        }}
      />

      {isActive && (
        <>
          <path
            d={edgePath}
            fill="none"
            style={{
              stroke: '#003399',
              strokeOpacity: compact ? 0.12 : 0.18,
              strokeWidth: compact ? 4 : 6,
              strokeLinecap: 'round',
            }}
          />
          <circle r={compact ? 2.4 : 3} fill="#003399" opacity={0.92}>
            <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
          </circle>
          <circle r={compact ? 1.6 : 2} fill="#5b8def" opacity={0.85}>
            <animateMotion dur="1.5s" begin="0.6s" repeatCount="indefinite" path={edgePath} />
          </circle>
        </>
      )}

      {showLabel && (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute select-none rounded-full bg-white/90 px-1.5 py-0.5 text-[9px] font-medium text-slate-500 shadow-sm ring-1 ring-slate-200/80 backdrop-blur"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
