// Status: real
//
// Product helpers intentionally create and observe a durable workflow root.
// Fixture replay remains available only through the explicit PresenterMode flag.

import type { AssessmentRunResponse, CoursePlanResponse } from '@/lib/api-types';
import { isMockMode } from '@/lib/mock';
import { replayAssessment, replayPersonaChat, replayResourceGeneration, replayTutorAsk } from '@/lib/mock/course.mock';
import type { SSEHandlers } from '@/lib/sse';
import {
  WorkflowRunClient,
  WorkflowRunClientError,
  type WorkflowSubscription,
} from '@/lib/workflow-run-client';
import type {
  WorkflowEvent,
  WorkflowRunStartRequest,
  WorkflowRunStartResponse,
  WorkflowRunStatusResponse,
  WorkflowRunViewState,
} from '@/lib/workflow-run.types';
import { mockLearningPath } from './mockData';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem, ResourceType } from './types';

// UUIDv5 identity from the frozen course_websec seed for `sql-injection`.
const demoTargetNodeId = 'e96f770a-57d0-5b49-a7d6-3af1de08e115';
const workflowRunClient = new WorkflowRunClient();

const PRODUCT_WORKFLOWS = {
  profile: 'profile_build_v1',
  coursePlan: 'course_plan_v1',
  resource: 'resource_generate_v1',
  tutor: 'tutor_routing_v1',
  assessment: 'assessment_update_v1',
} as const;

export type TaskResponse = {
  task_id: string;
  status: string;
};

export type ResourceGenerationBody = {
  user_id: string;
  kp_id: string;
  options?: Record<string, unknown>;
};

export type WorkflowProductHandlers = SSEHandlers & {
  onWorkflowStart?: (start: WorkflowRunStartResponse) => void;
  onWorkflowEvent?: (event: WorkflowEvent) => void;
  onWorkflowState?: (state: WorkflowRunViewState) => void;
};

function contractUuid(value: string, fallback: string): string {
  return /^[0-9a-f-]{36}$/i.test(value) ? value : fallback;
}

function adaptPlanResponse(response: CoursePlanResponse, fallbackCourseId: string): LearningPath {
  const nodes = response.path.map((node, index) => ({
    id: node.node_id,
    label: node.title,
    status: node.status === 'in_progress' ? 'active' as const : node.status,
    priority: index + 1,
  }));
  const edges = response.path.flatMap((node) =>
    node.prerequisites.map((source) => ({
      id: `${source}-${node.node_id}`,
      source,
      target: node.node_id,
    })),
  );
  return {
    courseId: response.course_id || fallbackCourseId,
    nodes,
    edges,
    milestones: nodes.map((node, index) => ({
      id: `milestone-${node.id}`,
      title: node.label,
      week: index + 1,
    })),
  };
}

function startWorkflowStream(
  request: WorkflowRunStartRequest,
  handlers: WorkflowProductHandlers,
): () => void {
  let disposed = false;
  let subscription: WorkflowSubscription | undefined;

  void workflowRunClient
    .start({ ...request, mode: 'real' })
    .then((start) => {
      if (disposed) return;
      handlers.onWorkflowStart?.(start);
      subscription = workflowRunClient.subscribe(start.run_id, {
        eventsUrl: start.events_url,
        initialState: {
          ...handlersInitialState(start),
        },
        onEvent: (event) => {
          handlers.onWorkflowEvent?.(event);
          dispatchWorkflowEvent(event, handlers);
        },
        onState: handlers.onWorkflowState,
        onConnection: (state) => {
          if (state === 'reconnecting') {
            handlers.onError?.({
              code: 'sse_reconnecting',
              message: '连接中断，正在从已确认事件恢复。',
              recoverable: true,
            });
          }
        },
        onError: (error) => {
          handlers.onError?.({
            code: error.code ?? 'sse_error',
            message: error.message,
            recoverable: error.code !== 'SSE_SEQUENCE_GAP',
          });
        },
      });
    })
    .catch((error: unknown) => {
      if (disposed) return;
      const clientError = error instanceof WorkflowRunClientError
        ? error
        : new WorkflowRunClientError(error instanceof Error ? error.message : '工作流启动失败');
      handlers.onError?.({
        code: clientError.code ?? 'WORKFLOW_START_FAILED',
        message: clientError.message,
        recoverable: false,
      });
    });

  return () => {
    disposed = true;
    // Disconnecting a view is deliberately not a workflow cancellation. Durable
    // cancellation is only available through WorkflowRunClient.cancel(runId).
    subscription?.unsubscribe();
  };
}

