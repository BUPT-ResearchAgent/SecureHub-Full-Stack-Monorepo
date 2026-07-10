// Status: mock
//
// 9 智能体的固定布局（圆形 + 中心 task_orchestrator）+ 视觉信息。

export type AgentId =
  | 'policy_interpreter'
  | 'hot_analyst'
  | 'job_analyst'
  | 'competition_advisor'
  | 'career_planner'
  | 'topic_explorer'
  | 'doc_archivist'
  | 'task_orchestrator'
  | 'outcome_evaluator';

export type AgentNodeMeta = {
  id: AgentId;
  label: string;
  emoji: string;
  color: string;
  /** 位置百分比（0-1），相对画布左上角。 */
  x: number;
  y: number;
};

export const SHOWCASE_AGENTS: AgentNodeMeta[] = [
  { id: 'task_orchestrator', label: '任务编排', emoji: '🧭', color: '#1e3a8a', x: 0.5, y: 0.5 },
  { id: 'career_planner', label: '画像规划', emoji: '🎯', color: '#0ea5e9', x: 0.5, y: 0.12 },
  { id: 'doc_archivist', label: '资料归档', emoji: '📚', color: '#7c3aed', x: 0.85, y: 0.28 },
  { id: 'topic_explorer', label: '主题探索', emoji: '🔍', color: '#9333ea', x: 0.92, y: 0.62 },
  { id: 'competition_advisor', label: '竞赛顾问', emoji: '🏆', color: '#f59e0b', x: 0.78, y: 0.88 },
  { id: 'outcome_evaluator', label: '效果评估', emoji: '✅', color: '#10b981', x: 0.22, y: 0.88 },
  { id: 'job_analyst', label: '岗位分析', emoji: '💼', color: '#ea580c', x: 0.08, y: 0.62 },
  { id: 'hot_analyst', label: '热点分析', emoji: '🔥', color: '#dc2626', x: 0.15, y: 0.28 },
  { id: 'policy_interpreter', label: '政策解读', emoji: '⚖️', color: '#0f766e', x: 0.35, y: 0.08 },
];

/** Showcase 用的固定边：以 task_orchestrator 为中心。 */
export const SHOWCASE_EDGES: { id: string; source: AgentId; target: AgentId }[] = [
  { id: 'e1', source: 'career_planner', target: 'task_orchestrator' },
  { id: 'e2', source: 'task_orchestrator', target: 'doc_archivist' },
  { id: 'e3', source: 'task_orchestrator', target: 'topic_explorer' },
  { id: 'e4', source: 'task_orchestrator', target: 'competition_advisor' },
  { id: 'e5', source: 'task_orchestrator', target: 'job_analyst' },
  { id: 'e6', source: 'task_orchestrator', target: 'hot_analyst' },
  { id: 'e7', source: 'task_orchestrator', target: 'policy_interpreter' },
  { id: 'e8', source: 'doc_archivist', target: 'outcome_evaluator' },
  { id: 'e9', source: 'topic_explorer', target: 'outcome_evaluator' },
  { id: 'e10', source: 'competition_advisor', target: 'outcome_evaluator' },
  { id: 'e11', source: 'outcome_evaluator', target: 'career_planner' },
];

export function getAgentMeta(id: AgentId): AgentNodeMeta {
  return SHOWCASE_AGENTS.find((a) => a.id === id) ?? SHOWCASE_AGENTS[0];
}
