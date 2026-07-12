import { API_BASE_URL, ApiError, getStoredAuthToken } from './api';
import {
  createWorkflowRunViewState,
  isTerminalWorkflowStatus,
  isWorkflowEventType,
  reduceWorkflowEvent,
  type WorkflowArtifactPayload,
  type WorkflowApprovalResponse,
  type WorkflowDonePayload,
  type WorkflowErrorPayload,
  type WorkflowEvent,
  type WorkflowEventCorrelation,
  type WorkflowEventEnvelope,
  type WorkflowEventPayloadByType,
  type WorkflowEventType,
  type WorkflowRunMode,
  type WorkflowRunControlResponse,
  type WorkflowRunStartRequest,
  type WorkflowRunStartResponse,
  type WorkflowRunStatus,
  type WorkflowRunStatusResponse,
  type WorkflowRunViewState,
} from './workflow-run.types';

const DEFAULT_RECONNECT_DELAY_MS = 750;
const DEFAULT_GAP_TIMEOUT_MS = 10_000;
const MAX_DEDUPE_SEQUENCES = 4_096;

type FetchLike = typeof fetch;
type JsonRecord = Record<string, unknown>;

export class WorkflowRunClientError extends Error {
  readonly status?: number;
  readonly code?: string;

  constructor(message: string, options: { status?: number; code?: string } = {}) {
    super(message);
    this.name = 'WorkflowRunClientError';
    this.status = options.status;
    this.code = options.code;
  }
}

export type WorkflowRunClientOptions = {
  apiBaseUrl?: string;
  fetchImpl?: FetchLike;
  getAuthToken?: () => string | null;
  storage?: Storage | null;
  reconnectDelayMs?: number;
  gapTimeoutMs?: number;
};

export type WorkflowSubscriptionOptions = {
  eventsUrl?: string;
  initialState?: WorkflowRunViewState;
  onEvent?: (event: WorkflowEvent) => void;
  onState?: (state: WorkflowRunViewState) => void;
  onConnection?: (state: 'connecting' | 'live' | 'reconnecting' | 'closed') => void;
  onError?: (error: WorkflowRunClientError) => void;
};

export type WorkflowSubscription = {
  getState: () => WorkflowRunViewState;
  unsubscribe: () => void;
};

export type WorkflowRunStartOptions = {
  idempotencyKey?: string;
};

export type ParsedSSEFrame = {
  id?: string;
  event?: string;
  data: unknown;
};

export function createWorkflowRunStateFromStart(
  start: WorkflowRunStartResponse,
): WorkflowRunViewState {
  return {
    ...createWorkflowRunViewState(start.run_id),
    status: start.status,
    mode: start.mode,
    requestedProvider: start.requested_provider,
    requestedModel: start.requested_model,
    actualProvider: start.actual_provider ?? start.provider,
    actualModel: start.actual_model ?? start.model,
  };
}

export class WorkflowRunClient {
  private readonly apiBaseUrl: string;
  private readonly fetchImpl: FetchLike;
  private readonly getAuthToken: () => string | null;
  private readonly storage: Storage | null;
  private readonly reconnectDelayMs: number;
  private readonly gapTimeoutMs: number;

  constructor(options: WorkflowRunClientOptions = {}) {
    this.apiBaseUrl = options.apiBaseUrl ?? API_BASE_URL;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.getAuthToken = options.getAuthToken ?? getStoredAuthToken;
    this.storage = options.storage ?? safeStorage();
    this.reconnectDelayMs = options.reconnectDelayMs ?? DEFAULT_RECONNECT_DELAY_MS;
    this.gapTimeoutMs = options.gapTimeoutMs ?? DEFAULT_GAP_TIMEOUT_MS;
  }

