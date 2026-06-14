// Status: mock
import type { SSEHandlers } from '@/lib/sse';
import type { SSEEvent } from '@/lib/sse.types';

export function replaySSEEvents(events: SSEEvent[], handlers: SSEHandlers, interval = 120): () => void {
  const timers: number[] = [];

  events.forEach((event, index) => {
    const timer = window.setTimeout(() => {
      switch (event.event) {
        case 'progress':
          handlers.onProgress?.(event.data);
          break;
        case 'evidence':
          event.data.forEach((chunk) => handlers.onEvidence?.(chunk));
          break;
        case 'token':
          handlers.onToken?.(event.data);
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
    }, index * interval);
    timers.push(timer);
  });

  return () => {
    timers.forEach((timer) => window.clearTimeout(timer));
  };
}
