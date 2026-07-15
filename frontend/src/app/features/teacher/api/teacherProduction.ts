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
  current_resource_id?: string | null;
  version_no: number;
  state: 'uploading' | 'processing' | 'ready' | 'correction_pending' | 'corrected' | 'withdrawn' | 'deleted';
  correction_of_id?: string | null;
  reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type TeacherWeaknessSnapshot = {
  id: string;
  course_id: string;
  teaching_class_id?: string | null;
  group_id?: string | null;
  sample_size: number;
  score_version: string;
  input_fingerprint: string;
  weak_knowledge_points: Array<{
    knowledge_node_id: string;
    knowledge_node_name: string;
    sample_size: number;
    average_score: number;
    incorrect_rate: number;
  }>;
  computed_at: string;
};

export type TeachingRecommendation = {
  id: string;
  course_id: string;
  source_snapshot_id: string;
  evidence_snapshot_id: string;
  agent_run_id?: string | null;
  version_no: number;
  diff: Record<string, unknown>;
  status: 'pending' | 'adopted' | 'rejected' | 'superseded' | 'withdrawn';
  created_at: string;
};

export type TeacherAssessment = {
  id: string;
  course_id: string;
  kind: 'assignment' | 'exam';
  logical_key: string;
  status: 'draft' | 'published' | 'closed' | 'withdrawn';
  created_at: string;
  updated_at: string;
};

export type TeacherAssessmentVersion = {
  id: string;
  assessment_id: string;
  version_no: number;
  title: string;
  instructions?: string | null;
  state: 'draft' | 'published' | 'withdrawn';
  frozen_at?: string | null;
  items: Array<{
    id: string;
    quiz_item_id: string;
    position: number;
    points: number;
    grading_mode: 'objective' | 'subjective';
    question_snapshot: Record<string, unknown>;
  }>;
  created_at: string;
};

export type TeacherAssignment = {
  id: string;
  course_id: string;
  assessment_id: string;
  assessment_version_id: string;
  logical_key: string;
  kind: 'assignment' | 'exam';
  title: string;
  version_no: number;
  target_type: 'class' | 'group' | 'student';
  teaching_class_id?: string | null;
  group_id?: string | null;
  student_id?: string | null;
  due_at: string;
  allow_late: boolean;
  status: 'active' | 'closed' | 'withdrawn';
  created_at: string;
};

export type TeacherAssignmentCreated = {
  id: string;
  assessment_version_id: string;
  target_type: 'class' | 'group' | 'student';
  teaching_class_id?: string | null;
  group_id?: string | null;
  student_id?: string | null;
  due_at: string;
  allow_late: boolean;
  status: 'active' | 'closed' | 'withdrawn';
  created_at: string;
};

export type TeacherGradeDecision = {
  id: string;
  submission_id: string;
  objective_score?: number | null;
  ai_suggested_score?: number | null;
  ai_agent_run_id?: string | null;
  ai_evidence_snapshot_id?: string | null;
  ai_suggestion_status: 'not_requested' | 'suggested' | 'rejected';
  final_score?: number | null;
  status: 'pending' | 'auto_scored' | 'teacher_reviewed' | 'published' | 'withdrawn';
  override_reason?: string | null;
  published_at?: string | null;
  withdrawn_at?: string | null;
};

export type TeacherAssessmentSubmission = {
  id: string;
  assignment_id: string;
  student_id: string;
  student_display_name: string;
  status: 'open' | 'submitted' | 'late' | 'locked';
  submitted_at?: string | null;
  grade?: TeacherGradeDecision | null;
};

export type TypedSyllabusContent = {
  title: string;
  summary: string;
  learning_outcomes: string[];
  modules: Array<{
    module_id: string;
    title: string;
    knowledge_node_ids: string[];
    learning_outcome: string;
    activities: string[];
  }>;
  assessment_plan: string;
  source_note: string;
};

