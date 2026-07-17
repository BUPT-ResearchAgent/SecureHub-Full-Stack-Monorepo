import { apiGet, apiPost } from '@/lib/api';

export type StudentCourseExperienceEvidence = {
  label: string;
  excerpt: string;
  source_kind: 'curated-demo' | 'external-preview' | 'real';
  source_url?: string | null;
};

export type StudentCourseExperienceTask = {
  title: string;
  knowledge_point?: string | null;
  status: 'todo' | 'active' | 'done' | 'blocked';
  order_index: number;
};

export type StudentCourseExperienceResource = {
  /** Opaque identifiers used only for current-student feedback API calls. */
  resource_id: string;
  lineage_root_id: string;
  logical_key: string;
  resource_type: 'doc' | 'ppt' | 'mindmap' | 'quiz' | 'lab' | 'readings' | 'video';
  title: string;
  knowledge_point?: string | null;
  version: number;
  available_versions: number[];
  quality_state: string;
  source_kind: 'curated-demo' | 'external-preview' | 'real';
  source_boundary: string;
  content: Record<string, unknown>;
  evidence: StudentCourseExperienceEvidence[];
  updated_at?: string | null;
};

export type StudentCourseExperienceAssignment = {
  id: string;
  logical_key: string;
  title: string;
  due_at: string;
  allow_late: boolean;
  question_count: number;
  assignment_status: 'active' | 'closed' | 'withdrawn';
  learner_status: 'not_started' | 'submitted' | 'late' | 'grading' | 'teacher_review' | 'published' | 'withdrawn';
  published_score?: number | null;
  next_action: string;
};

export type StudentCourseExperienceTutorExchange = {
  question: string;
  concept: string;
  defensive_example: string;
  next_step: string;
  evidence_status: 'available' | 'insufficient';
  source_kind: 'curated-demo' | 'real';
  source_boundary: string;
  evidence: StudentCourseExperienceEvidence[];
  recorded_at: string;
  /** True only for a persisted, current-student controlled demo record. */
  quick_reply_available: boolean;
};

export type StudentCourseDemoAssessmentDraft = {
  assignment_id: string;
  assignment_title: string;
  /** Opaque current-student quiz artifact ID for the real assessment workflow. */
  quiz_resource_id: string;
  answers: Record<string, string | string[]>;
  source_kind: 'curated-demo';
  source_boundary: string;
};

export type StudentCourseExperience = {
  course_id: string;
  course_code: 'WEBSEC-101';
  data_status: 'ready' | 'incomplete';
  missing_dependencies: string[];
  profile: {
    display_name: string;
    teaching_class_name: string;
    group_name?: string | null;
    learning_story: string;
    learning_story_summary: string;
    source_boundary: string;
  };
  progress_percent: number;
  next_step: string;
  tasks: StudentCourseExperienceTask[];
  capabilities: Array<{
    dimension: string;
    score: number;
    confidence: number;
    evidence_count: number;
  }>;
  resources: StudentCourseExperienceResource[];
  assignments: StudentCourseExperienceAssignment[];
  updates: Array<{
    subject: string;
    body: string;
    delivered_at: string;
    read: boolean;
  }>;
  tutor_exchanges: StudentCourseExperienceTutorExchange[];
  assessment_demo_draft?: StudentCourseDemoAssessmentDraft | null;
  assessment: {
    baseline_average?: number | null;
    recent_average?: number | null;
    trend: 'improving' | 'stable' | 'needs_attention' | 'insufficient';
    scored_attempt_count: number;
    metrics: Array<{
      knowledge_point: string;
      baseline_average?: number | null;
      recent_average?: number | null;
      sample_size: number;
      trend: 'improving' | 'stable' | 'needs_attention' | 'insufficient';
    }>;
    feedback_boundary: string;
  };
};

export type StudentAssessmentRead = {
  assignment_id: string;
  course_id: string;
  title: string;
  instructions?: string | null;
  due_at: string;
  allow_late: boolean;
  status: 'active';
  submission_status: 'open' | 'submitted' | 'late' | 'locked';
  items: Array<{
    quiz_item_id: string;
    position: number;
    points: number;
    grading_mode: 'objective' | 'subjective';
    knowledge_node_name: string;
    question_type: string;
    question: string;
    options: string[];
    content_version: number;
  }>;
};

export type StudentAssessmentSubmission = {
  id: string;
  assignment_id: string;
  student_id: string;
  status: 'open' | 'submitted' | 'late' | 'locked';
  submitted_at?: string | null;
};

/** Reads a current-user-only projection; no user, class, group, or evidence id is accepted. */
export function fetchStudentCourseExperience(courseId: string): Promise<StudentCourseExperience> {
  return apiGet<StudentCourseExperience>(
    `/api/v1/courses/${encodeURIComponent(courseId)}/student-experience`,
  );
}

/** Reads a frozen, assigned assessment without exposing its answer key. */
export function fetchStudentAssessment(assignmentId: string): Promise<StudentAssessmentRead> {
  return apiGet<StudentAssessmentRead>(
    `/api/v1/teaching/assessment-assignments/${encodeURIComponent(assignmentId)}`,
  );
}

/** Submits only answers for the authenticated student's published frozen assignment. */
export function submitStudentAssessment(
  assignmentId: string,
  answers: Record<string, string | string[]>,
): Promise<StudentAssessmentSubmission> {
  return apiPost<StudentAssessmentSubmission, { answers: Record<string, string | string[]> }>(
    `/api/v1/teaching/assessment-assignments/${encodeURIComponent(assignmentId)}/submit`,
    { answers },
  );
}
