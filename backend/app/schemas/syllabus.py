# Status: real

"""Strict typed syllabus contracts; arbitrary documents are not syllabuses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SyllabusModuleContent(BaseModel):
    module_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    knowledge_node_ids: list[UUID] = Field(min_length=1, max_length=30)
    learning_outcome: str = Field(min_length=1, max_length=1000)
    activities: list[str] = Field(min_length=1, max_length=12)


class TypedSyllabusContent(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=4000)
    learning_outcomes: list[str] = Field(min_length=1, max_length=20)
    modules: list[SyllabusModuleContent] = Field(min_length=1, max_length=32)
    assessment_plan: str = Field(min_length=1, max_length=2000)
    source_note: str = Field(min_length=1, max_length=1000)

    @field_validator("learning_outcomes")
    @classmethod
    def normalize_outcomes(cls, value: list[str]) -> list[str]:
        normalized = [entry.strip() for entry in value if entry.strip()]
        if not normalized:
            raise ValueError("至少需要一个学习目标")
        return normalized


class CreateSyllabusVersionRequest(BaseModel):
    typed_content: TypedSyllabusContent
    reason: str = Field(min_length=1, max_length=500)


class GenerateSyllabusVersionRequest(BaseModel):
    """Accept only a completed Runtime/Skill result already carrying evidence."""

    agent_run_id: UUID
    evidence_snapshot_id: UUID
    reason: str = Field(min_length=1, max_length=500)


class SyllabusReviewRequest(BaseModel):
    decision: Literal["approve", "reject", "withdraw"]
    reason: str = Field(min_length=1, max_length=500)


class SyllabusExportRequest(BaseModel):
    format: Literal["json", "markdown"]


class SyllabusVersionDTO(BaseModel):
    id: UUID
    syllabus_id: UUID
    version_no: int = Field(ge=1)
    typed_content: TypedSyllabusContent
    content_schema_version: Literal["syllabus-v1"]
    state: Literal["draft", "generation_pending", "review_pending", "published", "superseded", "withdrawn"]
    generated_from_agent_run_id: UUID | None = None
    evidence_snapshot_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SyllabusDiffDTO(BaseModel):
    from_version_id: UUID | None = None
    to_version_id: UUID
    changed_fields: list[str]
    added_module_ids: list[str]
    removed_module_ids: list[str]


class SyllabusExportDTO(BaseModel):
    id: UUID
    version_id: UUID
    format: Literal["json", "markdown"]
    generated_resource_id: UUID | None = None
    status: Literal["ready", "withdrawn", "failed"]
    content: str | dict[str, object]
    created_at: datetime
