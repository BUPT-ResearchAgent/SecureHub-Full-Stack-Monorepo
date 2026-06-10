export type ResourceType = 'doc' | 'ppt' | 'mindmap' | 'quiz' | 'lab' | 'video' | 'readings';

export type CapabilityDTO = {
  dimension: string;
  score: number;
  confidence: number;
  evidence_count: number;
};

export type ProfileDTO = {
  user_id: string;
  dimensions: Record<string, unknown>;
  capabilities: CapabilityDTO[];
  updated_at: string;
};

export type GeneratedResourceDTO = {
  id: string;
  user_id?: string;
  course_id?: string;
  resource_type: ResourceType;
  title: string;
  created_at: string;
  quality_score?: number | null;
};

export type EvidenceChunkDTO = {
  chunk_id: string;
  document_id: string;
  source_url?: string | null;
  platform?: string | null;
  author?: string | null;
  published_at?: string | null;
  fetched_at?: string | null;
  rights_note?: string | null;
  asset_type?: string | null;
  excerpt: string;
  page_no?: number | null;
  chapter?: string | null;
  timestamp?: number | null;
  reliability?: number | null;
  metadata?: {
    collection_mode?: 'manual' | 'api' | 'scrapling' | 'mediacrawler' | 'mindspider_reference';
    [key: string]: unknown;
  };
};

export type AgentRunDTO = {
  id?: string;
  run_id?: string;
  parent_run_id?: string | null;
  workflow_name?: string;
  agent_name: string;
  skill_name: string;
  status: string;
  duration_ms?: number | null;
  quality_score?: number | null;
  created_at?: string;
};

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
  };
};

export type ErrorEvent = {
  event: 'error';
  data: {
    code?: string;
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
