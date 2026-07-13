// Status: real
//
// Product helpers intentionally create and observe a durable workflow root.
// This module never silently falls back to fixture data. A caller that needs a
// PresenterMode root must explicitly pass `{ mode: 'fixture' }` to
// `startCourseTask`; real workflow errors stay real.

import type { AssessmentRunResponse } from '@/lib/api-types';
import { apiGet, apiPost } from '@/lib/api';
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
  ask_tutor: 'tutor_routing_v3',
  run_assessment: 'assessment_update_v2',
} as const;

export type CourseTaskRunMode = 'real' | 'fixture';

export type PersonaDialogue = {
  content: string;
  nextQuestion?: string;
};

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

export type CourseGraphApiNode = {
  id: string;
  name: string;
  resource_count: number;
  evidence_count: number;
};

export type CourseGraphApiResponse = {
  course_id: string;
  nodes: CourseGraphApiNode[];
  edges: Array<{ source_id: string; target_id: string; edge_type: 'prerequisite'; weight: number }>;
};

export type CoursePathApiResponse = {
  course_id: string;
  strategy: 'foundation_first' | 'accelerated_prerequisite_route';
  explanation: string;
  nodes: Array<{
    knowledge_point_id: string;
    title: string;
    status: 'locked' | 'ready' | 'in_progress' | 'done';
    prerequisites: string[];
    rationale: string;
  }>;
};

export type CourseProgressApiResponse = {
  course_id: string;
  progress_percent: number;
  completed_knowledge_point_ids: string[];
  current_knowledge_point_id?: string | null;
  next_knowledge_point_id?: string | null;
  next_recommendation?: string | null;
};

export type CourseProgressActivity = {
  knowledge_point_id: string;
  activity_type: 'resource' | 'assessment';
  activity_id: string;
  workflow_run_id?: string;
};

export function fetchCourseGraph(courseId: string): Promise<CourseGraphApiResponse> {
  return apiGet<CourseGraphApiResponse>(`/api/v1/courses/${encodeURIComponent(courseId)}/graph`);
}

export function fetchCoursePath(courseId: string): Promise<CoursePathApiResponse> {
  return apiGet<CoursePathApiResponse>(`/api/v1/courses/${encodeURIComponent(courseId)}/path`);
}

export function fetchCourseProgress(courseId: string): Promise<CourseProgressApiResponse> {
  return apiGet<CourseProgressApiResponse>(`/api/v1/courses/${encodeURIComponent(courseId)}/progress`);
}

/** Records only a completed durable resource/assessment root; no local progress is fabricated. */
export function recordCourseProgress(
  courseId: string,
  activity: CourseProgressActivity,
): Promise<CourseProgressApiResponse> {
  return apiPost<CourseProgressApiResponse, CourseProgressActivity>(
    `/api/v1/courses/${encodeURIComponent(courseId)}/progress`,
    activity,
  ).then((progress) => {
    window.dispatchEvent(new CustomEvent('securehub:course-progress', { detail: { courseId } }));
    return progress;
  });
}

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
        input: {
          answers: command.payload.answers,
          quiz_artifact_id: command.payload.quizArtifactId,
          context: { kp_id: kpId, current_path_node_ids: context.currentPathNodeIds },
        },
      };
    default:
      throw new UnsupportedCourseTaskIntentError((command as { intent?: unknown }).intent);
  }
}

type WorkflowPathNode = {
  id: string;
  label: string;
  description?: string;
  status: LearningPath['nodes'][number]['status'];
  prerequisites: string[];
};

