import { useCallback, useEffect, useMemo, useRef } from 'react';

export function useRafTokenBuffer(flush: (targetId: string, content: string) => void) {
  const queuesRef = useRef<Record<string, string>>({});
  const frameRef = useRef<number | null>(null);
  const flushRef = useRef(flush);

  useEffect(() => {
    flushRef.current = flush;
  }, [flush]);

  const drain = useCallback(() => {
    frameRef.current = null;
    const entries = Object.entries(queuesRef.current).filter(([, content]) => content.length > 0);
    queuesRef.current = {};
    entries.forEach(([targetId, content]) => flushRef.current(targetId, content));
  }, []);

  const push = useCallback((targetId: string, content: string) => {
    if (!content) return;
    queuesRef.current[targetId] = `${queuesRef.current[targetId] ?? ''}${content}`;
    if (frameRef.current == null) {
      frameRef.current = window.requestAnimationFrame(drain);
    }
  }, [drain]);

  const cancel = useCallback(() => {
    if (frameRef.current != null) {
      window.cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
    queuesRef.current = {};
  }, []);

  useEffect(() => cancel, []);

  return useMemo(() => ({ push, flush: drain, cancel }), [push, drain, cancel]);
}
