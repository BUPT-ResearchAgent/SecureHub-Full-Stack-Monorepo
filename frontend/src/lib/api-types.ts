export type JsonObject = Record<string, unknown>;

export interface CapabilityDTO {
  dimension: string;
  score: number;
  confidence: number;
  evidence_count: number;
}

export type CapabilityRadarDTO = CapabilityDTO;

export interface ProfileDTO {
  user_id: string;
  dimensions: JsonObject;
  capabilities: CapabilityDTO[];
  updated_at: string;
}

export interface GeneratedResourceDTO {
  id: string;
  resource_type: ResourceType;
  title: string;
  content?: JsonObject | null;
  object_key?: string | null;
  evidence_chunk_ids: string[];
  quality_score: number;
  status: 'generating' | 'ready' | 'failed';
  user_id?: string;
  course_id?: string;
  created_at?: string;
}

export type ResourceType = 'doc' | 'ppt' | 'mindmap' | 'quiz' | 'lab' | 'video' | 'readings';

export type EvidenceCollectionMode =
  | 'manual'
  | 'api'
  | 'scrapling'
  | 'mediacrawler'
  | 'mindspider_reference';

export interface EvidenceChunkDTO {
  chunk_id: string;
  document_id: string;
  /** Primary evidence text field. Renderers must prefer `chunk_text` over legacy `excerpt`. */
  chunk_text: string;
  /** Legacy fallback kept for older mock/backend payloads. */
  excerpt?: string | null;
  score: number;
  platform: string;
  rights_note: string;
  source_url: string | null;
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
}

export interface AgentRunDTO {
  id?: string;
  run_id?: string;
  parent_run_id?: string | null;
  workflow_name?: string;
  agent_name: string;
  skill_name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | string;
  duration_ms?: number | null;
  quality_score?: number | null;
  provider?: string | null;
  model?: string | null;
  token_usage?: JsonObject | null;
  created_at?: string;
}

export interface CoursePlanRequest {
  user_id: string;
  target_node_id: string;
  options?: JsonObject | null;
}

export interface LearningPathNodeDTO {
  node_id: string;
  title: string;
  status: 'locked' | 'ready' | 'in_progress' | 'done';
  prerequisites: string[];
}

export interface CoursePlanResponse {
  course_id: string;
  path: LearningPathNodeDTO[];
}

export type LearningPathDTO = CoursePlanResponse;

export interface ResourceGenerateRequest {
  type: ResourceType;
  kp_id: string;
  user_id: string;
  options?: JsonObject | null;
}

export interface AgentTraceDTO {
  run_id: string;
  parent_run_id?: string | null;
  agent_name: string;
  skill_name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  duration_ms?: number | null;
  quality_score?: number | null;
  provider?: string | null;
  model?: string | null;
  token_usage?: JsonObject | null;
}

export interface TutorAskRequest {
  user_id: string;
  course_id: string;
  question: string;
  context?: JsonObject | null;
}

export interface AssessmentRunRequest {
  user_id: string;
  course_id: string;
  answers: JsonObject[];
}

export interface AssessmentRunResponse {
  score: number;
  feedback: string;
  updated_capabilities: CapabilityDTO[];
}

export interface LLMHealthDTO {
  provider: string;
  model: string;
  mode: 'real' | 'fixture' | 'fallback';
  live_enabled: boolean;
  status: 'available' | 'degraded' | 'error' | 'unknown';
  last_error: string | null;
  rate_limit_state?: {
    used?: number;
    limit?: number;
    reset_at?: string;
  } | null;
}