export type TeacherSyllabusVersion = {
  id: string;
  syllabus_id: string;
  version_no: number;
  typed_content: TypedSyllabusContent;
  content_schema_version: 'syllabus-v1';
  state: 'draft' | 'generation_pending' | 'review_pending' | 'published' | 'superseded' | 'withdrawn';
  generated_from_agent_run_id?: string | null;
  evidence_snapshot_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type TeacherSyllabusDiff = {
  from_version_id?: string | null;
  to_version_id: string;
  changed_fields: string[];
  added_module_ids: string[];
  removed_module_ids: string[];
};

export type TeacherSyllabusExport = {
  id: string;
  version_id: string;
  format: 'json' | 'markdown';
  generated_resource_id?: string | null;
  status: 'ready' | 'withdrawn' | 'failed';
  content: string | Record<string, unknown>;
  created_at: string;
};

export function fetchTeacherProductionDashboard(): Promise<TeacherProductionDashboard> {
  return apiGet<TeacherProductionDashboard>(`${productionPath}/dashboard`);
}

export function fetchTeacherProductionCourses(): Promise<TeacherProductionCourseList> {
  return apiGet<TeacherProductionCourseList>(`${productionPath}/courses`);
}

export function fetchTeacherCourseAssets(courseId: string, includeDeleted = false): Promise<{ items: TeacherGovernedAsset[] }> {
  const suffix = includeDeleted ? '?include_deleted=true' : '';
  return apiGet<{ items: TeacherGovernedAsset[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/assets${suffix}`,
  );
}

export function bindTeacherCourseAsset(
  courseId: string,
  payload: { document_id: string; document_asset_id?: string; purpose: string; reason?: string },
): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/courses/${encodeURIComponent(courseId)}/assets`, payload);
}

export function correctTeacherCourseAsset(
  assetId: string,
  payload: { replacement_document_id: string; replacement_document_asset_id?: string; reason: string },
): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/assets/${encodeURIComponent(assetId)}/correct`, payload);
}

export function withdrawTeacherCourseAsset(assetId: string, reason: string): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/assets/${encodeURIComponent(assetId)}/withdraw`, { reason });
}

export function deleteTeacherCourseAsset(assetId: string, reason: string): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/assets/${encodeURIComponent(assetId)}/delete`, { reason });
}

export function restoreTeacherCourseAsset(assetId: string, reason: string): Promise<TeacherGovernedAsset> {
  return apiPost<TeacherGovernedAsset>(`${productionPath}/assets/${encodeURIComponent(assetId)}/restore`, { reason });
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

export function fetchTeacherWeaknessSnapshots(courseId: string): Promise<{ items: TeacherWeaknessSnapshot[] }> {
  return apiGet<{ items: TeacherWeaknessSnapshot[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/weakness-snapshots`,
  );
}

export function createTeacherWeaknessSnapshot(
  courseId: string,
  payload: { teaching_class_id?: string; group_id?: string; minimum_sample: number },
): Promise<TeacherWeaknessSnapshot> {
  return apiPost<TeacherWeaknessSnapshot>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/weakness-snapshots`,
    payload,
  );
}

export function fetchTeachingRecommendations(courseId: string): Promise<{ items: TeachingRecommendation[] }> {
  return apiGet<{ items: TeachingRecommendation[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/teaching-recommendations`,
  );
}

export function createTeachingRecommendation(
  courseId: string,
  payload: {
    source_snapshot_id: string;
    evidence_snapshot_id: string;
    agent_run_id?: string;
    title: string;
    actions: string[];
    rationale: string;
  },
): Promise<TeachingRecommendation> {
  return apiPost<TeachingRecommendation>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/teaching-recommendations`,
    payload,
  );
}

export function decideTeachingRecommendation(
  recommendationId: string,
  payload: { decision: 'adopt' | 'reject' | 'withdraw'; reason: string },
): Promise<TeachingRecommendation> {
  return apiPost<TeachingRecommendation>(
    `${productionPath}/teaching-recommendations/${encodeURIComponent(recommendationId)}/decision`,
    payload,
  );
}

export function fetchTeacherCourseAssignments(courseId: string): Promise<{ items: TeacherAssignment[] }> {
  return apiGet<{ items: TeacherAssignment[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/assignments`,
  );
}

export function createTeacherAssessment(
  courseId: string,
  payload: { kind: 'assignment' | 'exam'; logical_key: string },
): Promise<TeacherAssessment> {
  return apiPost<TeacherAssessment>(`${productionPath}/courses/${encodeURIComponent(courseId)}/assessments`, payload);
}

export function createTeacherAssessmentVersion(
  assessmentId: string,
  payload: {
    title: string;
    instructions?: string;
    items: Array<{ quiz_item_id: string; position: number; points: number; grading_mode: 'objective' | 'subjective' }>;
  },
): Promise<TeacherAssessmentVersion> {
  return apiPost<TeacherAssessmentVersion>(`${productionPath}/assessments/${encodeURIComponent(assessmentId)}/versions`, payload);
}

export function assignTeacherAssessmentVersion(
  versionId: string,
  payload: {
    target_type: 'class' | 'group' | 'student';
    teaching_class_id?: string;
    group_id?: string;
    student_id?: string;
    due_at: string;
    allow_late: boolean;
    reason?: string;
  },
): Promise<TeacherAssignmentCreated> {
  return apiPost<TeacherAssignmentCreated>(`${productionPath}/assessment-versions/${encodeURIComponent(versionId)}/assignments`, payload);
}

