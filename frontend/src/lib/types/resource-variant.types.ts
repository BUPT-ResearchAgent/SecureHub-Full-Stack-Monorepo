// Status: mock
// 资源变体 / 剧本台词卡 / 智能体辩论 / 资源溯源回放。
// 4-B-3 引入。

import type { ResourceType, EvidenceChunkDTO } from '@/lib/sse.types';

export type ResourceVariantKind = 'deep' | 'easy' | 'case';

export type ResourceVariant = {
  id: string;
  resourceType: ResourceType;
  kind: ResourceVariantKind;
  title: string;
  tagline: string;
  description: string;
  estimateMinutes: number;
  highlights: string[];
  preferredFor: string[]; // 哪些 persona 偏好
  content: string;
  evidenceRefs: EvidenceChunkDTO[];
};

export type ScreenplayCue = {
  id: string;
  actAt: number; // 第几秒
  agentId: string;
  agentName: string;
  avatar: string;
  line: string; // 台词
  durationMs: number;
};

export type ResourceScreenplay = {
  title: string;
  subtitle: string;
  resourceType: ResourceType;
  totalActs: number;
  cues: ScreenplayCue[];
};

export type AgentDebateExchange = {
  id: string;
  speakerAgent: string;
  speakerLabel: string;
  message: string;
  side: 'challenger' | 'defender';
  emittedAt: number; // 第几秒
};

export type AgentDebate = {
  topic: string;
  exchanges: AgentDebateExchange[];
  resolution: string;
  versionFrom: string;
  versionTo: string;
  diff: Array<{ type: 'add' | 'remove' | 'keep'; text: string }>;
};

export type ResourceReplayStep = {
  id: string;
  offsetMs: number;
  stage: 'request' | 'rag' | 'llm' | 'quality' | 'rebuild' | 'persist';
  agent: string;
  skill: string;
  summary: string;
  detail?: string;
  score?: number;
  evidenceCount?: number;
  outcome: 'success' | 'retry' | 'failed';
};

export type ResourceReplayTimeline = {
  resourceId: string;
  resourceType: ResourceType;
  startedAt: string;
  finishedAt: string;
  totalDurationMs: number;
  steps: ResourceReplayStep[];
};

export type ResourceIterationRequest = {
  id: string;
  resourceId: string;
  prompt: string;
  initiator: string;
  requestedAt: string;
};

export type ResourceVersionDiffSegment = {
  kind: 'add' | 'remove' | 'keep';
  text: string;
};

export type ResourceVersion = {
  version: number;
  createdAt: string;
  initiator: string;
  prompt?: string;
  content: string;
  qualityScore: number;
  diff?: ResourceVersionDiffSegment[];
};

export type ResourceTeacherSeedPrompt = {
  courseId: string;
  body: string;
  updatedAt: string;
  toneTags: string[];
};

export type ResourceSupervisionEntry = {
  id: string;
  studentName: string;
  resourceTitle: string;
  resourceType: ResourceType;
  agent: string;
  knowledgePoint: string;
  qualityScore: number;
  createdAt: string;
};