function handlersInitialState(start: WorkflowRunStartResponse): WorkflowRunViewState {
  return {
    runId: start.run_id,
    status: start.status,
    mode: start.mode,
    requestedProvider: start.requested_provider,
    requestedModel: start.requested_model,
    actualProvider: start.actual_provider ?? start.provider,
    actualModel: start.actual_model ?? start.model,
    nodes: {},
    evidence: {},
    artifacts: {},
    traces: {},
    tokenDrafts: {},
    activeStreamByStep: {},
    replacementPendingByStep: {},
    lastSequence: 0,
  };
}

function dispatchWorkflowEvent(event: WorkflowEvent, handlers: WorkflowProductHandlers): void {
  switch (event.event_type) {
    case 'progress': {
      const payload = event.payload;
      const status = payload.node_status ?? payload.status;
      handlers.onProgress?.({
        node_name: payload.node_name ?? payload.node_id ?? 'workflow',
        agent_id: payload.agent_id ?? payload.agent_name,
        skill_id: payload.skill_id ?? payload.skill_name,
        percentage: payload.percentage,
        status: status === 'failed' || status === 'blocked' ? 'failed' : status === 'succeeded' || status === 'done' ? 'done' : 'running',
      });
      return;
    }
    case 'evidence': {
      const payload = event.payload;
      payload.items.forEach((item) => handlers.onEvidence?.(item));
      return;
    }
    case 'token': {
      const payload = event.payload;
      handlers.onToken?.({ content: payload.content, index: payload.index });
      return;
    }
    case 'artifact': {
      const payload = event.payload;
      handlers.onArtifact?.({
        resource_id: payload.resource_id,
        resource_type: payload.resource_type,
        object_key: payload.object_key ?? undefined,
        title: payload.title,
      });
      return;
    }
    case 'trace': {
      const payload = event.payload;
      handlers.onTrace?.({
        id: payload.agent_run_id ?? payload.id,
        run_id: payload.run_id ?? event.workflow_run_id,
        agent_name: payload.agent_name ?? payload.agent_id ?? 'task_orchestrator',
        skill_name: payload.skill_name ?? payload.skill_id ?? 'WorkflowNode',
        status: payload.status ?? 'running',
        duration_ms: payload.duration_ms,
        quality_score: payload.quality_score,
        provider: event.actual_provider ?? event.provider ?? payload.provider,
        model: event.actual_model ?? event.model ?? payload.model,
      });
      return;
    }
    case 'done': {
      const payload = event.payload;
      handlers.onDone?.({
        run_id: event.workflow_run_id,
        final_output_ref: payload.final_output_ref ?? '',
        quality_score: payload.quality_score ?? 0,
      });
      return;
    }
    case 'error': {
      const payload = event.payload;
      handlers.onError?.({
        code: payload.code,
        message: payload.message,
        recoverable: payload.recoverable,
      });
      return;
    }
  }
}

type WorkflowTerminalResult = {
  state: WorkflowRunViewState;
  status: WorkflowRunStatusResponse;
};

async function runWorkflowToTerminal(
  request: WorkflowRunStartRequest,
): Promise<WorkflowTerminalResult> {
  const start = await workflowRunClient.start({ ...request, mode: 'real' });
  const terminal = await workflowRunClient.waitForTerminal(start);
  if (terminal.status !== 'succeeded') {
    throw new WorkflowRunClientError(terminal.error?.message ?? `工作流终态为 ${terminal.status}`, {
      code: terminal.error?.code ?? terminal.status,
    });
  }
  return { state: terminal, status: await workflowRunClient.status(start.run_id) };
}

