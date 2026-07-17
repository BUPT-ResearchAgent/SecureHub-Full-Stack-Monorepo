# Status: real

"""HTTP DTOs for the teacher-production state machine.

These contracts expose only durable state.  They intentionally carry IDs for
the existing course, knowledge, evidence, and runtime authorities instead of
copying their source payloads into the teaching domain.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class TeacherCourseDTO(BaseModel):
    id: UUID
    code: str
    title: str
    active_class_count: int = Field(ge=0)
    enrolled_student_count: int = Field(ge=0)


class TeacherCourseListDTO(BaseModel):
    items: list[TeacherCourseDTO]


class TeacherDashboardDTO(BaseModel):
    course_count: int = Field(ge=0)
    active_student_count: int = Field(ge=0)
    governed_asset_count: int = Field(ge=0)
    pending_quiz_review_count: int = Field(ge=0)
    active_assignment_count: int = Field(ge=0)
    pending_grade_count: int = Field(ge=0)
    definitions: dict[str, str]
    calculated_at: datetime


class TeachingPreflightActionDTO(BaseModel):
    """One teacher-facing action and its durable prerequisites."""

    action: Literal[
        "weakness_snapshot",
        "assignment_draft",
        "syllabus_candidate",
        "teaching_recommendation",
        "material_binding",
    ]
    ready: bool
    missing_requirements: list[str] = Field(default_factory=list)
    next_step: str


class TeacherProductionPreflightDTO(BaseModel):
    """Read-only course facts used before submitting teacher work."""

    course_id: UUID
    teaching_class_id: UUID | None = None
    active_class_count: int = Field(ge=0)
    teaching_class_available: bool
    enrolled_student_count: int = Field(ge=0)
    scored_student_count: int = Field(ge=0)
    scored_attempt_count: int = Field(ge=0)
    scored_coverage_rate: float = Field(ge=0, le=1)
    minimum_scored_student_count: int = Field(ge=1)
    knowledge_point_minimum_sample: int = Field(ge=1)
    knowledge_point_sample_ready_count: int = Field(ge=0)
    knowledge_point_sample_insufficient_count: int = Field(ge=0)
    active_assignment_count: int = Field(ge=0)
    submitted_assignment_count: int = Field(ge=0)
    graded_submission_count: int = Field(ge=0)
    window_start: datetime | None = None
    window_end: datetime | None = None
    window_note: str
    publishable_quiz_count: int = Field(ge=0)
    successful_agent_evidence_pair_count: int = Field(ge=0)
    ready_governed_asset_count: int = Field(ge=0)
    weakness_snapshot_count: int = Field(ge=0)
    actions: list[TeachingPreflightActionDTO]
    calculated_at: datetime


TeacherFormPurpose = Literal[
    "assignment",
    "teaching_recommendation",
    "syllabus_candidate",
    "subjective_grade",
    "asset_binding",
    "quiz_generation",
    "course_update",
    "notice",
]


class TeacherFormCandidateDTO(BaseModel):
    """Readable, in-scope candidate used by a teacher form selector."""

    id: UUID
    label: str
    summary: str
    state: str
    occurred_at: datetime | None = None


class TeacherFormQuizCandidateDTO(TeacherFormCandidateDTO):
    knowledge_node_id: UUID
    knowledge_node_name: str
    question_type: str
    difficulty: int = Field(ge=1, le=5)
    default_points: float = Field(gt=0)
    grading_mode: Literal["objective", "subjective"]


class TeacherFormMaterialCandidateDTO(TeacherFormCandidateDTO):
    document_asset_id: UUID | None = None


class TeacherFormAgentEvidencePairDTO(BaseModel):
    """A durable AgentRun/Evidence pair; IDs are selector values, never typed input."""

    agent_run_id: UUID
    evidence_snapshot_id: UUID
    label: str
    summary: str
    workflow_name: str
    occurred_at: datetime | None = None
    supports_typed_syllabus: bool = False
    supports_subjective_grade: bool = False


class TeacherFormContextDTO(BaseModel):
    """Course-scoped candidates and editable recommendation drafts for teacher forms."""

    course_id: UUID
    course_label: str
    purpose: TeacherFormPurpose
    teaching_classes: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    knowledge_points: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    publishable_quiz_items: list[TeacherFormQuizCandidateDTO] = Field(default_factory=list)
    material_candidates: list[TeacherFormMaterialCandidateDTO] = Field(default_factory=list)
    weakness_snapshots: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    agent_evidence_pairs: list[TeacherFormAgentEvidencePairDTO] = Field(default_factory=list)
    external_signals: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    syllabus_versions: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    teaching_recommendations: list[TeacherFormCandidateDTO] = Field(default_factory=list)
    dependency: TeachingPreflightActionDTO | None = None
    source_summary: list[str] = Field(default_factory=list)
    draft: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


class TeacherFormPrefillAuditDTO(BaseModel):
    """A durable record that a teacher applied a context prefill, not a submission."""

    course_id: UUID
    purpose: TeacherFormPurpose
    recorded_at: datetime


class BindCourseDocumentRequest(BaseModel):
    document_id: UUID
    document_asset_id: UUID | None = None
    purpose: str = Field(default="teaching_material", min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=500)


class CorrectCourseAssetRequest(BaseModel):
    replacement_document_id: UUID
    replacement_document_asset_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=500)


class AssetLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CourseAssetDTO(BaseModel):
    id: UUID
    course_id: UUID
    document_id: UUID
    document_title: str
    document_asset_id: UUID | None = None
    current_resource_id: UUID | None = None
    version_no: int = Field(ge=1)
    state: Literal[
        "uploading", "processing", "ready", "correction_pending", "corrected", "withdrawn", "deleted"
    ]
    correction_of_id: UUID | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class CourseAssetListDTO(BaseModel):
    items: list[CourseAssetDTO]


class CourseAssetPipelineEventDTO(BaseModel):
    """One persisted processing fact for a governed knowledge asset."""

    stage: str
    label: str
    state: Literal["completed", "pending", "failed"]
    occurred_at: datetime | None = None
    source: Literal["persisted_metadata", "persisted_record"]


class CourseAssetKnowledgeChunkDTO(BaseModel):
    """Teacher-readable, source-located chunk preview without raw internal IDs."""

    chunk_index: int = Field(ge=0)
    chapter: str | None = None
    page_no: int | None = Field(default=None, ge=1)
    excerpt: str = Field(min_length=1, max_length=800)
    knowledge_points: list[str] = Field(default_factory=list)
    embedding_status: str
    quality_state: str


class CourseAssetKnowledgeDetailDTO(BaseModel):
    """Read projection over existing documents/assets/chunks for one teacher asset."""

    asset: CourseAssetDTO
    source_type: str
    asset_type: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    page_count: int | None = Field(default=None, ge=0)
    chapter_count: int | None = Field(default=None, ge=0)
    chunk_count: int = Field(ge=0)
    indexed_chunk_count: int = Field(ge=0)
    pending_index_chunk_count: int = Field(ge=0)
    processing_elapsed_ms: int | None = Field(default=None, ge=0)
    processing_mode: str
    source_boundary: str
    source_url: str | None = None
    processing_timeline: list[CourseAssetPipelineEventDTO] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    chunks: list[CourseAssetKnowledgeChunkDTO] = Field(default_factory=list)


class QuizReviewRequest(BaseModel):
    decision: Literal["publish", "reject", "withdraw"]
    reason: str = Field(min_length=1, max_length=500)


class QuizReviewDecisionDTO(BaseModel):
    id: UUID
    quiz_item_id: UUID
    decision: Literal["publish", "reject", "withdraw"]
    before_status: str
    after_status: str
    reason: str
    created_at: datetime


class QuizCandidatePrepareRequest(BaseModel):
    """Teacher intent used to select an auditable, existing quiz candidate set."""

    knowledge_node_ids: list[UUID] = Field(default_factory=list, max_length=6)
    question_types: list[
        Literal["single_choice", "multi_choice", "fill", "short_answer", "code"]
    ] = Field(default_factory=list, max_length=5)
    quantity: int = Field(default=8, ge=1, le=36)
    target_difficulty: int = Field(default=3, ge=1, le=5)
    teaching_intent: str = Field(min_length=12, max_length=600)


class QuizCandidateItemDTO(BaseModel):
    id: UUID
    canonical_key: str
    knowledge_node_id: UUID
    knowledge_node_name: str
    question_type: Literal["single_choice", "multi_choice", "fill", "short_answer", "code"]
    difficulty: int = Field(ge=1, le=5)
    evidence_count: int = Field(ge=1)
    quality_state: Literal["passed"]


class QuizCandidatePreviewDTO(BaseModel):
    course_id: UUID
    source: Literal["persisted_quality_passed_bank"]
    live_generation_started: Literal[False] = False
    teaching_intent: str
    requested_quantity: int = Field(ge=1)
    available_count: int = Field(ge=0)
    items: list[QuizCandidateItemDTO] = Field(default_factory=list)
    next_step: str
    prepared_at: datetime


class WeaknessSnapshotRequest(BaseModel):
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    minimum_sample: int = Field(default=10, ge=1, le=10000)
    knowledge_point_minimum_sample: int = Field(default=5, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_window(self) -> "WeaknessSnapshotRequest":
        if self.window_start is not None and self.window_end is not None:
            if self.window_start > self.window_end:
                raise ValueError("时间窗起点不能晚于终点")
        return self


class WeaknessKnowledgePointDTO(BaseModel):
    knowledge_node_id: UUID
    knowledge_node_name: str
    sample_size: int = Field(ge=0)
    average_score: float = Field(ge=0, le=1)
    incorrect_rate: float = Field(ge=0, le=1)
    coverage_rate: float = Field(default=0, ge=0, le=1)
    trend: Literal["improving", "deteriorating", "stable", "insufficient_history"] = (
        "insufficient_history"
    )
    attention_status: Literal["needs_attention", "improving", "stable", "insufficient_sample"] = (
        "insufficient_sample"
    )
    weakness_score: float | None = Field(default=None, ge=0, le=1)
    previous_average_score: float | None = Field(default=None, ge=0, le=1)
    latest_attempt_at: datetime | None = None


class WeaknessSnapshotDTO(BaseModel):
    id: UUID
    course_id: UUID
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    sample_size: int = Field(ge=0)
    score_version: str
    input_fingerprint: str
    weak_knowledge_points: list[WeaknessKnowledgePointDTO]
    knowledge_point_metrics: list[WeaknessKnowledgePointDTO] = Field(default_factory=list)
    enrolled_student_count: int = Field(default=0, ge=0)
    scored_student_count: int = Field(default=0, ge=0)
    scored_coverage_rate: float = Field(default=0, ge=0, le=1)
    minimum_sample: int = Field(default=10, ge=1)
    knowledge_point_minimum_sample: int = Field(default=5, ge=1)
    window_start: datetime | None = None
    window_end: datetime | None = None
    latest_attempt_at: datetime | None = None
    computed_at: datetime


class WeaknessSnapshotListDTO(BaseModel):
    items: list[WeaknessSnapshotDTO]


class CreateTeachingRecommendationRequest(BaseModel):
    source_snapshot_id: UUID
    evidence_snapshot_id: UUID
    agent_run_id: UUID
    title: str = Field(min_length=8, max_length=200)
    actions: list[str] = Field(min_length=2, max_length=4)
    rationale: str = Field(min_length=120, max_length=1500)
    expected_impact: str = Field(min_length=30, max_length=600)

    @field_validator("actions")
    @classmethod
    def normalize_actions(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not 2 <= len(normalized) <= 4:
            raise ValueError("教学建议需要 2 至 4 条可执行行动")
        if len(set(normalized)) != len(normalized):
            raise ValueError("教学建议行动不能重复")
        if any(len(item) < 12 for item in normalized):
            raise ValueError("每条教学建议行动需说明具体教学动作")
        return normalized


TeachingActionType = Literal[
    "supplement_material",
    "review_assignment",
    "course_update_candidate",
    "syllabus_candidate",
    "learning_reminder",
]


class PendingTeachingActionDTO(BaseModel):
    """A durable draft created by adoption; it is never a published course change."""

    id: UUID
    action_type: TeachingActionType
    title: str
    draft: str
    status: Literal["pending_review"]
    created_at: datetime


class TeachingRecommendationDecisionRequest(BaseModel):
    decision: Literal["adopt", "reject", "withdraw"]
    reason: str = Field(min_length=1, max_length=500)
    action_type: TeachingActionType | None = None
    action_title: str | None = Field(default=None, min_length=8, max_length=200)
    action_draft: str | None = Field(default=None, min_length=80, max_length=3000)

    @model_validator(mode="after")
    def validate_adoption_action(self) -> "TeachingRecommendationDecisionRequest":
        action_values = (self.action_type, self.action_title, self.action_draft)
        if self.decision == "adopt":
            if any(value is None or not str(value).strip() for value in action_values):
                raise ValueError("采纳建议时必须填写待审核教学动作的类型、标题和草稿")
        elif any(value is not None for value in action_values):
            raise ValueError("仅采纳建议时可以创建待审核教学动作")
        return self


class TeachingRecommendationDTO(BaseModel):
    id: UUID
    course_id: UUID
    source_snapshot_id: UUID
    evidence_snapshot_id: UUID
    agent_run_id: UUID | None = None
    version_no: int = Field(ge=1)
    diff: dict[str, Any]
    status: Literal["pending", "adopted", "rejected", "superseded", "withdrawn"]
    pending_teaching_action: PendingTeachingActionDTO | None = None
    created_at: datetime


class TeachingRecommendationListDTO(BaseModel):
    items: list[TeachingRecommendationDTO]


class AssessmentCreateRequest(BaseModel):
    kind: Literal["assignment", "exam"]
    logical_key: str = Field(min_length=1, max_length=128)

    @field_validator("logical_key")
    @classmethod
    def normalize_logical_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("评估逻辑键不能为空")
        return value


class AssessmentDTO(BaseModel):
    id: UUID
    course_id: UUID
    kind: Literal["assignment", "exam"]
    logical_key: str
    status: Literal["draft", "published", "closed", "withdrawn"]
    created_at: datetime
    updated_at: datetime


class AssessmentVersionItemRequest(BaseModel):
    quiz_item_id: UUID
    position: int = Field(ge=1, le=200)
    points: float = Field(gt=0, le=1000)
    grading_mode: Literal["objective", "subjective"]


class AssessmentVersionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    instructions: str | None = Field(default=None, max_length=5000)
    items: list[AssessmentVersionItemRequest] = Field(min_length=1, max_length=200)


class AssessmentVersionItemDTO(BaseModel):
    id: UUID
    quiz_item_id: UUID
    position: int
    points: float
    grading_mode: Literal["objective", "subjective"]
    question_snapshot: dict[str, Any]


class AssessmentVersionDTO(BaseModel):
    id: UUID
    assessment_id: UUID
    version_no: int
    title: str
    instructions: str | None = None
    state: Literal["draft", "published", "withdrawn"]
    frozen_at: datetime | None = None
    items: list[AssessmentVersionItemDTO]
    created_at: datetime


class AssignmentCreateRequest(BaseModel):
    target_type: Literal["class", "group", "student"]
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    student_id: UUID | None = None
    due_at: datetime
    allow_late: bool = False
    reason: str | None = Field(default=None, max_length=500)


class AssessmentAssignmentDTO(BaseModel):
    id: UUID
    assessment_version_id: UUID
    target_type: Literal["class", "group", "student"]
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    student_id: UUID | None = None
    due_at: datetime
    allow_late: bool
    status: Literal["active", "closed", "withdrawn"]
    created_at: datetime


class TeacherAssignmentDTO(BaseModel):
    """Teacher-facing durable assignment projection, not a second assessment store."""

    id: UUID
    course_id: UUID
    assessment_id: UUID
    assessment_version_id: UUID
    logical_key: str
    kind: Literal["assignment", "exam"]
    title: str
    version_no: int = Field(ge=1)
    target_type: Literal["class", "group", "student"]
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    student_id: UUID | None = None
    due_at: datetime
    allow_late: bool
    status: Literal["active", "closed", "withdrawn"]
    created_at: datetime


class TeacherAssignmentListDTO(BaseModel):
    items: list[TeacherAssignmentDTO]


class SubmitAssessmentRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


class StudentAssessmentQuestionDTO(BaseModel):
    """Published question projection; answer and explanation never leave this API."""

    quiz_item_id: UUID
    position: int = Field(ge=1)
    points: float = Field(gt=0)
    grading_mode: Literal["objective", "subjective"]
    knowledge_node_name: str
    question_type: str
    question: str
    options: list[str] = Field(default_factory=list)
    content_version: int = Field(ge=1)


class StudentAssessmentReadDTO(BaseModel):
    """Student-scoped view of one open, published assessment assignment."""

    assignment_id: UUID
    course_id: UUID
    title: str
    instructions: str | None = None
    due_at: datetime
    allow_late: bool
    status: Literal["active"]
    submission_status: Literal["open", "submitted", "late", "locked"]
    items: list[StudentAssessmentQuestionDTO]


class AssessmentSubmissionDTO(BaseModel):
    id: UUID
    assignment_id: UUID
    student_id: UUID
    status: Literal["open", "submitted", "late", "locked"]
    submitted_at: datetime | None = None


class ObjectiveScoreDTO(BaseModel):
    submission_id: UUID
    objective_score: float = Field(ge=0)
    total_objective_points: float = Field(ge=0)
    status: Literal["auto_scored", "teacher_reviewed", "published", "withdrawn"]


class RecordSubjectiveSuggestionRequest(BaseModel):
    agent_run_id: UUID
    evidence_snapshot_id: UUID


class GradeOverrideRequest(BaseModel):
    final_score: float = Field(ge=0, le=100000)
    reason: str = Field(min_length=1, max_length=500)


class GradeDecisionDTO(BaseModel):
    id: UUID
    submission_id: UUID
    objective_score: float | None = None
    ai_suggested_score: float | None = None
    ai_agent_run_id: UUID | None = None
    ai_evidence_snapshot_id: UUID | None = None
    ai_suggestion_status: Literal["not_requested", "suggested", "rejected"]
    final_score: float | None = None
    status: Literal["pending", "auto_scored", "teacher_reviewed", "published", "withdrawn"]
    override_reason: str | None = None
    published_at: datetime | None = None
    withdrawn_at: datetime | None = None


class TeacherAssessmentSubmissionDTO(BaseModel):
    """Read projection for a teacher's in-scope submission and grade state."""

    id: UUID
    assignment_id: UUID
    student_id: UUID
    student_display_name: str
    status: Literal["open", "submitted", "late", "locked"]
    submitted_at: datetime | None = None
    grade: GradeDecisionDTO | None = None


class TeacherAssessmentSubmissionListDTO(BaseModel):
    items: list[TeacherAssessmentSubmissionDTO]


class StudentPublishedResultDTO(BaseModel):
    assignment_id: UUID
    submission_id: UUID
    final_score: float
    published_at: datetime
    status: Literal["published"]
