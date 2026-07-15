// Status: real

import { apiGet, apiPost } from '@/lib/api';

export type CourseUpdateImpact = {
  id: string;
  knowledge_node_id: string;
  impact_type: 'add' | 'revise' | 'retire' | 'emphasize';
  rationale: string;
};

export type CourseUpdateSuggestion = {
  id: string;
  course_id: string;
  signal_id: string;
  version_no: number;
  title: string;
  diff: Record<string, unknown>;
  status: 'draft' | 'pending_teacher_decision' | 'adopted' | 'rejected' | 'superseded' | 'withdrawn';
  impacts: CourseUpdateImpact[];
  decision?: { decision: 'adopt' | 'reject'; reason: string; decided_at: string } | null;
  created_at: string;
};

export function fetchCourseUpdateSuggestions(courseId: string): Promise<CourseUpdateSuggestion[]> {
  return apiGet<CourseUpdateSuggestion[]>(
    `/api/v1/course-updates/courses/${encodeURIComponent(courseId)}/suggestions`,
  );
}

export function decideCourseUpdateSuggestion(
  suggestionId: string,
  decision: 'adopt' | 'reject',
  reason: string,
): Promise<CourseUpdateSuggestion> {
  return apiPost<CourseUpdateSuggestion>(
    `/api/v1/course-updates/suggestions/${encodeURIComponent(suggestionId)}/decision`,
    { decision, reason },
  );
}