  async start(
    payload: WorkflowRunStartRequest,
    options: WorkflowRunStartOptions = {},
  ): Promise<WorkflowRunStartResponse> {
    const idempotencyKey = options.idempotencyKey ?? createIdempotencyKey();
    return this.requestJson<WorkflowRunStartResponse>('/api/v1/workflow-runs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify({ stream: true, mode: 'real', ...payload }),
    });
  }

  async status(runId: string): Promise<WorkflowRunStatusResponse> {
    return this.requestJson<WorkflowRunStatusResponse>(`/api/v1/workflow-runs/${encodeURIComponent(runId)}`, {
      method: 'GET',
    });
  }

  async cancel(runId: string): Promise<WorkflowRunControlResponse> {
    return this.control(runId, 'cancel');
  }

  async pause(runId: string): Promise<WorkflowRunControlResponse> {
    return this.control(runId, 'pause');
  }

  async resume(runId: string): Promise<WorkflowRunControlResponse> {
    return this.control(runId, 'resume');
  }

  async retry(runId: string, payload: Record<string, unknown> = {}): Promise<WorkflowRunControlResponse> {
    return this.control(runId, 'retry', payload);
  }

  /** Start one lineage-linked retry for an owned generated artifact. */
  async retryResource(
    resourceId: string,
    payload: Record<string, unknown> = {},
    options: WorkflowRunStartOptions = {},
  ): Promise<WorkflowRunStartResponse> {
    const idempotencyKey = options.idempotencyKey ?? createIdempotencyKey();
    return this.requestJson<WorkflowRunStartResponse>(
      `/api/v1/resources/${encodeURIComponent(resourceId)}/retry`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(payload),
      },
    );
  }

  async decideApproval(
    runId: string,
    approvalId: string,
    approved: boolean,
    decision: Record<string, unknown> = {},
  ): Promise<WorkflowApprovalResponse> {
    return this.requestJson<WorkflowApprovalResponse>(
      `/api/v1/workflow-runs/${encodeURIComponent(runId)}/approvals/${encodeURIComponent(approvalId)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, decision }),
      },
    );
  }

  subscribe(runId: string, options: WorkflowSubscriptionOptions = {}): WorkflowSubscription {
    let active = true;
    let controller: AbortController | undefined;
    let state = options.initialState ?? createWorkflowRunViewState(runId);
    const restoredCursor = this.restoreCursor(runId);
    if (restoredCursor > state.lastSequence) {
      state = { ...state, lastSequence: restoredCursor };
    }
    const receivedSequences = new Set<number>();
    let pipeline = Promise.resolve();

    const publishState = () => {
      this.persistCursor(runId, state.lastSequence);
      options.onState?.(state);
    };

    const processEvent = async (event: WorkflowEvent, allowGapRecovery: boolean): Promise<void> => {
      if (!active || event.workflow_run_id !== runId) return;
      if (receivedSequences.has(event.sequence) || event.sequence <= state.lastSequence) return;

      const expectedSequence = state.lastSequence + 1;
      if (event.sequence > expectedSequence) {
        if (!allowGapRecovery) {
          throw new WorkflowRunClientError('SSE event sequence gap could not be replayed', {
            code: 'SSE_SEQUENCE_GAP',
          });
        }
        await this.recoverGap({
          runId,
          eventsUrl: options.eventsUrl,
          fromSequence: expectedSequence,
          throughSequence: event.sequence - 1,
          onEvent: (missing) => processEvent(missing, false),
        });
      }

      if (receivedSequences.has(event.sequence) || event.sequence <= state.lastSequence) return;
      const visibleToPresenter = shouldForwardWorkflowEvent(state, event);
      state = reduceWorkflowEvent(state, event);
      receivedSequences.add(event.sequence);
      trimSequences(receivedSequences);
      publishState();
      if (visibleToPresenter) options.onEvent?.(event);
    };

    const enqueue = (event: WorkflowEvent) => {
      pipeline = pipeline
        .then(() => processEvent(event, true))
        .catch((error: unknown) => {
          if (!active) return;
          options.onError?.(asWorkflowRunClientError(error));
        });
      return pipeline;
    };

    const run = async () => {
      let reconnecting = false;
      while (active && !isTerminalWorkflowStatus(state.status)) {
        options.onConnection?.(reconnecting ? 'reconnecting' : 'connecting');
        controller = new AbortController();
        try {
          await this.consumeEventStream({
            runId,
            eventsUrl: options.eventsUrl,
            afterSequence: state.lastSequence,
            signal: controller.signal,
            onEvent: enqueue,
          });
          await pipeline;
          if (!active || isTerminalWorkflowStatus(state.status)) break;
          reconnecting = true;
          options.onConnection?.('reconnecting');
          await delay(this.reconnectDelayMs, controller.signal);
        } catch (error) {
          if (!active || isAbortError(error)) break;
          options.onError?.(asWorkflowRunClientError(error));
          reconnecting = true;
          options.onConnection?.('reconnecting');
          await delay(this.reconnectDelayMs, controller.signal);
        }
      }
      options.onConnection?.('closed');
    };

    void run();
    return {
      getState: () => state,
      unsubscribe: () => {
        if (!active) return;
        active = false;
        controller?.abort();
        options.onConnection?.('closed');
      },
    };
  }

  async waitForTerminal(
    start: WorkflowRunStartResponse,
    options: Omit<WorkflowSubscriptionOptions, 'initialState'> = {},
  ): Promise<WorkflowRunViewState> {
    const initialState = createWorkflowRunStateFromStart(start);
    if (isTerminalWorkflowStatus(initialState.status)) return initialState;

    return new Promise<WorkflowRunViewState>((resolve, reject) => {
      let subscription: WorkflowSubscription | undefined;
      subscription = this.subscribe(start.run_id, {
        ...options,
        eventsUrl: options.eventsUrl ?? start.events_url,
        initialState,
        onState: (state) => {
          options.onState?.(state);
          if (isTerminalWorkflowStatus(state.status)) {
            subscription?.unsubscribe();
            resolve(state);
          }
        },
        onError: (error) => {
          options.onError?.(error);
          if (error.code === 'SSE_SEQUENCE_GAP') {
            subscription?.unsubscribe();
            reject(error);
          }
        },
      });
    });
  }

  private async control(
    runId: string,
    action: 'cancel' | 'pause' | 'resume' | 'retry',
    payload: Record<string, unknown> = {},
  ): Promise<WorkflowRunControlResponse> {
    return this.requestJson<WorkflowRunControlResponse>(
      `/api/v1/workflow-runs/${encodeURIComponent(runId)}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    );
  }

  private async requestJson<T>(path: string, init: RequestInit): Promise<T> {
    const response = await this.fetchImpl(this.withApiBase(path), {
      ...init,
      headers: this.requestHeaders(init.headers),
    });
    if (!response.ok) throw await readWorkflowApiError(response);
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  private async consumeEventStream({
    runId,
    eventsUrl,
    afterSequence,
    signal,
    onEvent,
    untilSequence,
  }: {
    runId: string;
    eventsUrl?: string;
    afterSequence: number;
    signal: AbortSignal;
    onEvent: (event: WorkflowEvent) => Promise<void>;
    untilSequence?: number;
  }): Promise<void> {
    const response = await this.fetchImpl(
      this.makeEventsUrl(eventsUrl ?? `/api/v1/workflow-runs/${encodeURIComponent(runId)}/events`, afterSequence, untilSequence),
      {
        method: 'GET',
        headers: this.requestHeaders({
          Accept: 'text/event-stream',
          ...(afterSequence > 0 ? { 'Last-Event-ID': String(afterSequence) } : {}),
        }),
        signal,
      },
    );
    if (!response.ok) throw await readWorkflowApiError(response);
    if (!response.body) {
      throw new WorkflowRunClientError('Workflow event stream did not include a response body', {
        code: 'EMPTY_EVENT_STREAM',
      });
    }

    let fallbackSequence = afterSequence;
    await readSSEStream(response.body, async (frame) => {
      const event = normalizeWorkflowEvent(frame.data, {
        eventTypeHint: frame.event,
        sseId: frame.id,
        expectedRunId: runId,
        fallbackSequence: ++fallbackSequence,
      });
      if (!event) return;
      fallbackSequence = Math.max(fallbackSequence, event.sequence);
      await onEvent(event);
      if (untilSequence != null && event.sequence >= untilSequence) {
        signal.throwIfAborted?.();
      }
    });
  }

  private async recoverGap({
    runId,
    eventsUrl,
    fromSequence,
    throughSequence,
    onEvent,
  }: {
    runId: string;
    eventsUrl?: string;
    fromSequence: number;
    throughSequence: number;
    onEvent: (event: WorkflowEvent) => Promise<void>;
  }): Promise<void> {
    if (throughSequence < fromSequence) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.gapTimeoutMs);
    let recoveredThrough = fromSequence - 1;
    try {
      await this.consumeEventStream({
        runId,
        eventsUrl,
        afterSequence: fromSequence - 1,
        untilSequence: throughSequence,
        signal: controller.signal,
        onEvent: async (event) => {
          if (event.sequence < fromSequence || event.sequence > throughSequence) return;
          if (event.sequence !== recoveredThrough + 1) {
            throw new WorkflowRunClientError('SSE replay returned a non-contiguous sequence', {
              code: 'SSE_SEQUENCE_GAP',
            });
          }
          recoveredThrough = event.sequence;
          await onEvent(event);
          if (recoveredThrough >= throughSequence) controller.abort();
        },
      });
    } catch (error) {
      if (!(isAbortError(error) && recoveredThrough >= throughSequence)) throw error;
    } finally {
      clearTimeout(timeout);
    }
    if (recoveredThrough !== throughSequence) {
      throw new WorkflowRunClientError('SSE replay did not fill the complete sequence gap', {
        code: 'SSE_SEQUENCE_GAP',
      });
    }
  }

  private makeEventsUrl(eventsUrl: string, afterSequence: number, untilSequence?: number): string {
    const url = new URL(this.withApiBase(eventsUrl));
    if (afterSequence > 0) {
      // Both names are sent during rollout. New gateways use after_sequence;
      // Agent-Run v0.4 reads after_event_id.
      url.searchParams.set('after_sequence', String(afterSequence));
      url.searchParams.set('after_event_id', String(afterSequence));
    }
    if (untilSequence != null) url.searchParams.set('until_sequence', String(untilSequence));
    return url.toString();
  }

  private requestHeaders(headers?: HeadersInit): Headers {
    const next = new Headers(headers);
    next.set('Accept', next.get('Accept') ?? 'application/json');
    const token = this.getAuthToken();
    if (token && !next.has('Authorization')) next.set('Authorization', `Bearer ${token}`);
    return next;
  }

  private withApiBase(path: string): string {
    if (/^https?:\/\//i.test(path)) return path;
    const base = this.apiBaseUrl.replace(/\/$/, '');
    return `${base}${path.startsWith('/') ? path : `/${path}`}`;
  }

  private restoreCursor(runId: string): number {
    try {
      const value = this.storage?.getItem(cursorStorageKey(runId));
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
    } catch {
      return 0;
    }
  }

  private persistCursor(runId: string, sequence: number): void {
    try {
      this.storage?.setItem(cursorStorageKey(runId), String(sequence));
    } catch {
      // Cursor persistence is an optimization; the server remains authoritative.
    }
  }
}

