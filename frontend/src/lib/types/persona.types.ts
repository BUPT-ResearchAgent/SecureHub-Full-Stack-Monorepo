// Status: mock
// 画像产品化模型：维度状态 / 挑战 / 叙事 / 教师介入。
// 4-B-3 引入。所有 mock 数据要求纯函数化生成，便于测试。

export type PersonaDimensionKey =
  | 'base_knowledge'
  | 'cognitive_style'
  | 'weak_points'
  | 'preferred_modality'
  | 'time_budget'
  | 'target_direction'
  | 'motivation';

export type PersonaDimensionStatus =
  | 'unknown'
  | 'detected'
  | 'verified'
  | 'challenged'
  | 'recently-updated';

export type PersonaDimensionNode = {
  key: PersonaDimensionKey | string;
  label: string;
  value?: string;
  confidence: number; // 0-1
  status: PersonaDimensionStatus;
  evidenceMessageIds?: string[];
  parentKey?: string;
  children?: PersonaDimensionNode[];
  // 教师注入的自定义维度
  custom?: boolean;
  // 教师评语片段
  teacherNote?: string;
};

export type PersonaChallengeQuestion = {
  id: string;
  dimension: PersonaDimensionKey | string;
  prompt: string;
  expectedKeywords: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  rationale: string;
};

export type PersonaChallengeOutcome =
  | { kind: 'accepted'; confidenceDelta: number }
  | { kind: 'partial'; confidenceDelta: number }
  | { kind: 'rejected'; confidenceDelta: number };

export type PersonaChallengeAttempt = {
  questionId: string;
  dimension: PersonaDimensionKey | string;
  answer: string;
  outcome: PersonaChallengeOutcome;
  evaluatedAt: string;
};

export type PersonaNarrativeSegment = {
  text: string;
  highlights: string[]; // 关键词高亮
  generatedAt: string;
  dimensionKeys: Array<PersonaDimensionKey | string>;
};

export type ClassPersonaClusterPoint = {
  id: string;
  label: string; // 聚类名（"案例驱动"）
  studentCount: number;
  axisX: number; // 知识深度 0-1
  axisY: number; // 学习目标偏向 0-1
  dominantDimension: PersonaDimensionKey | string;
  studentIds: string[];
  color: string;
};

export type TeacherPersonaDimension = {
  key: string;
  label: string;
  description: string;
  challenges: PersonaChallengeQuestion[];
  createdAt: string;
};