function adaptPlanResponse(response: unknown, fallbackCourseId: string): LearningPath {
  if (!isRecord(response)) {
    throw new WorkflowRunClientError('学习路径工作流输出不是对象', { code: 'WORKFLOW_OUTPUT_INVALID' });
  }
  const rawPath = response.path ?? response.nodes;
  if (!Array.isArray(rawPath)) {
    throw new WorkflowRunClientError('学习路径工作流输出缺少 path 数组', { code: 'WORKFLOW_OUTPUT_INVALID' });
  }

  const normalized = rawPath.map((rawNode, index): WorkflowPathNode => {
    if (!isRecord(rawNode)) {
      throw new WorkflowRunClientError(`学习路径节点 ${index + 1} 不是对象`, { code: 'WORKFLOW_OUTPUT_INVALID' });
    }
    const id = firstNonEmptyString(rawNode.node_id, rawNode.id, rawNode.kp_id);
    const label = firstNonEmptyString(rawNode.title, rawNode.label);
    if (!id || !label) {
      throw new WorkflowRunClientError(`学习路径节点 ${index + 1} 缺少 ID 或标题`, { code: 'WORKFLOW_OUTPUT_INVALID' });
    }
    return {
      id,
      label,
      description: firstNonEmptyString(rawNode.description),
      status: normalizePathNodeStatus(rawNode.status),
      prerequisites: Array.isArray(rawNode.prerequisites)
        ? rawNode.prerequisites.filter((value): value is string => typeof value === 'string' && value.length > 0)
        : [],
    };
  });
  const nodes = normalized.map(({ id, label, description, status }, index) => ({
    id,
    label,
    description,
    status,
    priority: index + 1,
  }));
  const edges = normalized.flatMap((node) =>
    node.prerequisites.map((source) => ({
      id: `${source}-${node.id}`,
      source,
      target: node.id,
    })),
  );
  return {
    courseId: firstNonEmptyString(response.course_id) ?? fallbackCourseId,
    nodes,
    edges,
    milestones: nodes.map((node, index) => ({
      id: `milestone-${node.id}`,
      title: node.label,
      week: index + 1,
    })),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function firstNonEmptyString(...values: unknown[]): string | undefined {
  return values.find((value): value is string => typeof value === 'string' && value.trim().length > 0)?.trim();
}

function normalizePathNodeStatus(value: unknown): LearningPath['nodes'][number]['status'] {
  if (value === 'in_progress' || value === 'active') return 'active';
  if (value === 'locked' || value === 'ready' || value === 'done') return value;
  return 'ready';
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
  return {
    ...adaptPlanResponse(finalOutputFromStatus<Record<string, unknown>>(status), fallbackCourseId),
    workflowRunId: status.run_id,
  };
}

export function assessmentReportFromWorkflowStatus(
  status: WorkflowRunStatusResponse,
): AssessmentReport {
  const output = finalOutputFromStatus<Record<string, unknown>>(status);
  const nested = isRecord(output.assessment) ? output.assessment : output;
  const rawScore = nested.score ?? nested.overall_score ?? output.score ?? output.overall_score;
  const score = typeof rawScore === 'number' ? rawScore : Number(rawScore);
  const feedback = firstNonEmptyString(nested.feedback, nested.next_recommendation, nested.content, output.feedback, output.next_recommendation, output.content);
  if (!Number.isFinite(score) || score < 0 || score > 1 || !feedback) {
    throw new WorkflowRunClientError('评估工作流没有返回有效的分数和反馈，请重新生成测验后重试。', {
      code: 'WORKFLOW_OUTPUT_INVALID',
    });
  }
  const updatedCapabilities = Array.isArray(nested.updated_capabilities)
    ? nested.updated_capabilities
    : Array.isArray(output.updated_capabilities) ? output.updated_capabilities : [];
  return {
    score,
    scoreVector: Object.fromEntries(updatedCapabilities.flatMap((item) => {
      if (!isRecord(item) || typeof item.dimension !== 'string' || typeof item.score !== 'number') return [];
      return [[item.dimension, item.score] as const];
    })),
    feedback: [feedback],
    updatedProfile: {},
    updatedCapabilities: updatedCapabilities.filter(isCapabilityDto),
  };
}

function isCapabilityDto(value: unknown): value is AssessmentRunResponse['updated_capabilities'][number] {
  return isRecord(value)
    && typeof value.dimension === 'string'
    && typeof value.score === 'number'
    && typeof value.confidence === 'number'
    && typeof value.evidence_count === 'number';
}

/** Extracts only the learner-facing answer from the durable tutor terminal output. */
export function tutorAnswerFromWorkflowStatus(status: WorkflowRunStatusResponse): string {
  const output = finalOutputFromStatus<Record<string, unknown>>(status);
  const content = firstNonEmptyString(output.content, isRecord(output.answer) ? output.answer.content : undefined);
  if (!content) {
    throw new WorkflowRunClientError('辅导工作流没有返回可展示的回答，请重试该问题。', {
      code: 'WORKFLOW_OUTPUT_INVALID',
    });
  }
  return content;
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

/** Returns only learner-facing structured fields; evidence and quality internals stay out of chat bubbles. */
export function personaDialogueFromWorkflowStatus(
  status: WorkflowRunStatusResponse,
): PersonaDialogue | undefined {
  return personaDialogueFromOutput(finalOutputFromStatus<Record<string, unknown>>(status));
}

export function personaDialogueFromOutput(output: unknown): PersonaDialogue | undefined {
  if (!isRecord(output)) return undefined;
  const content = firstNonEmptyString(output.content);
  const nextQuestion = firstNonEmptyString(output.next_question, output.nextQuestion);
  if (!content && !nextQuestion) return undefined;
  return { content: content ?? nextQuestion ?? '', nextQuestion };
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
    // Match the durable WEBSEC-101 root used by the catalog-backed course UI.
    courseId: '5f63a7c3-1c76-513c-88a5-f335d6190816',
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