export function fetchTeacherAssignmentSubmissions(assignmentId: string): Promise<{ items: TeacherAssessmentSubmission[] }> {
  return apiGet<{ items: TeacherAssessmentSubmission[] }>(
    `${productionPath}/assessment-assignments/${encodeURIComponent(assignmentId)}/submissions`,
  );
}

export function scoreTeacherSubmissionObjective(submissionId: string): Promise<{ objective_score: number; total_objective_points: number }> {
  return apiPost<{ objective_score: number; total_objective_points: number }>(
    `${productionPath}/assessment-submissions/${encodeURIComponent(submissionId)}/score-objective`,
    {},
  );
}

export function recordTeacherSubjectiveSuggestion(
  submissionId: string,
  payload: { agent_run_id: string; evidence_snapshot_id: string },
): Promise<TeacherGradeDecision> {
  return apiPost<TeacherGradeDecision>(
    `${productionPath}/assessment-submissions/${encodeURIComponent(submissionId)}/subjective-suggestion`,
    payload,
  );
}

export function overrideTeacherSubmissionGrade(
  submissionId: string,
  payload: { final_score: number; reason: string },
): Promise<TeacherGradeDecision> {
  return apiPost<TeacherGradeDecision>(
    `${productionPath}/assessment-submissions/${encodeURIComponent(submissionId)}/override`,
    payload,
  );
}

export function publishTeacherSubmissionGrade(submissionId: string): Promise<TeacherGradeDecision> {
  return apiPost<TeacherGradeDecision>(`${productionPath}/assessment-submissions/${encodeURIComponent(submissionId)}/publish`, {});
}

export function withdrawTeacherSubmissionGrade(submissionId: string, reason: string): Promise<TeacherGradeDecision> {
  return apiPost<TeacherGradeDecision>(`${productionPath}/assessment-submissions/${encodeURIComponent(submissionId)}/withdraw`, { reason });
}

export function fetchTeacherSyllabusVersions(courseId: string): Promise<{ items: TeacherSyllabusVersion[] }> {
  return apiGet<{ items: TeacherSyllabusVersion[] }>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/syllabus/versions`,
  );
}

export function createTeacherSyllabusVersion(
  courseId: string,
  payload: { typed_content: TypedSyllabusContent; reason: string },
): Promise<TeacherSyllabusVersion> {
  return apiPost<TeacherSyllabusVersion>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/syllabus/versions`,
    payload,
  );
}

export function generateTeacherSyllabusVersion(
  courseId: string,
  payload: { agent_run_id: string; evidence_snapshot_id: string; reason: string },
): Promise<TeacherSyllabusVersion> {
  return apiPost<TeacherSyllabusVersion>(
    `${productionPath}/courses/${encodeURIComponent(courseId)}/syllabus/generate`,
    payload,
  );
}

export function reviewTeacherSyllabusVersion(
  versionId: string,
  payload: { decision: 'approve' | 'reject' | 'withdraw'; reason: string },
): Promise<TeacherSyllabusVersion> {
  return apiPost<TeacherSyllabusVersion>(
    `${productionPath}/syllabus/versions/${encodeURIComponent(versionId)}/review`,
    payload,
  );
}

export function compareTeacherSyllabusVersions(versionId: string, fromVersionId?: string): Promise<TeacherSyllabusDiff> {
  const suffix = fromVersionId ? `?from_version_id=${encodeURIComponent(fromVersionId)}` : '';
  return apiGet<TeacherSyllabusDiff>(`${productionPath}/syllabus/versions/${encodeURIComponent(versionId)}/diff${suffix}`);
}

export function previewTeacherSyllabusVersion(versionId: string): Promise<TeacherSyllabusVersion> {
  return apiGet<TeacherSyllabusVersion>(`${productionPath}/syllabus/versions/${encodeURIComponent(versionId)}/preview`);
}

export function exportTeacherSyllabusVersion(
  versionId: string,
  format: 'json' | 'markdown',
): Promise<TeacherSyllabusExport> {
  return apiPost<TeacherSyllabusExport>(`${productionPath}/syllabus/versions/${encodeURIComponent(versionId)}/export`, { format });
}

export function rollbackTeacherSyllabusVersion(versionId: string, reason: string): Promise<TeacherSyllabusVersion> {
  return apiPost<TeacherSyllabusVersion>(`${productionPath}/syllabus/versions/${encodeURIComponent(versionId)}/rollback`, { reason });
}
