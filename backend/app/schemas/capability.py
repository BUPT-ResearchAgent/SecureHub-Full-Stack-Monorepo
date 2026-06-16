# Status: real

"""Capability DTOs shared by profile and assessment flows."""

from pydantic import BaseModel


class CapabilityRadarDTO(BaseModel):
    dimension: str
    score: float
    confidence: float
    evidence_count: int


CapabilityDTO = CapabilityRadarDTO
