import type { AgentRunDTO, EvidenceChunkDTO, ResourceType } from './api-types';

export const WORKFLOW_EVENT_TYPES = [
  'progress',
  'evidence',
  'token',
  'artifact',
  'trace',
  'done',
  'error',
] as const;

export type WorkflowEventType = (typeof WORKFLOW_EVENT_TYPES)[number];

export type WorkflowRunMode = 'fixture' | 'real';

export type WorkflowRunStatus =
  | 'queued'
  | 'running'
  | 'reworking'
  | 'pausing'
  | 'paused'
  | 'waiting_approval'
  | 'cancelling'
  | 'cancelled'
  | 'succeeded'
  | 'failed'
  | 'blocked';

export type WorkflowNodeStatus =
  | 'pending'
  | 'ready'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'blocked'
  | 'cancelled'
  | 'skipped';

export type WorkflowEventCorrelation = {
  step_attempt_id?: string;
  agent_run_id?: string;
  provider_call_id?: string;
  stream_attempt?: number;
  node_id?: string;
  agent_id?: string;
  agent_name?: string;
  skill_id?: string;
  skill_name?: string;
};

export type WorkflowProgressPayload = WorkflowEventCorrelation & {
  node_name?: string;
  percentage?: number;
  status?: WorkflowRunStatus | WorkflowNodeStatus | string;
  root_status?: WorkflowRunStatus;
  node_status?: WorkflowNodeStatus;
  message?: string;
};

export type WorkflowEvidencePayload = WorkflowEventCorrelation & {
  items: EvidenceChunkDTO[];
  evidence_snapshot_ids?: string[];
};

export type WorkflowTokenPayload = WorkflowEventCorrelation & {
  content: string;
  index?: number;
  replace_draft?: boolean;
  replaces_stream_attempt?: number;
};

export type WorkflowArtifactPayload = WorkflowEventCorrelation & {
  resource_id: string;
  resource_type: ResourceType;
  object_key?: string | null;
  title: string;
  storage_status?: 'staging' | 'active' | 'orphaned' | 'deleted';
  quality_score?: number | null;
};

export type ProviderSwitch = {
  from_provider?: string;
  from_model?: string;
  to_provider?: string;
  to_model?: string;
  reason?: string;
  replace_draft?: boolean;
};

export type WorkflowTracePayload = WorkflowEventCorrelation &
  Partial<AgentRunDTO> & {
    id?: string;
    run_id?: string;
    status?: WorkflowNodeStatus | 'success' | 'error' | 'queued' | string;
    provider_switch?: ProviderSwitch;
    replace_draft?: boolean;
  };

export type WorkflowDonePayload = WorkflowEventCorrelation & {
  status: Extract<WorkflowRunStatus, 'succeeded' | 'cancelled'>;
  final_output_ref?: string | null;
  quality_score?: number | null;
  final_output?: Record<string, unknown> | null;
};

export type WorkflowErrorPayload = WorkflowEventCorrelation & {
  code: string;
  message: string;
  recoverable?: boolean;
  terminal?: boolean;
  status?: Extract<WorkflowRunStatus, 'failed' | 'blocked' | 'cancelled'>;
};

export type WorkflowEventPayloadByType = {
  progress: WorkflowProgressPayload;
  evidence: WorkflowEvidencePayload;
  token: WorkflowTokenPayload;
  artifact: WorkflowArtifactPayload;
  trace: WorkflowTracePayload;
  done: WorkflowDonePayload;
  error: WorkflowErrorPayload;
};

export type WorkflowEventEnvelope<T extends WorkflowEventType = WorkflowEventType> = {
  workflow_run_id: string;
  sequence: number;
  event_type: T;
  payload: WorkflowEventPayloadByType[T];
  created_at?: string;
  mode?: WorkflowRunMode;
  requested_provider?: string | null;
  requested_model?: string | null;
  provider?: string | null;
  model?: string | null;
  actual_provider?: string | null;
  actual_model?: string | null;
  step_attempt_id?: string;
  agent_run_id?: string;
  provider_call_id?: string;
  stream_attempt?: number;
};

export type WorkflowEvent =
  | (WorkflowEventEnvelope<'progress'> & { event_type: 'progress'; payload: WorkflowProgressPayload })
  | (WorkflowEventEnvelope<'evidence'> & { event_type: 'evidence'; payload: WorkflowEvidencePayload })
  | (WorkflowEventEnvelope<'token'> & { event_type: 'token'; payload: WorkflowTokenPayload })
  | (WorkflowEventEnvelope<'artifact'> & { event_type: 'artifact'; payload: WorkflowArtifactPayload })
  | (WorkflowEventEnvelope<'trace'> & { event_type: 'trace'; payload: WorkflowTracePayload })
  | (WorkflowEventEnvelope<'done'> & { event_type: 'done'; payload: WorkflowDonePayload })
  | (WorkflowEventEnvelope<'error'> & { event_type: 'error'; payload: WorkflowErrorPayload });

