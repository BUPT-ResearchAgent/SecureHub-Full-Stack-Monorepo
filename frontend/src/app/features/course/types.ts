import type { CapabilityDTO, EvidenceChunkDTO, ResourceType as SSEResourceType } from '@/lib/sse.types';

export type ResourceType = SSEResourceType;

export type PersonaDimensionKey =
  | 'base_knowledge'
  | 'cognitive_style'
  | 'weak_points'
  | 'preferred_modality'
  | 'time_budget'
  | 'target_direction'
  | 'motivation';

export type LearningPersona = {
  userId: string;
  dimensions: Record<PersonaDimensionKey, string>;
  completeness: number;
  updatedAt: string;
};

export type LearningPathNode = {
  id: string;
  label: string;
  status: 'locked' | 'ready' | 'active' | 'done';
  priority: number;
};

export type LearningPathEdge = {
  id: string;
  source: string;
  target: string;
};

export type LearningPath = {
  courseId: string;
  nodes: LearningPathNode[];
  edges: LearningPathEdge[];
  milestones: Array<{ id: string; title: string; week: number }>;
};

export type ResourceItem = {
  id: string;
  type: ResourceType;
  title: string;
  status: 'idle' | 'generating' | 'ready' | 'failed';
  content: string;
  evidenceRefs: EvidenceChunkDTO[];
  qualityScore?: number;
  errorCode?: string;
  errorMessage?: string;
};

export type AssessmentReport = {
  score: number;
  scoreVector: Record<string, number>;
  feedback: string[];
  updatedProfile: Partial<LearningPersona['dimensions']>;
  updatedCapabilities?: CapabilityDTO[];
};

export type CourseProgressEvent = {
  nodeName: string;
  status: string;
  percentage: number;
};
