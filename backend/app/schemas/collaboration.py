# Status: real

"""HTTP DTOs for evidence-bound updates and interpersonal messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ExternalSignalIngestRequest(BaseModel):
    kind: Literal["policy", "hot", "job"]
    source_document_id: UUID
    agent_run_id: UUID
    evidence_snapshot_id: UUID
    title: str = Field(min_length=1, max_length=200)


class ExternalSignalDTO(BaseModel):
    id: UUID
    kind: Literal["policy", "hot", "job"]
    title: str
    source_document_id: UUID
    agent_run_id: UUID
    evidence_snapshot_id: UUID
    source_fingerprint: str
    status: Literal["ingested", "validated", "rejected", "expired"]
    summary: str | None = None
    ingested_at: datetime


class CourseUpdateImpactRequest(BaseModel):
    knowledge_node_id: UUID
    impact_type: Literal["add", "revise", "retire", "emphasize"]
    rationale: str = Field(min_length=1, max_length=2000)


class CourseUpdateImpactDTO(CourseUpdateImpactRequest):
    id: UUID


class CreateCourseUpdateSuggestionRequest(BaseModel):
    course_id: UUID
    signal_id: UUID
    title: str = Field(min_length=1, max_length=200)
    diff: dict[str, Any]
    impacts: list[CourseUpdateImpactRequest] = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _require_nonempty_diff(self) -> "CreateCourseUpdateSuggestionRequest":
        if not self.diff:
            raise ValueError("建议 diff 不能为空")
        return self


class CourseUpdateDecisionRequest(BaseModel):
    decision: Literal["adopt", "reject"]
    reason: str = Field(min_length=1, max_length=2000)


class CourseUpdateDecisionDTO(BaseModel):
    id: UUID
    suggestion_id: UUID
    teacher_id: UUID
    decision: Literal["adopt", "reject"]
    reason: str
    decided_at: datetime


class CourseUpdateSuggestionDTO(BaseModel):
    id: UUID
    course_id: UUID
    signal_id: UUID
    agent_run_id: UUID
    evidence_snapshot_id: UUID
    version_no: int
    title: str
    diff: dict[str, Any]
    status: Literal[
        "draft", "pending_teacher_decision", "adopted", "rejected", "superseded", "withdrawn"
    ]
    impacts: list[CourseUpdateImpactDTO]
    decision: CourseUpdateDecisionDTO | None = None
    created_at: datetime
    updated_at: datetime


class MessageSendRequest(BaseModel):
    scope_type: Literal["course", "class", "individual"]
    course_id: UUID
    teaching_class_id: UUID | None = None
    target_user_id: UUID | None = None
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _validate_scope_shape(self) -> "MessageSendRequest":
        if self.scope_type == "course" and self.teaching_class_id is None and self.target_user_id is None:
            return self
        if self.scope_type == "class" and self.teaching_class_id is not None and self.target_user_id is None:
            return self
        if self.scope_type == "individual" and self.teaching_class_id is None and self.target_user_id is not None:
            return self
        raise ValueError("收件范围与课程、教学班或个人收件人不一致")


class RecallMessageRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class MessageDTO(BaseModel):
    id: UUID
    sender_user_id: UUID
    scope_type: Literal["course", "class", "individual"]
    course_id: UUID
    teaching_class_id: UUID | None = None
    target_user_id: UUID | None = None
    subject: str
    body: str
    safety_state: Literal["accepted", "rejected"]
    status: Literal["draft", "sent", "partially_delivered", "recalled", "expired"]
    sent_at: datetime | None = None
    recall_deadline_at: datetime | None = None
    recalled_at: datetime | None = None
    delivery_counts: dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MessageInboxItemDTO(MessageDTO):
    delivery_state: Literal["unread", "read", "recalled"]
    delivered_at: datetime
    read_at: datetime | None = None


class MessageInboxDTO(BaseModel):
    items: list[MessageInboxItemDTO]


class MessageReadDTO(BaseModel):
    message_id: UUID
    delivery_state: Literal["unread", "read", "recalled"]
    read_at: datetime | None = None
