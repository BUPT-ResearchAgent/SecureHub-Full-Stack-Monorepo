import { apiPost, apiStreamPost } from '@/lib/api';
import type { SSEHandlers } from '@/lib/sse';
import { isMockMode, withMockFallback } from '@/lib/mock';
import { replayAssessment, replayPersonaChat, replayResourceGeneration, replayTutorAsk } from '@/lib/mock/course.mock';
import { mockLearningPath } from './mockData';
import type { AssessmentRunResponse, CoursePlanResponse } from '@/lib/api-types';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem, ResourceType } from './types';

const demoTargetNodeId = '00000000-0000-0000-0000-000000000201';

export type TaskResponse = {
  task_id: string;
  status: string;
};

export type ResourceGenerationBody = {
  user_id: string;
  kp_id: string;
  options?: Record<string, unknown>;
};

function streamWithMockFallback(real: (fallback: (error: unknown) => void) => () => void, mock: () => () => void): () => void {
  if (isMockMode()) return mock();
  let stopped = false;
  let cancel: (() => void) | undefined;
  const fallback = (error: unknown) => {
    if (stopped) return;
    console.warn('真实 SSE 网络连接失败，已降级为演示回放。', error);
    cancel?.();
    cancel = mock();
  };
  try {
    cancel = real(fallback);
  } catch (error) {
    fallback(error);
  }
  return () => {
    stopped = true;
    cancel?.();
  };
}

function withNetworkFallbackHandlers(handlers: SSEHandlers, fallback: (error: unknown) => void): SSEHandlers {
  return {
    ...handlers,
    onError(error) {
      if (error.code === 'sse_error' || error.code === 'NetworkError') {
        fallback(error);
        return;
      }
      handlers.onError?.(error);
    },
  };
}

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

export function streamPersonaChat(
  userId: string,
  message: string,
  history: Array<Record<string, unknown>>,
  handlers: SSEHandlers,
): () => void {
  if (isMockMode()) {
    return replayPersonaChat(message, handlers);
  }
  return streamWithMockFallback(
    (fallback) => apiStreamPost('/api/v1/profile/chat', { user_id: userId, message, history }, withNetworkFallbackHandlers(handlers, fallback)),
    () => replayPersonaChat(message, handlers),
  );
}

export async function planLearning(courseId: string, userId: string, targetNodeId: string): Promise<LearningPath> {
  return withMockFallback(
    async () => {
      const response = await apiPost<CoursePlanResponse>(`/api/v1/courses/${courseId}/plan`, {
        user_id: userId,
        target_node_id: contractUuid(targetNodeId, demoTargetNodeId),
        options: { depth: 3, local_target_node_id: targetNodeId },
      });
      return adaptPlanResponse(response, courseId);
    },
    () => ({ ...mockLearningPath, courseId }),
  );
}

export function streamResourceGeneration(
  courseId: string,
  type: ResourceType,
  body: ResourceGenerationBody,
  handlers: SSEHandlers,
): () => void {
  if (isMockMode()) {
    return replayResourceGeneration(type, handlers);
  }
  return streamWithMockFallback(
    (fallback) => apiStreamPost(`/api/v1/courses/${courseId}/resources/generate?type=${type}`, {
      ...body,
      type,
      kp_id: contractUuid(body.kp_id, demoTargetNodeId),
      options: { ...body.options, local_kp_id: body.kp_id },
    }, withNetworkFallbackHandlers(handlers, fallback)),
    () => replayResourceGeneration(type, handlers),
  );
}

export function streamTutorAsk(
  userId: string,
  courseId: string,
  question: string,
  kpId: string,
  handlers: SSEHandlers,
): () => void {
  if (isMockMode()) {
    return replayTutorAsk(question, handlers);
  }
  return streamWithMockFallback(
    (fallback) => apiStreamPost('/api/v1/tutor/ask', {
      user_id: userId,
      course_id: courseId,
      question,
      context: { kp_id: kpId },
    }, withNetworkFallbackHandlers(handlers, fallback)),
    () => replayTutorAsk(question, handlers),
  );
}

export async function runAssessment(
  userId: string,
  courseId: string,
  answers: Array<Record<string, unknown>>,
): Promise<AssessmentReport> {
  const response = await withMockFallback(
    () => apiPost<AssessmentRunResponse>('/api/v1/assessment/run', {
      user_id: userId,
      course_id: courseId,
      answers,
    }),
    async () => {
      const mock = await replayAssessment(answers);
      return {
        score: mock.score,
        feedback: mock.feedback.join('\n'),
        updated_capabilities: mock.updatedCapabilities,
      };
    },
  );
  return {
    score: response.score,
    scoreVector: Object.fromEntries((response.updated_capabilities ?? []).map((item) => [item.dimension, item.score])),
    feedback: [response.feedback],
    updatedProfile: {},
    updatedCapabilities: response.updated_capabilities,
  };
}

export type CourseApiSnapshot = {
  persona: LearningPersona;
  path: LearningPath;
  resources: ResourceItem[];
};
