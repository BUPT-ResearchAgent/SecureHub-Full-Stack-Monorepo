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

from pydantic import BaseModel, Field, field_validator


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


class WeaknessSnapshotRequest(BaseModel):
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    minimum_sample: int = Field(default=1, ge=1, le=10000)


class WeaknessKnowledgePointDTO(BaseModel):
    knowledge_node_id: UUID
    knowledge_node_name: str
    sample_size: int = Field(ge=0)
    average_score: float = Field(ge=0, le=1)
    incorrect_rate: float = Field(ge=0, le=1)


class WeaknessSnapshotDTO(BaseModel):
    id: UUID
    course_id: UUID
    teaching_class_id: UUID | None = None
    group_id: UUID | None = None
    sample_size: int = Field(ge=0)
    score_version: str
    input_fingerprint: str
    weak_knowledge_points: list[WeaknessKnowledgePointDTO]
    computed_at: datetime


class WeaknessSnapshotListDTO(BaseModel):
    items: list[WeaknessSnapshotDTO]


class CreateTeachingRecommendationRequest(BaseModel):
    source_snapshot_id: UUID
    evidence_snapshot_id: UUID
    agent_run_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    actions: list[str] = Field(min_length=1, max_length=12)
    rationale: str = Field(min_length=1, max_length=1500)

    @field_validator("actions")
    @classmethod
    def normalize_actions(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            raise ValueError("教学建议至少需要一项行动")
        return normalized


class TeachingRecommendationDecisionRequest(BaseModel):
    decision: Literal["adopt", "reject", "withdraw"]
    reason: str = Field(min_length=1, max_length=500)


class TeachingRecommendationDTO(BaseModel):
    id: UUID
    course_id: UUID
    source_snapshot_id: UUID
    evidence_snapshot_id: UUID
    agent_run_id: UUID | None = None
    version_no: int = Field(ge=1)
    diff: dict[str, Any]
    status: Literal["pending", "adopted", "rejected", "superseded", "withdrawn"]
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
