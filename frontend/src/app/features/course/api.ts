import { apiPost, apiStream } from '@/lib/api';
import type { SSEHandlers } from '@/lib/sse';
import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem, ResourceType } from './types';

export type TaskResponse = {
  task_id: string;
  status: string;
};

export async function buildPersona(userId: string, message: string): Promise<TaskResponse> {
  return apiPost<TaskResponse>('/api/v1/profile/chat', { user_id: userId, message });
}

export async function planLearning(courseId: string, userId: string, selectedKpIds: string[]): Promise<TaskResponse> {
  return apiPost<TaskResponse>(`/api/v1/courses/${courseId}/plan`, {
    user_id: userId,
    selected_kp_ids: selectedKpIds,
  });
}

export async function generateResource(
  courseId: string,
  userId: string,
  type: ResourceType,
  kpId?: string,
): Promise<TaskResponse & { resource_type: ResourceType }> {
  return apiPost<TaskResponse & { resource_type: ResourceType }>(
    `/api/v1/courses/${courseId}/resources/generate?type=${type}`,
    { user_id: userId, kp_id: kpId },
  );
}

export async function runAssessment(userId: string, answers: Array<Record<string, unknown>>): Promise<AssessmentReport> {
  // TODO: replace placeholder once P1 assessment endpoint is enabled.
  return Promise.resolve({
    score: 0,
    scoreVector: {},
    feedback: [`TODO: submit ${answers.length} answers for ${userId}`],
    updatedProfile: {},
  });
}

export function streamCourseTask(taskId: string, handlers: SSEHandlers): () => void {
  return apiStream(`/api/v1/tasks/${taskId}/stream`, handlers);
}

export type CourseApiSnapshot = {
  persona: LearningPersona;
  path: LearningPath;
  resources: ResourceItem[];
};
