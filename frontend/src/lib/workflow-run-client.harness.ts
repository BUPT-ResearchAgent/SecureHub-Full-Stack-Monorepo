import { normalizeWorkflowEvent, parseSSEFrame, WorkflowRunClient } from './workflow-run-client';
import type { EvidenceChunkDTO } from './api-types';
import {
  createWorkflowRunViewState,
  reduceWorkflowEvent,
  type WorkflowEvent,
} from './workflow-run.types';

const RUN_ID = '00000000-0000-0000-0000-000000000001';
const STEP_ID = '00000000-0000-0000-0000-000000000002';

export async function runWorkflowRunClientHarness(): Promise<void> {
  const evidence = {
    chunk_id: '00000000-0000-0000-0000-000000000003',
    document_id: '00000000-0000-0000-0000-000000000004',
    chunk_text: 'Evidence from the durable runtime.',
    score: 0.91,
    platform: 'owasp',
    rights_note: 'CC BY-SA 4.0',
    source_url: 'https://owasp.org/',
  } satisfies EvidenceChunkDTO;

  let state = createWorkflowRunViewState(RUN_ID);
  state = reduceWorkflowEvent(state, event('progress', 1, {
    node_id: 'doc_archivist',
    step_attempt_id: STEP_ID,
    status: 'running',
  }));
  state = reduceWorkflowEvent(state, event('evidence', 2, {
    items: [evidence],
    step_attempt_id: STEP_ID,
    evidence_snapshot_ids: ['00000000-0000-0000-0000-000000000007'],
  }));
  state = reduceWorkflowEvent(state, event('token', 3, {
    content: 'old provider draft',
    step_attempt_id: STEP_ID,
    provider_call_id: 'provider-call-a',
    stream_attempt: 1,
  }));
  state = reduceWorkflowEvent(state, event('artifact', 4, {
    resource_id: '00000000-0000-0000-0000-000000000005',
    resource_type: 'doc',
    title: 'Generated document',
    storage_status: 'active',
  }));
  state = reduceWorkflowEvent(state, event('trace', 5, {
    agent_run_id: '00000000-0000-0000-0000-000000000006',
    agent_name: 'doc_archivist',
    skill_name: 'GenerateCourseDoc',
    status: 'succeeded',
    step_attempt_id: STEP_ID,
  }));

  assert(state.nodes.doc_archivist?.status === 'succeeded', 'progress/trace reducer did not update node state');
  assert(state.evidence[evidence.chunk_id]?.chunk_text === evidence.chunk_text, 'evidence reducer changed real evidence');
  assert(state.evidenceLineage[evidence.chunk_id]?.stepAttemptId === STEP_ID, 'evidence lineage lost its step attempt');
  assert(state.evidenceLineage[evidence.chunk_id]?.evidenceSnapshotIds.length === 1, 'evidence lineage lost snapshot IDs');
  assert(Object.keys(state.artifacts).length === 1, 'active artifact was not retained');

  state = reduceWorkflowEvent(state, event('trace', 6, {
    step_attempt_id: STEP_ID,
    replace_draft: true,
    provider_switch: { replace_draft: true, from_provider: 'deepseek', to_provider: 'spark' },
  }));
  state = reduceWorkflowEvent(state, event('token', 7, {
    content: 'replacement provider draft',
    step_attempt_id: STEP_ID,
    provider_call_id: 'provider-call-b',
    stream_attempt: 1,
  }));
  state = reduceWorkflowEvent(state, event('token', 8, {
    content: 'must be discarded',
    step_attempt_id: STEP_ID,
    provider_call_id: 'provider-call-a',
    stream_attempt: 1,
  }));

  const activeDraft = Object.values(state.tokenDrafts).find((draft) => draft.active);
  assert(activeDraft?.content === 'replacement provider draft', 'provider stream drafts were concatenated');

  const beforeDuplicate = state;
  state = reduceWorkflowEvent(state, event('token', 8, {
    content: 'duplicate',
    step_attempt_id: STEP_ID,
    provider_call_id: 'provider-call-b',
    stream_attempt: 1,
  }));
  assert(state === beforeDuplicate, 'duplicate sequence was applied');

  state = reduceWorkflowEvent(state, event('done', 9, { status: 'succeeded', quality_score: 0.9 }));
  state = reduceWorkflowEvent(state, event('error', 10, {
    code: 'SHOULD_NOT_REPLACE_DONE',
    message: 'terminal error after done',
  }));
  assert(state.status === 'succeeded' && state.terminalEvent === 'done', 'done/error terminal exclusivity failed');

  let approvalState = createWorkflowRunViewState(RUN_ID);
  approvalState = reduceWorkflowEvent(approvalState, event('progress', 1, {
    root_status: 'waiting_approval',
    approval_id: '00000000-0000-0000-0000-000000000008',
    approval_kind: 'provider_retry',
  }));
  assert(approvalState.approvalKind === 'provider_retry', 'approval kind was not retained for the control matrix');
  approvalState = reduceWorkflowEvent(approvalState, event('progress', 2, { root_status: 'queued' }));
  assert(!approvalState.approvalId && !approvalState.approvalKind, 'stale approval control survived after resume');

  let providerTraceState = createWorkflowRunViewState(RUN_ID);
  providerTraceState = reduceWorkflowEvent(providerTraceState, event('trace', 1, {
    agent_run_id: '00000000-0000-0000-0000-000000000009',
    provider_switch: { from_provider: 'xfyun', to_provider: 'deepseek', replace_draft: true },
  }));
  providerTraceState = reduceWorkflowEvent(providerTraceState, event('trace', 2, {
    agent_run_id: '00000000-0000-0000-0000-000000000009',
    status: 'succeeded',
  }));
  assert(
    Object.values(providerTraceState.traces).some((trace) => trace.provider_switch?.to_provider === 'deepseek'),
    'terminal trace erased the provider replacement audit',
  );

  const legacyFrame = parseSSEFrame('id: 11\nevent: token\ndata: {"content":"legacy fragment"}');
  assert(legacyFrame != null, 'SSE frame parser rejected a valid frame');
  const legacyEvent = normalizeWorkflowEvent(legacyFrame.data, {
    eventTypeHint: legacyFrame.event,
    sseId: legacyFrame.id,
    expectedRunId: RUN_ID,
  });
  assert(legacyEvent?.event_type === 'token' && legacyEvent.sequence === 11, 'legacy event compatibility failed');

  await verifyGapRecovery();
  await verifyReconnectAndRefreshCursor();
  await verifyRootScopedReplayStartsAtZero();
  await verifyControlAndApprovalRequests();
}