export function normalizeWorkflowEvent(
  rawData: unknown,
  {
    eventTypeHint,
    sseId,
    expectedRunId,
    fallbackSequence,
  }: {
    eventTypeHint?: string;
    sseId?: string;
    expectedRunId?: string;
    fallbackSequence?: number;
  } = {},
): WorkflowEvent | null {
  const record = isRecord(rawData) ? rawData : {};
  const eventTypeCandidate = stringValue(record.event_type) ?? stringValue(record.event) ?? eventTypeHint;
  if (!eventTypeCandidate || !isWorkflowEventType(eventTypeCandidate)) return null;

  const runId = stringValue(record.workflow_run_id) ?? expectedRunId ?? stringValue(record.run_id);
  if (!runId) return null;
  const sequence = numberValue(record.sequence) ?? numberValue(record.event_id) ?? numberValue(sseId) ?? fallbackSequence;
  if (!sequence || sequence < 1) return null;

  const payload = normalizePayload(eventTypeCandidate, rawData, record);
  if (!payload) return null;
  const envelope = {
    workflow_run_id: runId,
    sequence,
    event_type: eventTypeCandidate,
    payload,
    created_at: stringValue(record.created_at),
    mode: modeValue(record.mode),
    requested_provider: nullableString(record.requested_provider),
    requested_model: nullableString(record.requested_model),
    provider: nullableString(record.provider),
    model: nullableString(record.model),
    actual_provider: nullableString(record.actual_provider),
    actual_model: nullableString(record.actual_model),
    step_attempt_id: stringValue(record.step_attempt_id),
    agent_run_id: stringValue(record.agent_run_id),
    provider_call_id: stringValue(record.provider_call_id),
    stream_attempt: numberValue(record.stream_attempt),
  } as WorkflowEventEnvelope;

  return envelope as WorkflowEvent;
}

