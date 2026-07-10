// Status: mock
// 多路径并存 / 节点难度热力 / 导师标注 / 动态重规划 / 资源推送时间轴。
// 4-B-3 引入。

export type PathStrategy = 'sprint' | 'deep' | 'practice';

export type PathNodeDifficulty = 'easy' | 'fit' | 'challenge' | 'hard';

export type PathMentorAgent =
  | 'doc_archivist'
  | 'topic_explorer'
  | 'competition_advisor'
  | 'career_planner'
  | 'job_analyst'
  | 'policy_interpreter'
  | 'hot_analyst';

export type CandidatePathNode = {
  id: string;
  label: string;
  knowledgePointId: string;
  status: 'locked' | 'ready' | 'active' | 'done';
  difficulty: PathNodeDifficulty;
  importance: number; // 0-1，节点 size
  prerequisiteMastery: number; // 学生已掌握的前置 0-1
  estimateMinutes: number;
  mentorAgent: PathMentorAgent;
  mentorReason: string;
  scheduledFor?: string; // ISO date
};

export type CandidatePathEdge = {
  id: string;
  source: string;
  target: string;
};

export type CandidatePath = {
  id: string;
  strategy: PathStrategy;
  label: string;
  description: string;
  totalDays: number;
  daily: string;
  highlights: string[];
  recommendedForPersona: string[];
  nodes: CandidatePathNode[];
  edges: CandidatePathEdge[];
};

export type ReplanReason = 'over_perform' | 'struggling' | 'manual' | 'teacher_injected';

export type PathReplanEvent = {
  id: string;
  reason: ReplanReason;
  triggeredAt: string;
  summary: string;
  addedNodeIds: string[];
  removedNodeIds: string[];
  message: string;
};

export type PushScheduleSlot = {
  id: string;
  scheduledAt: string;
  bucket: 'today' | 'tomorrow' | 'day_after' | 'weekend';
  bucketLabel: string;
  resourceType: 'doc' | 'video' | 'lab' | 'quiz' | 'reading';
  title: string;
  agent: PathMentorAgent;
  rationale: string;
  durationMinutes: number;
  status: 'scheduled' | 'opt_in' | 'opt_out';
};

export type TeacherPathInsertion = {
  id: string;
  studentId: string;
  insertedAt: string;
  nodeLabel: string;
  reason: string;
  dueAt: string;
};

export type ClassPathCompletionCell = {
  studentId: string;
  studentName: string;
  nodeId: string;
  completion: number; // 0-1
  attemptedAt?: string;
};

export type ClassPathCompletionMatrix = {
  nodeIds: string[];
  nodeLabels: string[];
  cells: ClassPathCompletionCell[];
};
