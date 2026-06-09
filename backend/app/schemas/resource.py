# Status: partial-real

"""Pydantic schemas for ``/api/v1/courses/{cid}/resources/generate`` +
``/api/v1/resources`` (data-layer v2).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GeneratedResourceOut(BaseModel):
    id: UUID
    resource_type: str
    title: str
    user_id: UUID | None = None
    course_id: UUID | None = None
    kp_id: UUID | None = None
    agent_run_id: UUID | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    object_key: str | None = None
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    quality_score: float | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class GeneratedResourceListOut(BaseModel):
    items: list[GeneratedResourceOut]
    total: int
