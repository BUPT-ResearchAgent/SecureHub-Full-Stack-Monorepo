// Status: real

import { apiGet, apiPost } from '@/lib/api';
import type { QuizQualityRun, TeacherQuizBankResponse } from '../types/quizQuality';

const quizBankPath = '/api/v1/teacher/quiz-bank/websec';

export function fetchWebsecQuizBank(): Promise<TeacherQuizBankResponse> {
  return apiGet<TeacherQuizBankResponse>(quizBankPath);
}

export function validateWebsecQuizBank(): Promise<QuizQualityRun> {
  return apiPost<QuizQualityRun>(`${quizBankPath}/validate`, {});
}