function normalizePayload<T extends WorkflowEventType>(
  eventType: T,
  rawData: unknown,
  record: JsonRecord,
): WorkflowEventPayloadByType[T] | null {
  const rawPayload = record.payload;
  const payloadRecord = isRecord(rawPayload) ? rawPayload : isRecord(rawData) ? rawData : {};
  const correlation = mergeCorrelation(record, payloadRecord);

  if (eventType === 'evidence') {
    const source = Array.isArray(rawPayload) ? rawPayload : Array.isArray(rawData) ? rawData : payloadRecord.items;
    if (!Array.isArray(source)) return null;
    return { ...correlation, items: source } as WorkflowEventPayloadByType[T];
  }
  if (eventType === 'token') {
    const content = stringValue(payloadRecord.content);
    if (content == null) return null;
    return { ...payloadRecord, ...correlation, content } as WorkflowEventPayloadByType[T];
  }
  if (eventType === 'artifact') {
    const resourceId = stringValue(payloadRecord.resource_id);
    const resourceType = stringValue(payloadRecord.resource_type);
    const title = stringValue(payloadRecord.title);
    if (!resourceId || !resourceType || !title) return null;
    return {
      ...payloadRecord,
      ...correlation,
      resource_id: resourceId,
      resource_type: resourceType,
      title,
    } as WorkflowEventPayloadByType[T];
  }
  if (eventType === 'error') {
    const message = stringValue(payloadRecord.message);
    if (!message) return null;
    return {
      ...payloadRecord,
      ...correlation,
      code: stringValue(payloadRecord.code) ?? 'UNKNOWN_WORKFLOW_ERROR',
      message,
    } as WorkflowEventPayloadByType[T];
  }
  if (eventType === 'done') {
    const status = stringValue(payloadRecord.status) ?? 'succeeded';
    if (status !== 'succeeded' && status !== 'cancelled') return null;
    return { ...payloadRecord, ...correlation, status } as WorkflowEventPayloadByType[T];
  }
  return { ...payloadRecord, ...correlation } as WorkflowEventPayloadByType[T];
}

