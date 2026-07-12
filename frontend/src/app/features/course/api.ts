// Status: real
//
// Product helpers intentionally create and observe a durable workflow root.
// This module never silently falls back to fixture data. A caller that needs a
// PresenterMode root must explicitly pass `{ mode: 'fixture' }` to
// `startCourseTask`; real workflow errors stay real.

import type { AssessmentRunResponse, CoursePlanResponse } from '@/lib/api-types';
import type { SSEHandlers } from '@/lib/sse';
import {
  WorkflowRunClient,
  WorkflowRunClientError,
  type WorkflowSubscription,
} from '@/lib/workflow-run-client';
import {
  isTerminalWorkflowStatus,
  type WorkflowEvent,
  type WorkflowRunStartRequest,
  type WorkflowRunStartResponse,
  type WorkflowRunStatusResponse,
  type WorkflowRunViewState,
} from '@/lib/workflow-run.types';
import { SUPPORTED_TASK_INTENTS } from './types';
import type {
  AssessmentReport,
  CourseTaskCommand,
  CourseTaskContext,
  LearningPath,
  LearningPersona,
  PersonaDimensionKey,
  ResourceItem,
  ResourceType,
  SupportedTaskIntent,
} from './types';

const workflowRunClient = new WorkflowRunClient();
const UUID_PATTERN = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;

export const PRODUCT_WORKFLOWS = {
  build_persona: 'profile_build_v1',
  plan_course: 'course_plan_v1',
  generate_resource: 'resource_generate_v1',
  ask_tutor: 'tutor_routing_v1',
  run_assessment: 'assessment_update_v1',
} as const;

export type CourseTaskRunMode = 'real' | 'fixture';

export type CourseResourcePackOptions = {
  query?: string;
  options?: Record<string, unknown>;
  mode?: CourseTaskRunMode;
};

export type CourseResourceRetryOptions = {
  query?: string;
  options?: Record<string, unknown>;
  mode?: CourseTaskRunMode;
};

export class UnsupportedCourseTaskIntentError extends Error {
  readonly code = 'UNSUPPORTED_TASK_INTENT';

  constructor(intent: unknown) {
    super(`课程任务 intent 不受支持：${String(intent)}`);
    this.name = 'UnsupportedCourseTaskIntentError';
  }
}

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
  onWorkflowTerminal?: (status: WorkflowRunStatusResponse, state: WorkflowRunViewState) => void;
};

export function isSupportedTaskIntent(value: unknown): value is SupportedTaskIntent {
  return typeof value === 'string' && (SUPPORTED_TASK_INTENTS as readonly string[]).includes(value);
}

function assertUuid(value: string, field: string): string {
  if (/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(value)) return value;
  throw new WorkflowRunClientError(`${field} 必须是后端契约中的 UUID`, { code: 'INVALID_TASK_CONTEXT' });
}

export function createCourseTaskRequest(command: CourseTaskCommand): WorkflowRunStartRequest {
  const { context } = command;
  const courseId = assertUuid(context.courseId, 'courseId');
  const kpId = assertUuid(context.kpId, 'kpId');

  switch (command.intent) {
    case 'build_persona':
      return {
        workflow: PRODUCT_WORKFLOWS.build_persona,
        user_id: context.userId,
        course_id: courseId,
        input: { message: command.payload.message, history: command.payload.history },
      };
    case 'plan_course':
      return {
        workflow: PRODUCT_WORKFLOWS.plan_course,
        user_id: context.userId,
        course_id: courseId,
        input: {
          target_node_id: assertUuid(command.payload.targetNodeId, 'targetNodeId'),
          options: { depth: command.payload.depth ?? 3, current_path_node_ids: context.currentPathNodeIds },
        },
      };
    case 'generate_resource':
      return {
        workflow: PRODUCT_WORKFLOWS.generate_resource,
        user_id: context.userId,
        course_id: courseId,
        input: {
          resource_type: command.payload.resourceType,
          kp_id: kpId,
          options: command.payload.options ?? {},
        },
      };
    case 'ask_tutor':
      return {
        workflow: PRODUCT_WORKFLOWS.ask_tutor,
        user_id: context.userId,
        course_id: courseId,
        input: { question: command.payload.question, context: { kp_id: kpId, current_path_node_ids: context.currentPathNodeIds } },
      };
    case 'run_assessment':
      return {
        workflow: PRODUCT_WORKFLOWS.run_assessment,
        user_id: context.userId,
        course_id: courseId,
        input: { answers: command.payload.answers, context: { kp_id: kpId, current_path_node_ids: context.currentPathNodeIds } },
      };
    default:
      throw new UnsupportedCourseTaskIntentError((command as { intent?: unknown }).intent);
  }
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
  mode: CourseTaskRunMode = 'real',
): () => void {
  return startWorkflowSubscription(
    () => workflowRunClient.start({ ...request, mode }),
    handlers,
  );
}

