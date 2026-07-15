// Status: real

import { apiGet, apiPost } from '@/lib/api';

const productionPath = '/api/v1/teacher/production';

export type TeacherProductionDashboard = {
  course_count: number;
  active_student_count: number;
  governed_asset_count: number;
  pending_quiz_review_count: number;
  active_assignment_count: number;
  pending_grade_count: number;
  definitions: Record<string, string>;
  calculated_at: string;
};

export type TeacherProductionCourse = {
  id: string;
  code: string;
  title: string;
  active_class_count: number;
  enrolled_student_count: number;
};

export type TeacherProductionCourseList = { items: TeacherProductionCourse[] };

export type TeacherGovernedAsset = {
  id: string;
  course_id: string;
  document_id: string;
  document_title: string;
  document_asset_id?: string | null;
  version_no: number;
  state: 'uploading' | 'processing' | 'ready' | 'correction_pending' | 'corrected' | 'withdrawn' | 'deleted';
  correction_of_id?: string | null;
  reason?: string | null;
  created_at: string;
  updated_at: string;
};

export function fetchTeacherProductionDashboard(): Promise<TeacherProductionDashboard> {
  return apiGet<TeacherProductionDashboard>(`${productionPath}/dashboard`);
}

export function fetchTeacherProductionCourses(): Promise<TeacherProductionCourseList> {
  return apiGet<TeacherProductionCourseList>(`${productionPath}/courses`);
}

export function fetchTeacherCourseAssets(courseId: string): Promise<{ items: TeacherGovernedAsset[] }> {
  return apiGet<{ items: TeacherGovernedAsset[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/assets`,
  );
}

export function withdrawTeacherCourseAsset(assetId: string, reason: string): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/assets/${encodeURIComponent(assetId)}/withdraw`, { reason });
}

export function reviewTeacherQuizItem(
  courseId: string,
  quizItemId: string,
  decision: 'publish' | 'reject' | 'withdraw',
  reason: string,
): Promise<{ id: string; quiz_item_id: string; decision: string; after_status: string }> {
  return apiPost<{ id: string; quiz_item_id: string; decision: string; after_status: string }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/quiz-items/${encodeURIComponent(quizItemId)}/review`,
    { decision, reason },
  );
}