function mergeCorrelation(source: JsonRecord, payload: JsonRecord): WorkflowEventCorrelation {
  return {
    step_attempt_id: stringValue(payload.step_attempt_id) ?? stringValue(source.step_attempt_id),
    agent_run_id: stringValue(payload.agent_run_id) ?? stringValue(source.agent_run_id),
    provider_call_id: stringValue(payload.provider_call_id) ?? stringValue(source.provider_call_id),
    stream_attempt: numberValue(payload.stream_attempt) ?? numberValue(source.stream_attempt),
    node_id: stringValue(payload.node_id) ?? stringValue(source.node_id),
    agent_id: stringValue(payload.agent_id) ?? stringValue(source.agent_id),
    agent_name: stringValue(payload.agent_name) ?? stringValue(source.agent_name),
    skill_id: stringValue(payload.skill_id) ?? stringValue(source.skill_id),
    skill_name: stringValue(payload.skill_name) ?? stringValue(source.skill_name),
  };
}

export async function readSSEStream(
  stream: ReadableStream<Uint8Array>,
  onFrame: (frame: ParsedSSEFrame) => Promise<void>,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? '';
      for (const block of blocks) {
        const frame = parseSSEFrame(block);
        if (frame) await onFrame(frame);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) {
      const frame = parseSSEFrame(buffer);
      if (frame) await onFrame(frame);
    }
  } finally {
    reader.releaseLock();
  }
}