export type WorkflowRunStartRequest = {
  workflow: string;
  user_id: string;
  course_id?: string;
  input?: Record<string, unknown>;
  mode?: WorkflowRunMode;
  provider?: string;
  model?: string;
  stream?: boolean;
};

export type WorkflowRunStartResponse = {
  run_id: string;
  workflow: string;
  status: WorkflowRunStatus;
  events_url: string;
  cancel_url: string;
  mode: WorkflowRunMode;
  requested_provider?: string | null;
  requested_model?: string | null;
  provider?: string | null;
  model?: string | null;
  actual_provider?: string | null;
  actual_model?: string | null;
};

export type WorkflowRunNode = WorkflowEventCorrelation & {
  node_id: string;
  status: WorkflowNodeStatus;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  quality_score?: number | null;
};

export type WorkflowRunStatusResponse = {
  run_id: string;
  workflow: string;
  status: WorkflowRunStatus;
  mode: WorkflowRunMode;
  requested_provider?: string | null;
  requested_model?: string | null;
  provider?: string | null;
  model?: string | null;
  actual_provider?: string | null;
  actual_model?: string | null;
  child_runs?: WorkflowRunNode[];
  nodes?: WorkflowRunNode[];
  final_output?: Record<string, unknown> | null;
  error?: WorkflowErrorPayload | null;
};

export type WorkflowNodeViewState = {
  nodeId: string;
  status: WorkflowNodeStatus;
  agentId?: string;
  agentName?: string;
  skillId?: string;
  skillName?: string;
  stepAttemptId?: string;
  agentRunId?: string;
  durationMs?: number;
  qualityScore?: number;
};

export type WorkflowTokenDraft = {
  key: string;
  stepKey: string;
  providerCallId?: string;
  streamAttempt?: number;
  content: string;
  active: boolean;
  replacedAtSequence?: number;
};

export type WorkflowRunViewState = {
  runId: string;
  status: WorkflowRunStatus;
  mode?: WorkflowRunMode;
  requestedProvider?: string | null;
  requestedModel?: string | null;
  actualProvider?: string | null;
  actualModel?: string | null;
  nodes: Record<string, WorkflowNodeViewState>;
  evidence: Record<string, EvidenceChunkDTO>;
  artifacts: Record<string, WorkflowArtifactPayload>;
  traces: Record<string, WorkflowTracePayload>;
  tokenDrafts: Record<string, WorkflowTokenDraft>;
  activeStreamByStep: Record<string, string>;
  replacementPendingByStep: Record<string, boolean>;
  lastSequence: number;
  terminalEvent?: 'done' | 'error';
  error?: WorkflowErrorPayload;
  qualityScore?: number;
};

export const TERMINAL_WORKFLOW_STATUSES: ReadonlySet<WorkflowRunStatus> = new Set([
  'cancelled',
  'succeeded',
  'failed',
  'blocked',
]);

export function isWorkflowEventType(value: string): value is WorkflowEventType {
  return (WORKFLOW_EVENT_TYPES as readonly string[]).includes(value);
}

export function isTerminalWorkflowStatus(status: WorkflowRunStatus): boolean {
  return TERMINAL_WORKFLOW_STATUSES.has(status);
}

export function isWorkflowDraftReplacement(event: WorkflowEvent): boolean {
  if (event.event_type === 'token') {
    return Boolean(event.payload.replace_draft || event.payload.replaces_stream_attempt != null);
  }
  return event.event_type === 'trace' && Boolean(
    event.payload.replace_draft || event.payload.provider_switch?.replace_draft,
  );
}

export function createWorkflowRunViewState(runId: string): WorkflowRunViewState {
  return {
    runId,
    status: 'queued',
    nodes: {},
    evidence: {},
    artifacts: {},
    traces: {},
    tokenDrafts: {},
    activeStreamByStep: {},
    replacementPendingByStep: {},
    lastSequence: 0,
  };
}

