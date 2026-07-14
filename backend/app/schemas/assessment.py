# Status: real

"""Assessment request and response DTOs."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.capability import CapabilityDTO


class AssessmentAnswerDTO(BaseModel):
    quiz_item_id: str | None = None
    answer: object | None = None


class AssessmentRunRequest(BaseModel):
    user_id: UUID
    course_id: UUID
    answers: list[dict[str, object]] = Field(default_factory=list)
    quiz_artifact_id: str | None = None
    mode: Literal["fixture", "real"] = "real"
    provider: str | None = None
    model: str | None = None


class AssessmentRunResponse(BaseModel):
    score: float
    feedback: str
    updated_capabilities: list[CapabilityDTO] = Field(default_factory=list)
    assessment_audit: dict[str, object] | None = None


class AssessmentResultDTO(AssessmentRunResponse):
    pass
