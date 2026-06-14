# Status: real

"""Learner profile DTOs mirrored by profile endpoints and frontend radar UI."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CapabilityDTO(BaseModel):
    dimension: str
    score: float
    confidence: float
    evidence_count: int


class ProfileDimensionsDTO(BaseModel):
    dimensions: dict[str, Any]


class ProfileDTO(BaseModel):
    user_id: str
    dimensions: dict[str, Any]
    capabilities: list[CapabilityDTO]
    updated_at: datetime
