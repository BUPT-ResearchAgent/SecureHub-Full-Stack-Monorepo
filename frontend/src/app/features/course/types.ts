import type { CapabilityDTO, EvidenceChunkDTO, ResourceType as SSEResourceType } from '@/lib/sse.types';
import type { WorkflowRunStatus } from '@/lib/workflow-run.types';

export type ResourceType = SSEResourceType;

export type PptDeckLayoutId = 'cover' | 'statement' | 'timeline' | 'compare' | 'cards' | 'closing';

export type PptCodeDemo = {
  language?: string;
  before?: string;
  after?: string;
  caption?: string;
};

export type PptDeckSlide = {
  layout_id: PptDeckLayoutId;
  title: string;
  claim: string;
  bullets: string[];
  code_demo?: PptCodeDemo;
  evidence_refs: string[];
  speaker_note?: string;
};

export type PptDeckSpec = {
  title: string;
  theme: string;
  slides: PptDeckSlide[];
};

export type PptRenderMode = 'securehub_swiss_v1';

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
  description?: string;
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
  workflowRunId?: string;
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
  deckSpec?: PptDeckSpec;
  renderMode?: PptRenderMode | string;
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

/**
 * The course surface deliberately accepts only product workflows with a
 * stable adapter.  This is not an LLM intent classifier: callers must choose
 * one of the five supported actions before a durable root can be created.
 */
export const SUPPORTED_TASK_INTENTS = [
  'build_persona',
  'plan_course',
  'generate_resource',
  'ask_tutor',
  'run_assessment',
] as const;

export type SupportedTaskIntent = (typeof SUPPORTED_TASK_INTENTS)[number];

export type CourseTaskContext = {
  userId: string;
  courseId: string;
  kpId: string;
  currentPathNodeIds: string[];
};

export type CourseTaskCommand =
  | {
      intent: 'build_persona';
      context: CourseTaskContext;
      payload: { message: string; history: Array<Record<string, unknown>> };
    }
  | {
      intent: 'plan_course';
      context: CourseTaskContext;
      payload: { targetNodeId: string; depth?: number };
    }
  | {
      intent: 'generate_resource';
      context: CourseTaskContext;
      payload: { resourceType: ResourceType; options?: Record<string, unknown> };
    }
  | {
      intent: 'ask_tutor';
      context: CourseTaskContext;
      payload: { question: string };
    }
  | {
      intent: 'run_assessment';
      context: CourseTaskContext;
      payload: {
        answers: Array<Record<string, unknown>>;
        quizArtifactId?: string;
        assessmentAssignmentId?: string;
      };
    };

export type CourseWorkflowRoot = {
  runId: string;
  intent: SupportedTaskIntent;
  workflow: string;
  status: WorkflowRunStatus;
  mode: 'real' | 'fixture';
  provider?: string | null;
  model?: string | null;
  evidenceCount: number;
  artifactIds: string[];
  lastSequence: number;
  updatedAt: string;
  error?: { code: string; message: string; recoverable?: boolean };
};