export function parseSSEFrame(block: string): ParsedSSEFrame | null {
  const dataLines: string[] = [];
  let id: string | undefined;
  let event: string | undefined;
  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '');
    if (field === 'id') id = value;
    if (field === 'event') event = value;
    if (field === 'data') dataLines.push(value);
  }
  if (!dataLines.length) return null;
  try {
    return { id, event, data: JSON.parse(dataLines.join('\n')) as unknown };
  } catch {
    throw new WorkflowRunClientError('Workflow event stream contained invalid JSON', {
      code: 'INVALID_EVENT_ENVELOPE',
    });
  }
}

function trimSequences(sequences: Set<number>): void {
  if (sequences.size <= MAX_DEDUPE_SEQUENCES) return;
  const oldest = sequences.values().next().value;
  if (typeof oldest === 'number') sequences.delete(oldest);
}

async function readWorkflowApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const detail = isRecord(payload) && isRecord(payload.detail) ? payload.detail : undefined;
  const message =
    stringValue(detail?.message) ??
    stringValue(payload && isRecord(payload) ? payload.message : undefined) ??
    response.statusText ??
    'Workflow request failed';
  const code = stringValue(detail?.code) ?? stringValue(payload && isRecord(payload) ? payload.code : undefined);
  return new ApiError(response.status, message, code, payload);
}

function asWorkflowRunClientError(error: unknown): WorkflowRunClientError {
  if (error instanceof WorkflowRunClientError) return error;
  if (error instanceof ApiError) {
    return new WorkflowRunClientError(error.message, { status: error.status, code: error.code });
  }
  return new WorkflowRunClientError(error instanceof Error ? error.message : 'Workflow event stream failed', {
    code: 'SSE_CONNECTION_FAILED',
  });
}

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `workflow-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function cursorStorageKey(runId: string): string {
  return `securehub-workflow-run:${runId}:last-event-id`;
}

function safeStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = globalThis.setTimeout(resolve, ms);
    signal.addEventListener(
      'abort',
      () => {
        globalThis.clearTimeout(timer);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true },
    );
  });
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function isRecord(value: unknown): value is JsonRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function nullableString(value: unknown): string | null | undefined {
  if (value === null) return null;
  return stringValue(value);
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isInteger(value) && value >= 0) return value;
  if (typeof value === 'string' && /^\d+$/.test(value)) return Number(value);
  return undefined;
}

function modeValue(value: unknown): WorkflowRunMode | undefined {
  return value === 'fixture' || value === 'real' ? value : undefined;
}

function shouldForwardWorkflowEvent(state: WorkflowRunViewState, event: WorkflowEvent): boolean {
  if (state.terminalEvent) return false;
  if (event.event_type !== 'token') return true;

  const stepKey = event.payload.step_attempt_id ?? event.payload.node_id ?? 'root';
  const activeDraftKey = state.activeStreamByStep[stepKey];
  if (!activeDraftKey) return true;
  const incomingDraftKey = `${stepKey}:${event.payload.provider_call_id ?? 'legacy'}:${event.payload.stream_attempt ?? 0}`;
  if (activeDraftKey === incomingDraftKey) return true;
  return Boolean(
    event.payload.replace_draft ||
      event.payload.replaces_stream_attempt != null ||
      state.replacementPendingByStep[stepKey],
  );
}

export function workflowEventToArtifact(event: WorkflowEvent): WorkflowArtifactPayload | undefined {
  return event.event_type === 'artifact' ? event.payload : undefined;
}

export function workflowEventToDone(event: WorkflowEvent): WorkflowDonePayload | undefined {
  return event.event_type === 'done' ? event.payload : undefined;
}

export function workflowEventToError(event: WorkflowEvent): WorkflowErrorPayload | undefined {
  return event.event_type === 'error' ? event.payload : undefined;
}