function finalOutputAs<T>(terminal: WorkflowTerminalResult): T {
  const finalOutput = terminal.status.final_output;
  if (finalOutput && typeof finalOutput === 'object') {
    // RuntimeEngine wraps the terminal action/skill result with durable
    // metadata (`ref`, quality score). Product mappers consume the persisted
    // domain payload, never the wrapper itself.
    const payload = (finalOutput as Record<string, unknown>).output;
    if (payload && typeof payload === 'object' && !Array.isArray(payload)) return payload as T;
    return finalOutput as T;
  }
  throw new WorkflowRunClientError('工作流没有返回可映射的最终输出', {
    code: 'WORKFLOW_OUTPUT_MISSING',
  });
}

export function streamPersonaChat(
  userId: string,
  message: string,
  history: Array<Record<string, unknown>>,
  handlers: WorkflowProductHandlers,
): () => void {
  if (isMockMode()) return replayPersonaChat(message, handlers);
  return startWorkflowStream(
    {
      workflow: PRODUCT_WORKFLOWS.profile,
      user_id: userId,
      input: { message, history },
    },
    handlers,
  );
}

export async function planLearning(courseId: string, userId: string, targetNodeId: string): Promise<LearningPath> {
  if (isMockMode()) return { ...mockLearningPath, courseId };
  const terminal = await runWorkflowToTerminal({
    workflow: PRODUCT_WORKFLOWS.coursePlan,
    user_id: userId,
    course_id: courseId,
    input: {
      target_node_id: contractUuid(targetNodeId, demoTargetNodeId),
      options: { depth: 3, local_target_node_id: targetNodeId },
    },
  });
  return adaptPlanResponse(finalOutputAs<CoursePlanResponse>(terminal), courseId);
}

export function streamResourceGeneration(
  courseId: string,
  type: ResourceType,
  body: ResourceGenerationBody,
  handlers: WorkflowProductHandlers,
): () => void {
  if (isMockMode()) return replayResourceGeneration(type, handlers);
  return startWorkflowStream(
    {
      workflow: PRODUCT_WORKFLOWS.resource,
      user_id: body.user_id,
      course_id: courseId,
      input: {
        resource_type: type,
        kp_id: contractUuid(body.kp_id, demoTargetNodeId),
        options: { ...body.options, local_kp_id: body.kp_id },
      },
    },
    handlers,
  );
}

export function streamTutorAsk(
  userId: string,
  courseId: string,
  question: string,
  kpId: string,
  handlers: WorkflowProductHandlers,
): () => void {
  if (isMockMode()) return replayTutorAsk(question, handlers);
  return startWorkflowStream(
    {
      workflow: PRODUCT_WORKFLOWS.tutor,
      user_id: userId,
      course_id: courseId,
      input: { question, context: { kp_id: kpId } },
    },
    handlers,
  );
}

export async function runAssessment(
  userId: string,
  courseId: string,
  answers: Array<Record<string, unknown>>,
): Promise<AssessmentReport> {
  if (isMockMode()) {
    const mock = await replayAssessment(answers);
    const updatedCapabilities = mock.updatedCapabilities ?? [];
    return {
      score: mock.score,
      scoreVector: Object.fromEntries(updatedCapabilities.map((item) => [item.dimension, item.score])),
      feedback: mock.feedback,
      updatedProfile: {},
      updatedCapabilities,
    };
  }

  const terminal = await runWorkflowToTerminal({
    workflow: PRODUCT_WORKFLOWS.assessment,
    user_id: userId,
    course_id: courseId,
    input: { answers },
  });
  const response = finalOutputAs<AssessmentRunResponse>(terminal);
  return {
    score: response.score,
    scoreVector: Object.fromEntries((response.updated_capabilities ?? []).map((item) => [item.dimension, item.score])),
    feedback: [response.feedback],
    updatedProfile: {},
    updatedCapabilities: response.updated_capabilities,
  };
}

export { workflowRunClient };

export type CourseApiSnapshot = {
  persona: LearningPersona;
  path: LearningPath;
  resources: ResourceItem[];
};