async function verifyGapRecovery(): Promise<void> {
  const seenSequences: number[] = [];
  let replayRequested = false;
  let replayHeader: string | null = null;
  const client = new WorkflowRunClient({
    apiBaseUrl: 'https://securehub.test',
    storage: null,
    getAuthToken: () => null,
    fetchImpl: async (input, init) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      if (url.includes('after_sequence=1')) {
        replayRequested = true;
        replayHeader = headers.get('Last-Event-ID');
        return sseResponse([
          envelopeFrame('token', 2, {
            content: 'replayed token',
            step_attempt_id: STEP_ID,
            provider_call_id: 'provider-call-a',
            stream_attempt: 1,
          }),
        ]);
      }
      return sseResponse([
        envelopeFrame('progress', 1, { node_id: 'doc_archivist', status: 'running' }),
        envelopeFrame('done', 3, { status: 'succeeded' }),
      ]);
    },
  });

  const terminalState = await new Promise<ReturnType<typeof createWorkflowRunViewState>>((resolve, reject) => {
    let subscription: ReturnType<typeof client.subscribe> | undefined;
    subscription = client.subscribe(RUN_ID, {
      onEvent: (event) => seenSequences.push(event.sequence),
      onState: (state) => {
        if (state.status !== 'succeeded') return;
        subscription?.unsubscribe();
        resolve(state);
      },
      onError: reject,
    });
  });

  assert(replayRequested, 'live sequence gap did not request PostgreSQL replay');
  assert(replayHeader === '1', 'gap replay did not send Last-Event-ID');
  assert(seenSequences.join(',') === '1,2,3', 'gap replay did not preserve sequence order');
  assert(terminalState.lastSequence === 3, 'gap replay did not advance the Last-Event-ID cursor');
}

async function verifyReconnectAndRefreshCursor(): Promise<void> {
  const storage = new MemoryStorage();
  const reconnectRequests: Array<{ url: string; lastEventId: string | null }> = [];
  const reconnectingClient = new WorkflowRunClient({
    apiBaseUrl: 'https://securehub.test',
    storage,
    getAuthToken: () => null,
    reconnectDelayMs: 0,
    fetchImpl: async (input, init) => {
      const request = {
        url: String(input),
        lastEventId: new Headers(init?.headers).get('Last-Event-ID'),
      };
      reconnectRequests.push(request);
      return sseResponse(
        reconnectRequests.length === 1
          ? [envelopeFrame('progress', 1, { node_id: 'producer', status: 'running' })]
          : [envelopeFrame('done', 2, { status: 'succeeded' })],
      );
    },
  });

  const reconnected = await terminalState(reconnectingClient, RUN_ID);
  assert(reconnected.lastSequence === 2, 'reconnect did not converge the terminal stream');
  assert(reconnectRequests.length === 2, 'closed non-terminal stream did not reconnect');
  assert(reconnectRequests[1]?.url.includes('after_sequence=1'), 'reconnect did not resume from the durable cursor');
  assert(reconnectRequests[1]?.lastEventId === '1', 'reconnect did not send Last-Event-ID');

  let refreshRequest: { url: string; lastEventId: string | null } | undefined;
  const refreshedClient = new WorkflowRunClient({
    apiBaseUrl: 'https://securehub.test',
    storage,
    getAuthToken: () => null,
    fetchImpl: async (input, init) => {
      refreshRequest = {
        url: String(input),
        lastEventId: new Headers(init?.headers).get('Last-Event-ID'),
      };
      return sseResponse([envelopeFrame('done', 3, { status: 'succeeded' })]);
    },
  });

  const refreshed = await terminalState(refreshedClient, RUN_ID);
  assert(refreshed.lastSequence === 3, 'refreshed client did not process the resumed terminal event');
  assert(refreshRequest?.url.includes('after_sequence=2'), 'refresh did not restore the persisted cursor');
  assert(refreshRequest?.lastEventId === '2', 'refresh did not replay with the persisted Last-Event-ID');
}

