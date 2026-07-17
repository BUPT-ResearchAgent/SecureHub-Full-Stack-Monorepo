import { apiGet, apiPost } from '@/lib/api';

export type ReplanDecision = 'accept' | 'defer' | 'revert';
export type RecommendationDecision = 'accept' | 'defer' | 'reject' | 'complete';
export type ResourceFeedbackKind =
  | 'too_difficult'
  | 'too_shallow'
  | 'missing_example'
  | 'want_diagram'
  | 'want_practice';

export type StudentLearningLoopCandidate = {
  id: string;
  status: 'pending' | 'deferred' | 'accepted' | 'reverted' | 'expired';
  source_version_no: number;
  accepted_version_no?: number | null;
  trigger_label: string;
  trigger_at?: string | null;
  reason_code: string;
  reason_text: string;
  affected_knowledge_point?: string | null;
  expected_minutes: number;
  changed_tasks: Array<{
    action: 'added' | 'retained';
    title: string;
    knowledge_point?: string | null;
    status: 'todo' | 'active' | 'done' | 'blocked';
    expected_minutes: number;
  }>;
  source_boundary: string;
  created_at: string;
  updated_at: string;
};

export type StudentLearningPathVersion = {
  id: string;
  version_no: number;
  kind: 'baseline' | 'replan' | 'revert';
  state: 'active' | 'historical';
  title: string;
  summary: string;
  diff: Record<string, unknown>;
  created_at: string;
};

export type StudentResourceRecommendation = {
  id: string;
  resource_id: string;
  title: string;
  resource_type: string;
  knowledge_point?: string | null;
  status: 'scheduled' | 'accepted' | 'deferred' | 'rejected' | 'superseded' | 'feedback_received' | 'completed';
  scheduled_at: string;
  rationale: string;
  source_boundary: string;
  created_at: string;
};

export type StudentResourceFeedback = {
  id: string;
  resource_id: string;
  status: 'submitted' | 'retry_requested' | 'regenerated' | 'provider_unavailable' | 'failed' | 'rejected';
  feedback_kinds: ResourceFeedbackKind[];
  comment?: string | null;
  retry_workflow_run_id?: string | null;
  resulting_resource_id?: string | null;
  outcome: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type StudentResourceLineage = {
  lineage_root_id: string;
  logical_key: string;
  resource_type: string;
  title: string;
  knowledge_point?: string | null;
  current_resource_id: string;
  versions: Array<{
    resource_id: string;
    version: number;
    parent_resource_id?: string | null;
    title: string;
    status: string;
    quality_score?: number | null;
    quality_delta?: number | null;
    changed_fields: string[];
    change_summary?: string | null;
    evidence_count: number;
    run_state: string;
    source_kind: 'curated-demo' | 'external-preview' | 'real';
    source_boundary: string;
    created_at: string;
  }>;
};

export type StudentLearningLoop = {
  course_id: string;
  candidates: StudentLearningLoopCandidate[];
  path_versions: StudentLearningPathVersion[];
  recommendations: StudentResourceRecommendation[];
  feedback: StudentResourceFeedback[];
  resource_lineages: StudentResourceLineage[];
};

export type ResourceFeedbackSubmitResponse = {
  feedback: StudentResourceFeedback;
  workflow?: Record<string, unknown> | null;
};

function base(courseId: string): string {
  return `/api/v1/courses/${encodeURIComponent(courseId)}/learning-loop`;
}

/** Current-user-only read model; it does not accept student, class, or evidence IDs. */
export function fetchStudentLearningLoop(courseId: string): Promise<StudentLearningLoop> {
  return apiGet<StudentLearningLoop>(base(courseId));
}

export function createStudentReplanCandidate(courseId: string): Promise<StudentLearningLoopCandidate> {
  return apiPost<StudentLearningLoopCandidate, Record<string, never>>(
    `${base(courseId)}/replan-candidates`,
    {},
  );
}

export function decideStudentReplanCandidate(
  courseId: string,
  candidateId: string,
  decision: ReplanDecision,
): Promise<StudentLearningLoopCandidate> {
  return apiPost<StudentLearningLoopCandidate, { decision: ReplanDecision }>(
    `${base(courseId)}/replan-candidates/${encodeURIComponent(candidateId)}/decision`,
    { decision },
  );
}

export function decideStudentRecommendation(
  courseId: string,
  recommendationId: string,
  decision: RecommendationDecision,
): Promise<StudentResourceRecommendation> {
  return apiPost<StudentResourceRecommendation, { decision: RecommendationDecision }>(
    `${base(courseId)}/recommendations/${encodeURIComponent(recommendationId)}/decision`,
    { decision },
  );
}

export function submitStudentResourceFeedback(
  courseId: string,
  resourceId: string,
  payload: {
    feedback_kinds: ResourceFeedbackKind[];
    comment?: string;
    recommendation_id?: string;
  },
): Promise<ResourceFeedbackSubmitResponse> {
  return apiPost<ResourceFeedbackSubmitResponse, typeof payload>(
    `${base(courseId)}/resources/${encodeURIComponent(resourceId)}/feedback`,
    payload,
  );
}
