// Status: real
import { useEffect, useReducer, type Dispatch, type Reducer } from 'react';
import { AUTH_SESSION_TOKEN_STORAGE_KEY, AUTH_TOKEN_STORAGE_KEY } from './api';

export function usePersistedReducer<S, A>(
  reducer: Reducer<S, A>,
  initial: S,
  storageKey: string,
): [S, Dispatch<A>] {
  const [state, dispatch] = useReducer(reducer, initial, (fallback) => {
    if (typeof window === 'undefined') return fallback;
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return fallback;
      return JSON.parse(raw) as S;
    } catch {
      return fallback;
    }
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
      // localStorage 配额或隐私模式失败时不阻断主流程。
    }
  }, [state, storageKey]);

  return [state, dispatch];
}

export function clearSecureHubPersistedState(): void {
  if (typeof window === 'undefined') return;
  Object.keys(window.localStorage).forEach((key) => {
    if (!key.startsWith('securehub-')) return;
    if (key === AUTH_TOKEN_STORAGE_KEY || key === AUTH_SESSION_TOKEN_STORAGE_KEY) return;
    window.localStorage.removeItem(key);
  });
}
