import { apiPost, apiStreamPost } from '@/lib/api';
import type { SSEHandlers } from '@/lib/sse';
import { isMockMode } from '@/lib/mock';
import { replayAssessment, replayPersonaChat, replayResourceGeneration, replayTutorAsk } from '@/lib/mock/course.mock';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem, ResourceType } from './types';

export type TaskResponse = {
  task_id: string;
  status: string;
};

export type ResourceGenerationBody = {
  user_id: string;
  kp_id: string;
  options?: Record<string, unknown>;
};

export function streamPersonaChat(
  userId: string,
  message: string,
  history: Array<Record<string, unknown>>,
  handlers: SSEHandlers,
): () => void {
  if (isMockMode()) {
    return replayPersonaChat(message, handlers);
  }
  return apiStreamPost('/api/v1/profile/chat', { user_id: userId, message, history }, handlers);
}

export async function planLearning(courseId: string, userId: string, targetNodeId: string): Promise<LearningPath> {
  return apiPost<LearningPath>(`/api/v1/courses/${courseId}/plan`, {
    user_id: userId,
    target_node_id: targetNodeId,
    options: { depth: 3 },
  });
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
  return apiStreamPost(`/api/v1/courses/${courseId}/resources/generate?type=${type}`, body, handlers);
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
  return apiStreamPost('/api/v1/tutor/ask', {
    user_id: userId,
    course_id: courseId,
    question,
    context: { kp_id: kpId },
  }, handlers);
}

export async function runAssessment(
  userId: string,
  courseId: string,
  answers: Array<Record<string, unknown>>,
): Promise<AssessmentReport> {
  if (isMockMode()) {
    return replayAssessment(answers);
  }
  const response = await apiPost<{
    score: number;
    feedback: string;
    updated_capabilities: AssessmentReport['updatedCapabilities'];
  }>('/api/v1/assessment/run', {
    user_id: userId,
    course_id: courseId,
    answers,
  });
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
