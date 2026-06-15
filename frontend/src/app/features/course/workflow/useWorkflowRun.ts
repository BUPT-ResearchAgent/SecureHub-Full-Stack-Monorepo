import { useCallback, useEffect, useReducer, useRef } from 'react';
import type { AgentRunDTO } from '@/lib/sse.types';
import type { WorkflowDefinition, WorkflowReplayStep } from './types';
import { createInitialRunState, createMockReplaySteps, workflowRunReducer } from './runtime';

function runId(workflowId: string): string {
  return `${workflowId}-${Date.now()}`;
}

export function useWorkflowRun(workflow: WorkflowDefinition) {
  const [state, dispatch] = useReducer(
    workflowRunReducer,
    workflow,
    (initialWorkflow) => createInitialRunState(initialWorkflow),
  );
  const timersRef = useRef<number[]>([]);
  const stepsRef = useRef<WorkflowReplayStep[]>([]);
  const elapsedRef = useRef(0);
  const startedAtRef = useRef(0);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }, []);

  const applyStep = useCallback((step: WorkflowReplayStep) => {
    if (step.type === 'node') dispatch({ type: 'patchNode', nodeId: step.nodeId, patch: step.patch });
    if (step.type === 'edge') dispatch({ type: 'setEdge', edgeId: step.edgeId, status: step.status });
    if (step.type === 'resources') dispatch({ type: 'markResources', resources: step.resources });
    if (step.type === 'quality') dispatch({ type: 'setQuality', score: step.score });
    if (step.type === 'phase') dispatch({ type: 'setPhase', phase: step.phase });
  }, []);

  const schedule = useCallback(
    (steps: WorkflowReplayStep[], elapsed: number) => {
      clearTimers();
      steps
        .filter((step) => step.at > elapsed)
        .forEach((step) => {
          const timer = window.setTimeout(() => applyStep(step), step.at - elapsed);
          timersRef.current.push(timer);
        });
    },
    [applyStep, clearTimers],
  );

  const reset = useCallback(() => {
    clearTimers();
    elapsedRef.current = 0;
    startedAtRef.current = 0;
    stepsRef.current = [];
    dispatch({ type: 'reset', workflow });
  }, [clearTimers, workflow]);

  const beginExternalRun = useCallback(() => {
    clearTimers();
    elapsedRef.current = 0;
    startedAtRef.current = performance.now();
    stepsRef.current = [];
    dispatch({ type: 'reset', workflow, phase: 'running', runId: runId(workflow.id) });
  }, [clearTimers, workflow]);

  const run = useCallback(() => {
    if (state.phase === 'paused' && stepsRef.current.length) {
      startedAtRef.current = performance.now() - elapsedRef.current;
      dispatch({ type: 'setPhase', phase: 'running' });
      schedule(stepsRef.current, elapsedRef.current);
      return;
    }

    const steps = createMockReplaySteps(workflow.id);
    stepsRef.current = steps;
    elapsedRef.current = 0;
    startedAtRef.current = performance.now();
    dispatch({ type: 'reset', workflow, phase: 'running', runId: runId(workflow.id) });
    schedule(steps, 0);
  }, [schedule, state.phase, workflow]);

  const pause = useCallback(() => {
    if (state.phase !== 'running') return;
    elapsedRef.current = performance.now() - startedAtRef.current;
    clearTimers();
    dispatch({ type: 'setPhase', phase: 'paused' });
  }, [clearTimers, state.phase]);

  const applyTrace = useCallback((run: AgentRunDTO) => {
    dispatch({ type: 'applyTrace', run });
  }, []);

  useEffect(() => {
    reset();
    return clearTimers;
  }, [clearTimers, reset]);

  return {
    state,
    run,
    pause,
    reset,
    beginExternalRun,
    applyTrace,
  };
}