export function reduceWorkflowEvent(
  state: WorkflowRunViewState,
  event: WorkflowEvent,
): WorkflowRunViewState {
  if (event.workflow_run_id !== state.runId || event.sequence <= state.lastSequence) {
    return state;
  }

  const next = withEnvelopeMetadata({ ...state, lastSequence: event.sequence }, event);
  if (next.terminalEvent) {
    return next;
  }

  switch (event.event_type) {
    case 'progress':
      return applyProgress(next, event);
    case 'evidence':
      return applyEvidence(next, event);
    case 'token':
      return applyToken(next, event);
    case 'artifact':
      return applyArtifact(next, event);
    case 'trace':
      return applyTrace(next, event);
    case 'done':
      return {
        ...next,
        status: event.payload.status,
        terminalEvent: 'done',
        error: undefined,
        qualityScore: event.payload.quality_score ?? next.qualityScore,
      };
    case 'error': {
      if (event.payload.terminal === false) {
        return { ...next, error: event.payload };
      }
      return {
        ...next,
        status: event.payload.status ?? 'failed',
        terminalEvent: 'error',
        error: event.payload,
      };
    }
  }
}

function withEnvelopeMetadata(
  state: WorkflowRunViewState,
  event: WorkflowEvent,
): WorkflowRunViewState {
  return {
    ...state,
    mode: event.mode ?? state.mode,
    requestedProvider: event.requested_provider ?? state.requestedProvider,
    requestedModel: event.requested_model ?? state.requestedModel,
    actualProvider: event.actual_provider ?? event.provider ?? state.actualProvider,
    actualModel: event.actual_model ?? event.model ?? state.actualModel,
  };
}

function applyProgress(
  state: WorkflowRunViewState,
  event: WorkflowEventEnvelope<'progress'>,
): WorkflowRunViewState {
  const payload = event.payload;
  const rootStatus = payload.root_status ?? asWorkflowRunStatus(payload.status);
  const nodeId = payload.node_id;
  if (!nodeId) {
    return rootStatus ? { ...state, status: rootStatus } : state;
  }

  const nodeStatus = payload.node_status ?? asWorkflowNodeStatus(payload.status) ?? 'running';
  return {
    ...state,
    nodes: {
      ...state.nodes,
      [nodeId]: {
        ...state.nodes[nodeId],
        nodeId,
        status: nodeStatus,
        agentId: payload.agent_id ?? state.nodes[nodeId]?.agentId,
        agentName: payload.agent_name ?? state.nodes[nodeId]?.agentName,
        skillId: payload.skill_id ?? state.nodes[nodeId]?.skillId,
        skillName: payload.skill_name ?? state.nodes[nodeId]?.skillName,
        stepAttemptId: payload.step_attempt_id ?? state.nodes[nodeId]?.stepAttemptId,
      },
    },
  };
}

function applyEvidence(
  state: WorkflowRunViewState,
  event: WorkflowEventEnvelope<'evidence'>,
): WorkflowRunViewState {
  const evidence = { ...state.evidence };
  for (const item of event.payload.items) {
    evidence[item.chunk_id] = item;
  }
  return { ...state, evidence };
}

function applyToken(
  state: WorkflowRunViewState,
  event: WorkflowEventEnvelope<'token'>,
): WorkflowRunViewState {
  const payload = event.payload;
  const stepKey = payload.step_attempt_id ?? payload.node_id ?? 'root';
  const draftKey = makeDraftKey(stepKey, payload.provider_call_id, payload.stream_attempt);
  const activeDraftKey = state.activeStreamByStep[stepKey];
  const requiresReplacement = Boolean(
    payload.replace_draft ||
      payload.replaces_stream_attempt != null ||
      state.replacementPendingByStep[stepKey],
  );

  if (activeDraftKey && activeDraftKey !== draftKey && !requiresReplacement) {
    // A provider switch without replace semantics must not concatenate drafts.
    return state;
  }

  const tokenDrafts = { ...state.tokenDrafts };
  let replacementPendingByStep = state.replacementPendingByStep;
  if (state.replacementPendingByStep[stepKey]) {
    replacementPendingByStep = { ...state.replacementPendingByStep };
    delete replacementPendingByStep[stepKey];
  }
  if (activeDraftKey && (activeDraftKey !== draftKey || requiresReplacement)) {
    const previous = tokenDrafts[activeDraftKey];
    if (previous) {
      tokenDrafts[activeDraftKey] = {
        ...previous,
        active: false,
        replacedAtSequence: event.sequence,
      };
    }
  }

  const existing = tokenDrafts[draftKey];
  tokenDrafts[draftKey] = {
    key: draftKey,
    stepKey,
    providerCallId: payload.provider_call_id,
    streamAttempt: payload.stream_attempt,
    content: `${existing?.content ?? ''}${payload.content}`,
    active: true,
  };

  return {
    ...state,
    tokenDrafts,
    activeStreamByStep: { ...state.activeStreamByStep, [stepKey]: draftKey },
    replacementPendingByStep,
  };
}

