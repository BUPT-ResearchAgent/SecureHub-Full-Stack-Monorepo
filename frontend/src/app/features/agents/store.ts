// Status: real
import { createContext, createElement, useContext, type Dispatch, type ReactNode } from 'react';
import { usePersistedReducer } from '@/lib/persist';
import type { AgentRunDTO } from './types';
import { getRunId } from './utils';

export type AgentTraceState = {
  runs: AgentRunDTO[];
  loading: boolean;
  error?: string;
};

export type AgentTraceAction =
  | { type: 'setLoading'; loading: boolean }
  | { type: 'setError'; error?: string }
  | { type: 'replaceRuns'; runs: AgentRunDTO[] }
  | { type: 'upsertRun'; run: AgentRunDTO };

export const initialAgentTraceState: AgentTraceState = {
  runs: [],
  loading: false,
};

export function agentTraceReducer(state: AgentTraceState, action: AgentTraceAction): AgentTraceState {
  switch (action.type) {
    case 'setLoading':
      return { ...state, loading: action.loading };
    case 'setError':
      return { ...state, error: action.error };
    case 'replaceRuns':
      return { ...state, runs: action.runs, loading: false, error: undefined };
    case 'upsertRun': {
      const id = getRunId(action.run);
      if (!id) return state;
      const exists = state.runs.some((run) => getRunId(run) === id);
      const runs = exists
        ? state.runs.map((run) => (getRunId(run) === id ? { ...run, ...action.run } : run))
        : [action.run, ...state.runs];
      return { ...state, runs };
    }
    default:
      return state;
  }
}

const AgentTraceStateContext = createContext<AgentTraceState | null>(null);
const AgentTraceDispatchContext = createContext<Dispatch<AgentTraceAction> | null>(null);

export function AgentTraceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = usePersistedReducer(agentTraceReducer, initialAgentTraceState, 'securehub-agents-trace');
  return createElement(
    AgentTraceStateContext.Provider,
    { value: state },
    createElement(AgentTraceDispatchContext.Provider, { value: dispatch }, children),
  );
}

export function useAgentTraceState(): AgentTraceState {
  const state = useContext(AgentTraceStateContext);
  if (!state) throw new Error('useAgentTraceState 必须在 AgentTraceProvider 内使用');
  return state;
}

export function useAgentTraceDispatch(): Dispatch<AgentTraceAction> {
  const dispatch = useContext(AgentTraceDispatchContext);
  if (!dispatch) throw new Error('useAgentTraceDispatch 必须在 AgentTraceProvider 内使用');
  return dispatch;
}
