import type { EvidenceChunkDTO, ResourceType } from '@/lib/sse.types';

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

export type SkillId = string;
export type NodeStatus = 'idle' | 'queued' | 'running' | 'success' | 'failed' | 'skipped';
export type EdgeStatus = 'idle' | 'active' | 'done';

export type AgentMeta = {
  id: AgentId;
  label: string;
  shortLabel: string;
  role: string;
  tools: string[];
  color: string;
};

export type WorkflowNode = {
  id: string;
  agentId: AgentId;
  skillId?: SkillId;
  label: string;
  position: { x: number; y: number };
  group?: string;
  initialStatus?: NodeStatus;
  resourceTypes?: ResourceType[];
};

export type WorkflowEdge = {
  id: string;
  source: string;
  target: string;
  dataLabel?: string;
};

export type WorkflowDefinition = {
  id: 'course_learning' | 'tutor_routing' | 'resource_generate' | 'assessment_run';
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  defaultEntry: string;
};

export type WorkflowNodeRun = {
  status: NodeStatus;
  startedAt?: number;
  durationMs?: number;
  qualityScore?: number;
  skillId?: SkillId;
  evidenceChunks?: EvidenceChunkDTO[];
  inputSummary?: Record<string, unknown>;
  outputSummary?: Record<string, unknown>;
  interactionLogs?: Array<{ time: string; text: string }>;
};

export type WorkflowEdgeRun = {
  status: EdgeStatus;
};

export type WorkflowRunState = {
  workflowId: WorkflowDefinition['id'];
  nodes: Record<string, WorkflowNodeRun>;
  edges: Record<string, WorkflowEdgeRun>;
  currentRunId?: string;
  overallQuality?: number;
  producedResources: Partial<Record<ResourceType, number>>;
  phase: 'idle' | 'running' | 'paused' | 'done';
};

export type WorkflowReplayStep =
  | { at: number; type: 'node'; nodeId: string; patch: Partial<WorkflowNodeRun> }
  | { at: number; type: 'edge'; edgeId: string; status: EdgeStatus }
  | { at: number; type: 'resources'; resources: ResourceType[] }
  | { at: number; type: 'quality'; score: number }
  | { at: number; type: 'phase'; phase: WorkflowRunState['phase'] };