function applyArtifact(
  state: WorkflowRunViewState,
  event: WorkflowEventEnvelope<'artifact'>,
): WorkflowRunViewState {
  if (event.payload.storage_status && event.payload.storage_status !== 'active') {
    return state;
  }
  return {
    ...state,
    artifacts: { ...state.artifacts, [event.payload.resource_id]: event.payload },
  };
}

function applyTrace(
  state: WorkflowRunViewState,
  event: WorkflowEventEnvelope<'trace'>,
): WorkflowRunViewState {
  const payload = event.payload;
  const traceId = payload.agent_run_id ?? payload.id ?? payload.run_id ?? `trace-${event.sequence}`;
  let next: WorkflowRunViewState = {
    ...state,
    traces: { ...state.traces, [traceId]: payload },
  };

  const nodeId = payload.node_id ?? payload.agent_name;
  const nodeStatus = asWorkflowNodeStatus(payload.status);
  if (nodeId && nodeStatus) {
    next = {
      ...next,
      nodes: {
        ...next.nodes,
        [nodeId]: {
          ...next.nodes[nodeId],
          nodeId,
          status: nodeStatus,
          agentId: payload.agent_id ?? next.nodes[nodeId]?.agentId,
          agentName: payload.agent_name ?? next.nodes[nodeId]?.agentName,
          skillId: payload.skill_id ?? next.nodes[nodeId]?.skillId,
          skillName: payload.skill_name ?? next.nodes[nodeId]?.skillName,
          stepAttemptId: payload.step_attempt_id ?? next.nodes[nodeId]?.stepAttemptId,
          agentRunId: payload.agent_run_id ?? payload.id ?? next.nodes[nodeId]?.agentRunId,
          durationMs: payload.duration_ms ?? next.nodes[nodeId]?.durationMs,
          qualityScore: payload.quality_score ?? next.nodes[nodeId]?.qualityScore,
        },
      },
    };
  }

  const requiresReplacement = payload.replace_draft || payload.provider_switch?.replace_draft;
  const stepKey = payload.step_attempt_id ?? payload.node_id;
  if (requiresReplacement && stepKey) {
    return markDraftReplacement(next, stepKey, event.sequence);
  }
  return next;
}

function markDraftReplacement(
  state: WorkflowRunViewState,
  stepKey: string,
  sequence: number,
): WorkflowRunViewState {
  const tokenDrafts = { ...state.tokenDrafts };
  const activeDraftKey = state.activeStreamByStep[stepKey];
  if (activeDraftKey && tokenDrafts[activeDraftKey]) {
    tokenDrafts[activeDraftKey] = {
      ...tokenDrafts[activeDraftKey],
      active: false,
      content: '',
      replacedAtSequence: sequence,
    };
  }
  const activeStreamByStep = { ...state.activeStreamByStep };
  delete activeStreamByStep[stepKey];
  return {
    ...state,
    tokenDrafts,
    activeStreamByStep,
    replacementPendingByStep: { ...state.replacementPendingByStep, [stepKey]: true },
  };
}

function makeDraftKey(stepKey: string, providerCallId?: string, streamAttempt?: number): string {
  return `${stepKey}:${providerCallId ?? 'legacy'}:${streamAttempt ?? 0}`;
}

function asWorkflowRunStatus(value: unknown): WorkflowRunStatus | undefined {
  switch (value) {
    case 'queued':
    case 'running':
    case 'reworking':
    case 'pausing':
    case 'paused':
    case 'waiting_approval':
    case 'cancelling':
    case 'cancelled':
    case 'succeeded':
    case 'failed':
    case 'blocked':
      return value;
    case 'done':
    case 'success':
      return 'succeeded';
    case 'error':
      return 'failed';
    default:
      return undefined;
  }
}

function asWorkflowNodeStatus(value: unknown): WorkflowNodeStatus | undefined {
  switch (value) {
    case 'pending':
    case 'ready':
    case 'running':
    case 'succeeded':
    case 'failed':
    case 'blocked':
    case 'cancelled':
    case 'skipped':
      return value;
    case 'queued':
      return 'pending';
    case 'success':
    case 'done':
      return 'succeeded';
    case 'error':
      return 'failed';
    default:
      return undefined;
  }
}
