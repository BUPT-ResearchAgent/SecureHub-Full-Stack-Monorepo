# Status: real

"""Student-owned path-replan and resource-feedback API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ReplanStatus = Literal["pending", "deferred", "accepted", "reverted", "expired"]
ReplanDecision = Literal["accept", "defer", "revert"]
RecommendationStatus = Literal[
    "scheduled", "accepted", "deferred", "rejected", "superseded", "feedback_received", "completed"
]
FeedbackKind = Literal["too_difficult", "too_shallow", "missing_example", "want_diagram", "want_practice"]
FeedbackStatus = Literal[
    "submitted", "retry_requested", "regenerated", "provider_unavailable", "failed", "rejected"
]


class PathReplanCreateRequest(BaseModel):
    """The caller may cite one owned trigger, or let the service choose the latest owned event."""

    trigger_event_id: UUID | None = None
    assessment_workflow_run_id: UUID | None = None

    @model_validator(mode="after")
    def _at_most_one_trigger(self) -> "PathReplanCreateRequest":
        if self.trigger_event_id is not None and self.assessment_workflow_run_id is not None:
            raise ValueError("一次重规划只能引用一个触发来源")
        return self


class PathReplanDecisionRequest(BaseModel):
    decision: ReplanDecision
    reason: str | None = Field(default=None, max_length=400)


class PathTaskChangeDTO(BaseModel):
    action: Literal["added", "retained"]
    title: str
    knowledge_point: str | None = None
    status: Literal["todo", "active", "done", "blocked"]
    expected_minutes: int = Field(ge=0)


class PathVersionDTO(BaseModel):
    id: UUID
    version_no: int = Field(ge=1)
    kind: Literal["baseline", "replan", "revert"]
    state: Literal["active", "historical"]
    title: str
    summary: str
    diff: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PathReplanCandidateDTO(BaseModel):
    id: UUID
    status: ReplanStatus
    source_version_no: int = Field(ge=1)
    accepted_version_no: int | None = Field(default=None, ge=1)
    trigger_label: str
    trigger_at: datetime | None = None
    reason_code: str
    reason_text: str
    affected_knowledge_point: str | None = None
    expected_minutes: int = Field(ge=0)
    changed_tasks: list[PathTaskChangeDTO] = Field(default_factory=list)
    source_boundary: str
    created_at: datetime
    updated_at: datetime


class ResourceRecommendationDTO(BaseModel):
    id: UUID
    resource_id: UUID
    title: str
    resource_type: str
    knowledge_point: str | None = None
    status: RecommendationStatus
    scheduled_at: datetime
    rationale: str
    source_boundary: str
    created_at: datetime


class ResourceRecommendationDecisionRequest(BaseModel):
    decision: Literal["accept", "defer", "reject", "complete"]
    reason: str | None = Field(default=None, max_length=400)


class ResourceFeedbackRequest(BaseModel):
    feedback_kinds: list[FeedbackKind] = Field(min_length=1, max_length=5)
    comment: str | None = Field(default=None, max_length=500)
    recommendation_id: UUID | None = None
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)


class ResourceFeedbackDTO(BaseModel):
    id: UUID
    resource_id: UUID
    status: FeedbackStatus
    feedback_kinds: list[FeedbackKind]
    comment: str | None = None
    retry_workflow_run_id: UUID | None = None
    resulting_resource_id: UUID | None = None
    outcome: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ResourceFeedbackSubmitResponse(BaseModel):
    feedback: ResourceFeedbackDTO
    workflow: dict[str, Any] | None = None


class ResourceLineageVersionDTO(BaseModel):
    resource_id: UUID
    version: int = Field(ge=1)
    parent_resource_id: UUID | None = None
    title: str
    status: str
    quality_score: float | None = None
    quality_delta: float | None = None
    changed_fields: list[str] = Field(default_factory=list)
    change_summary: str | None = None
    evidence_count: int = Field(ge=0)
    run_state: str
    source_kind: Literal["curated-demo", "external-preview", "real"]
    source_boundary: str
    created_at: datetime


class ResourceLineageDTO(BaseModel):
    lineage_root_id: UUID
    logical_key: str
    resource_type: str
    title: str
    knowledge_point: str | None = None
    current_resource_id: UUID
    versions: list[ResourceLineageVersionDTO] = Field(default_factory=list)


class StudentLearningLoopDTO(BaseModel):
    course_id: UUID
    candidates: list[PathReplanCandidateDTO] = Field(default_factory=list)
    path_versions: list[PathVersionDTO] = Field(default_factory=list)
    recommendations: list[ResourceRecommendationDTO] = Field(default_factory=list)
    feedback: list[ResourceFeedbackDTO] = Field(default_factory=list)
    resource_lineages: list[ResourceLineageDTO] = Field(default_factory=list)


__all__ = [
    "PathReplanCandidateDTO",
    "PathReplanCreateRequest",
    "PathReplanDecisionRequest",
    "PathVersionDTO",
    "ResourceFeedbackDTO",
    "ResourceFeedbackRequest",
    "ResourceFeedbackSubmitResponse",
    "ResourceLineageDTO",
    "ResourceRecommendationDecisionRequest",
    "StudentLearningLoopDTO",
]
