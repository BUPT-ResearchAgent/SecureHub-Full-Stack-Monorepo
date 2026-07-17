// Status: real

import { apiGet, apiPost } from '@/lib/api';
import type { QuizQualityRun, TeacherQuizBankResponse } from '../types/quizQuality';

const quizBankPath = '/api/v1/teacher/quiz-bank/websec';

export function fetchWebsecQuizBank(): Promise<TeacherQuizBankResponse> {
  return fetchWithOneConnectionRetry();
}

export function validateWebsecQuizBank(): Promise<QuizQualityRun> {
  return apiPost<QuizQualityRun>(`${quizBankPath}/validate`, {});
}

/**
 * A browser can lose a local development-server connection during a backend
 * hot reload.  Retrying only a transport failure is safe for this read-only
 * endpoint.  HTTP responses (including 403 and 5xx) remain visible to the
 * page exactly as returned and are never retried or replaced with demo data.
 */
async function fetchWithOneConnectionRetry(): Promise<TeacherQuizBankResponse> {
  try {
    return await apiGet<TeacherQuizBankResponse>(quizBankPath);
  } catch (cause) {
    if (!(cause instanceof TypeError)) throw cause;
    return apiGet<TeacherQuizBankResponse>(quizBankPath);
  }
}
