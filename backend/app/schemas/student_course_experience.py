# Status: real

"""Student-scoped course experience DTOs.

These projections are intentionally additive.  They expose only the current
student's enrolment, progress, submissions, and course-scoped curated assets;
they never accept a caller-controlled student, class, group, AgentRun, or
Evidence Snapshot identifier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StudentCourseEvidenceDTO(BaseModel):
    label: str
    excerpt: str
    source_kind: Literal["curated-demo", "external-preview", "real"]
    source_url: str | None = None


class StudentCourseProfileDTO(BaseModel):
    display_name: str
    teaching_class_name: str
    group_name: str | None = None
    learning_story: str
    learning_story_summary: str
    source_boundary: str


class StudentCourseCapabilityDTO(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)


class StudentCourseTaskDTO(BaseModel):
    title: str
    knowledge_point: str | None = None
    status: Literal["todo", "active", "done", "blocked"]
    order_index: int = Field(ge=0)


class StudentCourseResourceDTO(BaseModel):
    # Opaque to normal presentation; the client only returns it to the
    # current-student feedback endpoint and never renders it as a label.
    resource_id: UUID
    lineage_root_id: UUID
    logical_key: str
    resource_type: Literal["doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"]
    title: str
    knowledge_point: str | None = None
    version: int = Field(ge=1)
    available_versions: list[int] = Field(default_factory=list)
    quality_state: str
    source_kind: Literal["curated-demo", "external-preview", "real"]
    source_boundary: str
    content: dict[str, Any] = Field(default_factory=dict)
    evidence: list[StudentCourseEvidenceDTO] = Field(default_factory=list)
    updated_at: datetime | None = None


class StudentCourseAssignmentDTO(BaseModel):
    id: UUID
    logical_key: str
    title: str
    due_at: datetime
    allow_late: bool
    question_count: int = Field(ge=0)
    assignment_status: Literal["active", "closed", "withdrawn"]
    learner_status: Literal[
        "not_started", "submitted", "late", "grading", "teacher_review", "published", "withdrawn"
    ]
    published_score: float | None = Field(default=None, ge=0)
    next_action: str


class StudentCourseUpdateDTO(BaseModel):
    subject: str
    body: str
    delivered_at: datetime
    read: bool


class StudentCourseTutorExchangeDTO(BaseModel):
    question: str
    concept: str
    defensive_example: str
    next_step: str
    evidence_status: Literal["available", "insufficient"]
    source_kind: Literal["curated-demo", "real"]
    source_boundary: str
    evidence: list[StudentCourseEvidenceDTO] = Field(default_factory=list)
    recorded_at: datetime


class StudentCourseKnowledgeMetricDTO(BaseModel):
    knowledge_point: str
    baseline_average: float | None = Field(default=None, ge=0, le=1)
    recent_average: float | None = Field(default=None, ge=0, le=1)
    sample_size: int = Field(ge=0)
    trend: Literal["improving", "stable", "needs_attention", "insufficient"]


class StudentCourseAssessmentDTO(BaseModel):
    baseline_average: float | None = Field(default=None, ge=0, le=1)
    recent_average: float | None = Field(default=None, ge=0, le=1)
    trend: Literal["improving", "stable", "needs_attention", "insufficient"]
    scored_attempt_count: int = Field(ge=0)
    metrics: list[StudentCourseKnowledgeMetricDTO] = Field(default_factory=list)
    feedback_boundary: str


class StudentCourseExperienceDTO(BaseModel):
    course_id: UUID
    course_code: Literal["WEBSEC-101"]
    data_status: Literal["ready", "incomplete"]
    missing_dependencies: list[str] = Field(default_factory=list)
    profile: StudentCourseProfileDTO
    progress_percent: float = Field(ge=0, le=100)
    next_step: str
    tasks: list[StudentCourseTaskDTO] = Field(default_factory=list)
    capabilities: list[StudentCourseCapabilityDTO] = Field(default_factory=list)
    resources: list[StudentCourseResourceDTO] = Field(default_factory=list)
    assignments: list[StudentCourseAssignmentDTO] = Field(default_factory=list)
    updates: list[StudentCourseUpdateDTO] = Field(default_factory=list)
    tutor_exchanges: list[StudentCourseTutorExchangeDTO] = Field(default_factory=list)
    assessment: StudentCourseAssessmentDTO