function startWorkflowSubscription(
  startRoot: () => Promise<WorkflowRunStartResponse>,
  handlers: WorkflowProductHandlers,
): () => void {
  let disposed = false;
  let subscription: WorkflowSubscription | undefined;
  let terminalReported = false;

  void startRoot()
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
        onState: (state) => {
          handlers.onWorkflowState?.(state);
          if (!terminalReported && isTerminalWorkflowStatus(state.status)) {
            terminalReported = true;
            void workflowRunClient.status(start.run_id)
              .then((status) => handlers.onWorkflowTerminal?.(status, state))
              .catch((error: unknown) => reportTerminalProjectionError(error, handlers));
          }
        },
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

/** Starts one fresh durable root for a closed, typed course intent. */
export function startCourseTask(
  command: CourseTaskCommand,
  handlers: WorkflowProductHandlers,
  options: { mode?: CourseTaskRunMode } = {},
): () => void {
  const intent = (command as { intent?: unknown }).intent;
  if (!isSupportedTaskIntent(intent)) throw new UnsupportedCourseTaskIntentError(intent);
  return startWorkflowStream(createCourseTaskRequest(command), handlers, options.mode ?? 'real');
}

/** Starts the additive v2 six-resource bundle without changing the five task intents. */
export function startCourseResourcePack(
  context: CourseTaskContext,
  handlers: WorkflowProductHandlers,
  options: CourseResourcePackOptions = {},
): () => void {
  const courseId = assertUuid(context.courseId, 'courseId');
  const kpId = assertUuid(context.kpId, 'kpId');
  return startWorkflowStream(
    {
      workflow: 'course_learning_full_v2',
      user_id: context.userId,
      course_id: courseId,
      input: {
        kp_id: kpId,
        query: options.query ?? 'Generate the complete course resource pack',
        options: options.options ?? {},
      },
    },
    handlers,
    options.mode ?? 'real',
  );
}

/** Starts a distinct resource-only root linked to its owned parent artifact. */
export function retryCourseResource(
  resourceId: string,
  handlers: WorkflowProductHandlers,
  options: CourseResourceRetryOptions = {},
): () => void {
  if (!UUID_PATTERN.test(resourceId)) {
    throw new WorkflowRunClientError('resourceId 必须是后端契约中的 UUID', { code: 'INVALID_RESOURCE_ID' });
  }
  return startWorkflowSubscription(
    () => workflowRunClient.retryResource(resourceId, {
      query: options.query,
      options: options.options ?? {},
      mode: options.mode ?? 'real',
    }),
    handlers,
  );
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
  command: CourseTaskCommand,
): Promise<WorkflowTerminalResult> {
  const start = await workflowRunClient.start({ ...createCourseTaskRequest(command), mode: 'real' });
  const terminal = await workflowRunClient.waitForTerminal(start);
  if (terminal.status !== 'succeeded') {
    throw new WorkflowRunClientError(terminal.error?.message ?? `工作流终态为 ${terminal.status}`, {
      code: terminal.error?.code ?? terminal.status,
    });
  }
  return { state: terminal, status: await workflowRunClient.status(start.run_id) };
}

/** Re-subscribes to an existing root after a page refresh without creating another root. */
export function resumeCourseTask(
  runId: string,
  handlers: WorkflowProductHandlers,
): () => void {
  let disposed = false;
  let subscription: WorkflowSubscription | undefined;
  void workflowRunClient.status(runId)
    .then((status) => {
      if (disposed) return;
      const initialState: WorkflowRunViewState = {
        ...handlersInitialState({
          run_id: status.run_id,
          workflow: status.workflow,
          status: status.status,
          events_url: `/api/v1/workflow-runs/${status.run_id}/events`,
          cancel_url: `/api/v1/workflow-runs/${status.run_id}/cancel`,
          mode: status.mode,
          requested_provider: status.requested_provider,
          requested_model: status.requested_model,
          provider: status.provider,
          model: status.model,
          actual_provider: status.actual_provider,
          actual_model: status.actual_model,
        }),
        status: status.status,
      };
      handlers.onWorkflowState?.(initialState);
      if (isTerminalWorkflowStatus(status.status)) {
        handlers.onWorkflowTerminal?.(status, initialState);
        return;
      }
      subscription = workflowRunClient.subscribe(runId, {
        initialState,
        onEvent: (event) => {
          handlers.onWorkflowEvent?.(event);
          dispatchWorkflowEvent(event, handlers);
        },
        onState: (state) => {
          handlers.onWorkflowState?.(state);
          if (isTerminalWorkflowStatus(state.status)) {
            void workflowRunClient.status(runId)
              .then((terminal) => handlers.onWorkflowTerminal?.(terminal, state))
              .catch((error: unknown) => reportTerminalProjectionError(error, handlers));
          }
        },
        onError: (error) => handlers.onError?.({
          code: error.code ?? 'SSE_CONNECTION_FAILED',
          message: error.message,
          recoverable: error.code !== 'SSE_SEQUENCE_GAP',
        }),
      });
    })
    .catch((error: unknown) => {
      if (disposed) return;
      const clientError = error instanceof WorkflowRunClientError
        ? error
        : new WorkflowRunClientError(error instanceof Error ? error.message : '无法恢复工作流');
      handlers.onError?.({
        code: clientError.code ?? 'WORKFLOW_RESUME_FAILED',
        message: clientError.message,
        recoverable: false,
      });
    });

  return () => {
    disposed = true;
    subscription?.unsubscribe();
  };
}

function finalOutputFromStatus<T>(status: WorkflowRunStatusResponse): T {
  const finalOutput = status.final_output;
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

export function learningPathFromWorkflowStatus(
  status: WorkflowRunStatusResponse,
  fallbackCourseId: string,
): LearningPath {
  return adaptPlanResponse(finalOutputFromStatus<CoursePlanResponse>(status), fallbackCourseId);
}

export function assessmentReportFromWorkflowStatus(
  status: WorkflowRunStatusResponse,
): AssessmentReport {
  const response = finalOutputFromStatus<AssessmentRunResponse>(status);
  return {
    score: response.score,
    scoreVector: Object.fromEntries((response.updated_capabilities ?? []).map((item) => [item.dimension, item.score])),
    feedback: [response.feedback],
    updatedProfile: {},
    updatedCapabilities: response.updated_capabilities,
  };
}

export function learningPersonaFromWorkflowStatus(
  status: WorkflowRunStatusResponse,
  userId: string,
): LearningPersona {
  const output = finalOutputFromStatus<{ dimensions?: unknown }>(status);
  const rawDimensions = output.dimensions;
  if (!rawDimensions || typeof rawDimensions !== 'object' || Array.isArray(rawDimensions)) {
    throw new WorkflowRunClientError('画像工作流没有返回维度投影', { code: 'WORKFLOW_OUTPUT_INVALID' });
  }
  const dimensions = Object.fromEntries(
    Object.entries(rawDimensions).filter(([, value]) => typeof value === 'string'),
  ) as Partial<Record<PersonaDimensionKey, string>>;
  const required: PersonaDimensionKey[] = [
    'base_knowledge',
    'cognitive_style',
    'weak_points',
    'preferred_modality',
    'time_budget',
    'target_direction',
  ];
  return {
    userId,
    dimensions: dimensions as LearningPersona['dimensions'],
    completeness: required.filter((key) => Boolean(dimensions[key])).length / required.length,
    updatedAt: new Date().toISOString(),
  };
}

export function streamPersonaChat(
  userId: string,
  message: string,
  history: Array<Record<string, unknown>>,
  handlers: WorkflowProductHandlers,
): () => void {
  return startCourseTask({
    intent: 'build_persona',
    context: defaultTaskContext(userId),
    payload: { message, history },
  }, handlers);
}

export async function planLearning(courseId: string, userId: string, targetNodeId: string): Promise<LearningPath> {
  const terminal = await runWorkflowToTerminal({
    intent: 'plan_course',
    context: { ...defaultTaskContext(userId), courseId, kpId: targetNodeId },
    payload: { targetNodeId },
  });
  return learningPathFromWorkflowStatus(terminal.status, courseId);
}

export function streamResourceGeneration(
  courseId: string,
  type: ResourceType,
  body: ResourceGenerationBody,
  handlers: WorkflowProductHandlers,
): () => void {
  return startCourseTask({
    intent: 'generate_resource',
    context: { ...defaultTaskContext(body.user_id), courseId, kpId: body.kp_id },
    payload: { resourceType: type, options: body.options },
  }, handlers);
}

export function streamTutorAsk(
  userId: string,
  courseId: string,
  question: string,
  kpId: string,
  handlers: WorkflowProductHandlers,
): () => void {
  return startCourseTask({
    intent: 'ask_tutor',
    context: { ...defaultTaskContext(userId), courseId, kpId },
    payload: { question },
  }, handlers);
}

export async function runAssessment(
  userId: string,
  courseId: string,
  answers: Array<Record<string, unknown>>,
): Promise<AssessmentReport> {
  const terminal = await runWorkflowToTerminal({
    intent: 'run_assessment',
    context: { ...defaultTaskContext(userId), courseId },
    payload: { answers },
  });
  return assessmentReportFromWorkflowStatus(terminal.status);
}

export { workflowRunClient };

function defaultTaskContext(userId: string): CourseTaskContext {
  return {
    userId,
    courseId: '00000000-0000-0000-0000-000000000101',
    kpId: 'e96f770a-57d0-5b49-a7d6-3af1de08e115',
    currentPathNodeIds: [],
  };
}

function reportTerminalProjectionError(error: unknown, handlers: WorkflowProductHandlers): void {
  const clientError = error instanceof WorkflowRunClientError
    ? error
    : new WorkflowRunClientError(
      '任务已经结束，但无法读取持久化结果。请刷新页面后恢复该任务。',
      { code: 'WORKFLOW_TERMINAL_STATUS_UNAVAILABLE' },
    );
  handlers.onError?.({
    code: clientError.code ?? 'WORKFLOW_TERMINAL_STATUS_UNAVAILABLE',
    message: clientError.message,
    recoverable: false,
  });
}

export type CourseApiSnapshot = {
  persona: LearningPersona;
  path: LearningPath;
  resources: ResourceItem[];
};
