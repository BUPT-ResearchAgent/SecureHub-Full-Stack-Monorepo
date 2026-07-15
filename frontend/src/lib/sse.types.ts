// EvidenceChunkDTO is defined in api-types:
// `chunk_text` is the primary text field, `excerpt` is legacy fallback only.
export type {
  AgentRunDTO,
  CapabilityDTO,
  EvidenceChunkDTO,
  EvidenceCollectionMode,
  GeneratedResourceDTO,
  JsonObject,
  LLMHealthDTO,
  LearningPathDTO,
  ProfileDTO,
  ResourceType,
} from './api-types';

import type { AgentRunDTO, EvidenceChunkDTO, ResourceType } from './api-types';

export type SSEErrorCode =
  | 'ApiKeyMissing'
  | 'InsufficientEvidence'
  | 'sse_reconnecting'
  | 'BudgetExceeded'
  | 'LLMProviderError'
  | 'QualityCheckFailed'
  | 'SkillTimeout'
  | 'RateLimited'
  | 'EmptyStream'
  | 'NetworkError'
  | 'sse_error'
  | 'InternalError'
  | 'UnknownError';

export type ProgressEvent = {
  event: 'progress';
  data: {
    node_name: string;
    agent_id?: string;
    skill_id?: string;
    percentage?: number;
    status: 'running' | 'done' | 'failed';
  };
};

export type EvidenceEvent = {
  event: 'evidence';
  data: EvidenceChunkDTO[];
};

export type TokenEvent = {
  event: 'token';
  data: {
    content: string;
    index?: number;
  };
};

export type ArtifactEvent = {
  event: 'artifact';
  data: {
    resource_id: string;
    resource_type: ResourceType;
    object_key?: string;
    title: string;
    quality_score?: number | null;
  };
};

export type TraceEvent = {
  event: 'trace';
  data: AgentRunDTO;
};

export type DoneEvent = {
  event: 'done';
  data: {
    run_id: string;
    final_output_ref: string;
    quality_score: number;
    status?: 'succeeded' | 'cancelled';
  };
};

export type ErrorEvent = {
  event: 'error';
  data: {
    code?: SSEErrorCode | string;
    message: string;
    recoverable?: boolean;
  };
};

export type SSEEvent =
  | ProgressEvent
  | EvidenceEvent
  | TokenEvent
  | ArtifactEvent
  | TraceEvent
  | DoneEvent
  | ErrorEvent;
