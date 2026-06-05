export type TokenEvent = { content: string };
export type EvidenceEvent = {
  chunk_id: string;
  source: string;
  excerpt: string;
  reliability: number;
};
export type ProgressEvent = {
  node_name: string;
  status: string;
  agent_id?: string | null;
  skill_id?: string | null;
  percentage: number;
};
export type DoneEvent = {
  run_id: string;
  final_output_ref?: string | null;
  quality_score?: number | null;
};
export type StreamErrorEvent = {
  code: string;
  message: string;
  recoverable: boolean;
};

export type SSEHandlers = {
  onToken?: (event: TokenEvent) => void;
  onEvidence?: (event: EvidenceEvent) => void;
  onProgress?: (event: ProgressEvent) => void;
  onDone?: (event: DoneEvent) => void;
  onError?: (event: StreamErrorEvent) => void;
};

function parseEvent<T>(message: MessageEvent<string>): T {
  return JSON.parse(message.data || '{}') as T;
}

export function streamTask(url: string, handlers: SSEHandlers): () => void {
  const eventSource = new EventSource(url, { withCredentials: true });
  eventSource.addEventListener('token', (message) => {
    handlers.onToken?.(parseEvent<TokenEvent>(message as MessageEvent<string>));
  });
  eventSource.addEventListener('evidence', (message) => {
    handlers.onEvidence?.(parseEvent<EvidenceEvent>(message as MessageEvent<string>));
  });
  eventSource.addEventListener('progress', (message) => {
    handlers.onProgress?.(parseEvent<ProgressEvent>(message as MessageEvent<string>));
  });
  eventSource.addEventListener('done', (message) => {
    handlers.onDone?.(parseEvent<DoneEvent>(message as MessageEvent<string>));
    eventSource.close();
  });
  eventSource.addEventListener('error', () => {
    handlers.onError?.({ code: 'sse_error', message: 'SSE connection failed', recoverable: true });
  });
  return () => eventSource.close();
}
