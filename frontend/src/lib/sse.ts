import { useEffect } from 'react';
import type {
  ArtifactEvent,
  DoneEvent,
  ErrorEvent as SSEErrorEvent,
  EvidenceChunkDTO,
  EvidenceEvent,
  ProgressEvent,
  SSEEvent,
  TokenEvent,
  TraceEvent,
} from './sse.types';

export type {
  AgentRunDTO,
  ArtifactEvent,
  DoneEvent,
  ErrorEvent,
  EvidenceChunkDTO,
  EvidenceEvent,
  ProgressEvent,
  ResourceType,
  SSEEvent,
  TokenEvent,
  TraceEvent,
} from './sse.types';

const EVENT_NAMES = ['progress', 'evidence', 'token', 'artifact', 'trace', 'done', 'error'] as const;

type EventName = (typeof EVENT_NAMES)[number];
type EventByName<T extends EventName> = Extract<SSEEvent, { event: T }>;

export type SSEHandlers = {
  onToken?: (event: TokenEvent['data']) => void;
  onEvidence?: (event: EvidenceChunkDTO) => void;
  onProgress?: (event: ProgressEvent['data']) => void;
  onArtifact?: (event: ArtifactEvent['data']) => void;
  onTrace?: (event: TraceEvent['data']) => void;
  onDone?: (event: DoneEvent['data']) => void;
  onError?: (event: SSEErrorEvent['data']) => void;
};

type OpenSSEOptions = {
  onEvent: (e: SSEEvent) => void;
  onError?: (e: unknown) => void;
};

function parseMessage<T>(message: MessageEvent<string>): T {
  return JSON.parse(message.data || '{}') as T;
}

function hasMessageData(event: Event): event is MessageEvent<string> {
  return 'data' in event && typeof (event as MessageEvent<string>).data === 'string';
}

function normalizeEvidence(data: EvidenceEvent['data'] | EvidenceChunkDTO): EvidenceEvent['data'] {
  return Array.isArray(data) ? data : [data];
}

function dispatchEventByName(eventName: EventName, rawData: unknown, opts?: OpenSSEOptions) {
  const normalized =
    eventName === 'evidence' ? normalizeEvidence(rawData as EvidenceEvent['data']) : rawData;
  opts?.onEvent({ event: eventName, data: normalized } as SSEEvent);
}

function dispatchHandlers(event: SSEEvent, handlers: SSEHandlers) {
  switch (event.event) {
    case 'token':
      handlers.onToken?.(event.data);
      break;
    case 'evidence':
      for (const chunk of event.data) {
        handlers.onEvidence?.(chunk);
      }
      break;
    case 'progress':
      handlers.onProgress?.(event.data);
      break;
    case 'artifact':
      handlers.onArtifact?.(event.data);
      break;
    case 'trace':
      handlers.onTrace?.(event.data);
      break;
    case 'done':
      handlers.onDone?.(event.data);
      break;
    case 'error':
      handlers.onError?.(event.data);
      break;
  }
}

function parseSSEBlock(block: string): { eventName: EventName; data: unknown } | null {
  let eventName: EventName = 'token';
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '');
    if (field === 'event' && EVENT_NAMES.includes(value as EventName)) {
      eventName = value as EventName;
    }
    if (field === 'data') {
      dataLines.push(value);
    }
  }

  if (!dataLines.length) return null;
  const dataText = dataLines.join('\n');
  return {
    eventName,
    data: JSON.parse(dataText || '{}'),
  };
}

export function openSSE(url: string, opts?: OpenSSEOptions): () => void {
  const source = new EventSource(url);

  for (const eventName of EVENT_NAMES) {
    source.addEventListener(eventName, (message) => {
      if (!hasMessageData(message)) {
        opts?.onError?.(message);
        return;
      }
      try {
        const data = parseMessage<EventByName<typeof eventName>['data']>(message);
        dispatchEventByName(eventName, data, opts);
      } catch (error) {
        opts?.onError?.(error);
      }
    });
  }

  source.onerror = (event) => {
    opts?.onError?.(event);
  };

  return () => source.close();
}

export function openSSEPost(
  url: string,
  body: unknown,
  opts?: OpenSSEOptions & {
    headers?: HeadersInit;
  },
): () => void {
  const controller = new AbortController();
  const maxRetries = 1;
  const retryDelay = 2000;

  const sleep = (delay: number) =>
    new Promise((resolve) => {
      window.setTimeout(resolve, delay);
    });

  const connect = async (attempt: number): Promise<void> => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Accept: 'text/event-stream',
          'Content-Type': 'application/json',
          ...opts?.headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        let message = '流式请求失败';
        let code: string | undefined;
        try {
          const payload = await response.json();
          const detail = (payload as { detail?: unknown }).detail;
          if (typeof detail === 'string') {
            message = detail;
          } else if (detail && typeof detail === 'object') {
            const detailMessage = (detail as { message?: unknown }).message;
            const detailCode = (detail as { code?: unknown }).code;
            if (typeof detailMessage === 'string') message = detailMessage;
            if (typeof detailCode === 'string') code = detailCode;
          }
        } catch {
          message = response.statusText || message;
        }
        dispatchEventByName('error', { code, message, recoverable: response.status < 500 }, opts);
        return;
      }

      if (!response.body) {
        dispatchEventByName('error', { code: 'EmptyStream', message: '后端没有返回流式内容', recoverable: true }, opts);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() ?? '';
        for (const block of blocks) {
          try {
            const parsed = parseSSEBlock(block);
            if (parsed) {
              dispatchEventByName(parsed.eventName, parsed.data, opts);
            }
          } catch (error) {
            opts?.onError?.(error);
          }
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) {
        const parsed = parseSSEBlock(buffer);
        if (parsed) {
          dispatchEventByName(parsed.eventName, parsed.data, opts);
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      if (attempt < maxRetries) {
        dispatchEventByName(
          'error',
          { code: 'sse_reconnecting', message: '网络中断，正在重连…', recoverable: true },
          opts,
        );
        await sleep(retryDelay);
        if (!controller.signal.aborted) {
          await connect(attempt + 1);
        }
        return;
      }
      opts?.onError?.(error);
    }
  };

  void connect(0);

  return () => controller.abort();
}

export function useSSE(
  url: string | null | undefined,
  opts?: OpenSSEOptions,
): void {
  useEffect(() => {
    if (!url) return undefined;
    return openSSE(url, opts);
  }, [url, opts]);
}

export function streamTask(url: string, handlers: SSEHandlers): () => void {
  return openSSE(url, {
    onEvent(event) {
      dispatchHandlers(event, handlers);
    },
    onError(error) {
      handlers.onError?.({
        code: 'sse_error',
        message: '流式连接失败',
        recoverable: true,
      });
      console.error(error);
    },
  });
}

export function streamTaskPost(url: string, body: unknown, handlers: SSEHandlers, headers?: HeadersInit): () => void {
  return openSSEPost(url, body, {
    headers,
    onEvent(event) {
      dispatchHandlers(event, handlers);
    },
    onError(error) {
      handlers.onError?.({
        code: 'sse_error',
        message: '流式连接失败',
        recoverable: true,
      });
      console.error(error);
    },
  });
}
