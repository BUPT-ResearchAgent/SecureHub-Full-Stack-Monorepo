import type { Dispatch } from 'react';
import type { WorkflowProductHandlers } from '../api';
import type { CourseAction } from '../store';
import type { CourseWorkflowRoot, ResourceItem, SupportedTaskIntent } from '../types';
import type { WorkflowEvent, WorkflowRunStartResponse, WorkflowRunStatusResponse, WorkflowRunViewState } from '@/lib/workflow-run.types';

/**
 * Projects durable workflow metadata into the per-course persisted store.
 * Rendering components retain ownership of their own token/artifact views;
 * this lifecycle is only the durable root and recovery projection.
 */
export function createCourseTaskLifecycle(
  intent: SupportedTaskIntent,
  dispatch: Dispatch<CourseAction>,
  downstream: WorkflowProductHandlers = {},
  initialRoot?: CourseWorkflowRoot,
): WorkflowProductHandlers {
  let root: CourseWorkflowRoot | undefined = initialRoot;

  const projectArtifact = (event: Extract<WorkflowEvent, { event_type: 'artifact' }>, status: ResourceItem['status']) => {
    const existing = event.payload;
    dispatch({
      type: 'upsertResource',
      resource: {
        id: existing.resource_id,
        type: existing.resource_type,
        title: existing.title,
        status,
        content: '',
        evidenceRefs: [],
        qualityScore: existing.quality_score ?? undefined,
      },
    });
  };

  const publish = (state: WorkflowRunViewState) => {
    if (!root) return;
    root = {
      ...root,
      status: state.status,
      provider: state.actualProvider ?? root.provider,
      model: state.actualModel ?? root.model,
      evidenceCount: Object.keys(state.evidence).length,
      artifactIds: Object.keys(state.artifacts),
      lastSequence: state.lastSequence,
      updatedAt: new Date().toISOString(),
      error: state.error
        ? { code: state.error.code, message: state.error.message, recoverable: state.error.recoverable }
        : undefined,
    };
    dispatch({ type: 'upsertWorkflowRoot', root });
  };

  return {
    ...downstream,
    onWorkflowStart(start: WorkflowRunStartResponse) {
      root = {
        runId: start.run_id,
        intent,
        workflow: start.workflow,
        status: start.status,
        mode: start.mode,
        provider: start.actual_provider ?? start.provider,
        model: start.actual_model ?? start.model,
        evidenceCount: 0,
        artifactIds: [],
        lastSequence: 0,
        updatedAt: new Date().toISOString(),
      };
      dispatch({ type: 'upsertWorkflowRoot', root });
      downstream.onWorkflowStart?.(start);
    },
    onWorkflowState(state: WorkflowRunViewState) {
      publish(state);
      downstream.onWorkflowState?.(state);
    },
    onWorkflowEvent(event: WorkflowEvent) {
      if (event.event_type === 'artifact') projectArtifact(event, 'generating');
      downstream.onWorkflowEvent?.(event);
    },
    onWorkflowTerminal(status: WorkflowRunStatusResponse, state: WorkflowRunViewState) {
      publish({ ...state, status: status.status, error: status.error ?? state.error });
      if (status.status === 'succeeded') {
        Object.values(state.artifacts).forEach((artifact) => {
          projectArtifact({
            workflow_run_id: state.runId,
            sequence: state.lastSequence,
            event_type: 'artifact',
            payload: artifact,
          }, 'ready');
        });
      }
      downstream.onWorkflowTerminal?.(status, state);
    },
    onError(error) {
      if (root) {
        const updatedRoot: CourseWorkflowRoot = {
          ...root,
          updatedAt: new Date().toISOString(),
          error: {
            code: error.code ?? 'WORKFLOW_CLIENT_ERROR',
            message: error.message,
            recoverable: error.recoverable,
          },
        };
        root = updatedRoot;
        dispatch({ type: 'upsertWorkflowRoot', root: updatedRoot });
      }
      downstream.onError?.(error);
    },
  };
}
