import { EdgeLabelRenderer, getBezierPath, type EdgeProps } from 'reactflow';
import type { EdgeStatus } from './types';

export type WorkflowEdgeData = {
  status: EdgeStatus;
  label?: string;
};

export function AnimatedWorkflowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps<WorkflowEdgeData>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.24,
  });
  const status = data?.status ?? 'idle';
  const active = status === 'active';
  const done = status === 'done';
  const stroke = active ? '#003399' : done ? '#16a34a' : '#cbd5e1';

  return (
    <>
      <path
        id={id}
        d={edgePath}
        fill="none"
        markerEnd={markerEnd}
        className={active ? 'workflow-edge-active' : undefined}
        style={{
          stroke,
          strokeWidth: active ? 2.5 : 1.6,
          strokeDasharray: status === 'idle' ? '6 8' : undefined,
        }}
      />
      {active && (
        <circle r="4" fill="#003399" opacity="0.92">
          <animateMotion dur="1.15s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute rounded-full border border-slate-200 bg-white/90 px-2 py-0.5 text-[10px] font-medium text-slate-500 shadow-sm"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
