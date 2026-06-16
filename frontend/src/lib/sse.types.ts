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

/**
 * Closed enum for `EvidenceChunkDTO.collection_mode`.
 * See `docs/api/evidence-contract.md §4.2`.
 */
export type EvidenceCollectionMode =
  | 'manual'
  | 'api'
  | 'scrapling'
  | 'mediacrawler'
  | 'mindspider_reference';

/**
 * Wire-format evidence chunk — see `docs/api/evidence-contract.md` (v1, 2026-06-16).
 *
 * - Required: chunk_id, document_id, chunk_text, score, platform, rights_note.
 * - Conditionally required: `source_url` is required unless `platform === 'manual'`.
 * - All other fields optional.
 *
 * Backend Pydantic mirror: `backend/app/schemas/evidence.py::EvidenceChunkDTO`.
 */
export type EvidenceChunkDTO = {
  // identity
  chunk_id: string;
  document_id: string;
  // body
  chunk_text: string;
  score: number;
  // source identity
  platform: string;
  rights_note: string;
  // source link (conditional; null only when platform === 'manual')
  source_url: string | null;
  // optional display
  title?: string | null;
  author?: string | null;
  published_at?: string | null;
  fetched_at?: string | null;
  collection_mode?: EvidenceCollectionMode | null;
  asset_type?: string | null;
  page_no?: number | null;
  chapter?: string | null;
  timestamp?: number | null;
  license?: string | null;
  reliability?: number | null;
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
