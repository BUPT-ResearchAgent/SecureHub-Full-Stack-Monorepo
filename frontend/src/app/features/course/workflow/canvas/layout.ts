import type { AgentId, WorkflowDefinition, WorkflowNode } from '../types';

/**
 * 9 智能体在圆形 orb 画布上的位置。
 *
 * 标准布局（compact = false）：career_planner 在左、task_orchestrator 居中、
 * 4 个生产者在右侧并行环、outcome_evaluator 在最右、policy/job 浮在底部。
 *
 * Chat-first compact 布局：把上述坐标整体压缩 ~30%，让画布在 380–420px 宽
 * 的右栏内仍能放下 9 个 56px orb，同时保留方向感。
 */
const standardPositions: Record<AgentId, { x: number; y: number }> = {
  career_planner: { x: 36, y: 184 },
  task_orchestrator: { x: 224, y: 184 },
  doc_archivist: { x: 432, y: 36 },
  competition_advisor: { x: 504, y: 140 },
  topic_explorer: { x: 504, y: 240 },
  hot_analyst: { x: 432, y: 332 },
  outcome_evaluator: { x: 660, y: 184 },
  policy_interpreter: { x: 144, y: 360 },
  job_analyst: { x: 312, y: 376 },
};

const compactPositions: Record<AgentId, { x: number; y: number }> = {
  career_planner: { x: 14, y: 132 },
  task_orchestrator: { x: 132, y: 132 },
  doc_archivist: { x: 226, y: 30 },
  competition_advisor: { x: 262, y: 108 },
  topic_explorer: { x: 262, y: 184 },
  hot_analyst: { x: 226, y: 244 },
  outcome_evaluator: { x: 340, y: 136 },
  policy_interpreter: { x: 80, y: 280 },
  job_analyst: { x: 196, y: 296 },
};

export function applyOrbLayout(
  workflow: WorkflowDefinition,
  options?: { compact?: boolean },
): WorkflowNode[] {
  const positions = options?.compact ? compactPositions : standardPositions;
  return workflow.nodes.map((node) => ({
    ...node,
    position: positions[node.agentId] ?? node.position,
  }));
}

export const ORB_DIAMETER = 72;
export const ORB_DIAMETER_COMPACT = 56;
