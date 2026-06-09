# Status: partial-real

"""Pydantic schemas for the ``/api/v1/profile/*`` surface (data-layer v2)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    user_id: UUID
    display_name: str
    email: str
    dimensions: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None


class ProfileUpdateIn(BaseModel):
    dimensions: dict[str, Any]


class CapabilityOut(BaseModel):
    dimension: str
    score: float
    confidence: float
    evidence_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityListOut(BaseModel):
    user_id: UUID
    items: list[CapabilityOut]
