# Status: real

"""Pydantic schemas for generated learning resources."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

JsonObject = dict[str, object]
ResourceType = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video", "readings"]
ResourceStatus = Literal["generating", "ready", "failed"]


class ResourceGenerateRequest(BaseModel):
    type: ResourceType
    kp_id: str
    user_id: str
    options: JsonObject | None = None


class GeneratedResourceDTO(BaseModel):
    id: str
    resource_type: ResourceType
    title: str
    content: JsonObject | None = None
    object_key: str | None = None
    evidence_chunk_ids: list[str]
    quality_score: float
    status: ResourceStatus


class GeneratedResourceOut(BaseModel):
    id: UUID
    resource_type: str
    title: str
    user_id: UUID | None = None
    course_id: UUID | None = None
    kp_id: UUID | None = None
    agent_run_id: UUID | None = None
    content: JsonObject = Field(default_factory=dict)
    object_key: str | None = None
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    quality_score: float | None = None
    status: str
    metadata: JsonObject = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class GeneratedResourceListOut(BaseModel):
    items: list[GeneratedResourceOut]
    total: int