async function verifyRootScopedReplayStartsAtZero(): Promise<void> {
  const storage = new MemoryStorage();
  storage.setItem(`securehub-workflow-run:${RUN_ID}:last-event-id`, '9');
  let requestUrl = '';
  const client = new WorkflowRunClient({
    apiBaseUrl: 'https://securehub.test',
    storage,
    getAuthToken: () => null,
    fetchImpl: async (input) => {
      requestUrl = String(input);
      return sseResponse([
        envelopeFrame('progress', 1, { node_id: 'quality_check', status: 'running' }),
        envelopeFrame('done', 2, { status: 'succeeded' }),
      ]);
    },
  });

  const replayed = await new Promise<ReturnType<typeof createWorkflowRunViewState>>((resolve, reject) => {
    let subscription: ReturnType<typeof client.subscribe> | undefined;
    subscription = client.subscribe(RUN_ID, {
      replayFromStart: true,
      onState: (state) => {
        if (state.status !== 'succeeded') return;
        subscription?.unsubscribe();
        resolve(state);
      },
      onError: reject,
    });
  });

  assert(replayed.lastSequence === 2, 'root-scoped replay did not rebuild from event sequence 0');
  assert(!requestUrl.includes('after_sequence='), 'root-scoped replay inherited an unrelated UI cursor');
  assert(storage.getItem(`securehub-workflow-run:${RUN_ID}:last-event-id`) === '9', 'audit replay overwrote the interactive stream cursor');
}

async function verifyControlAndApprovalRequests(): Promise<void> {
  const requests: Array<{ url: string; method?: string; body?: string }> = [];
  const approvalId = '00000000-0000-0000-0000-000000000099';
  const client = new WorkflowRunClient({
    apiBaseUrl: 'https://securehub.test',
    storage: null,
    getAuthToken: () => null,
    fetchImpl: async (input, init) => {
      const url = String(input);
      requests.push({ url, method: init?.method, body: typeof init?.body === 'string' ? init.body : undefined });
      if (url.includes('/approvals/')) {
        return jsonResponse({
          approval_id: approvalId,
          run_id: RUN_ID,
          kind: 'workflow_action',
          status: 'approved',
          request: {},
          decision: { reviewed: true },
        });
      }
      return jsonResponse({ run_id: RUN_ID, status: 'queued', compatibility: 'compatible' });
    },
  });

  const paused = await client.pause(RUN_ID);
  const approval = await client.decideApproval(RUN_ID, approvalId, true, { reviewed: true });

  assert(paused.compatibility === 'compatible', 'control response did not preserve compatibility status');
  assert(approval.status === 'approved', 'approval response did not preserve decision status');
  assert(requests[0]?.url.endsWith(`/workflow-runs/${RUN_ID}/pause`), 'pause endpoint path is incorrect');
  assert(requests[1]?.url.endsWith(`/workflow-runs/${RUN_ID}/approvals/${approvalId}`), 'approval endpoint path is incorrect');
  assert(JSON.parse(requests[1]?.body ?? '{}').approved === true, 'approval request did not send the decision');
}

function terminalState(client: WorkflowRunClient, runId: string) {
  return new Promise<ReturnType<typeof createWorkflowRunViewState>>((resolve, reject) => {
    let subscription: ReturnType<typeof client.subscribe> | undefined;
    subscription = client.subscribe(runId, {
      onState: (state) => {
        if (state.status !== 'succeeded') return;
        subscription?.unsubscribe();
        resolve(state);
      },
      onError: reject,
    });
  });
}

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

function envelopeFrame(eventType: WorkflowEvent['event_type'], sequence: number, payload: unknown): string {
  return `id: ${sequence}\nevent: ${eventType}\ndata: ${JSON.stringify({
    workflow_run_id: RUN_ID,
    sequence,
    event_type: eventType,
    payload,
  })}\n\n`;
}

function sseResponse(frames: string[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(frames.join('')));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
}

function event<T extends WorkflowEvent['event_type']>(
  eventType: T,
  sequence: number,
  payload: Extract<WorkflowEvent, { event_type: T }>['payload'],
): Extract<WorkflowEvent, { event_type: T }> {
  return {
    workflow_run_id: RUN_ID,
    sequence,
    event_type: eventType,
    payload,
  } as Extract<WorkflowEvent, { event_type: T }>;
}

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`WorkflowRunClient harness: ${message}`);
}
