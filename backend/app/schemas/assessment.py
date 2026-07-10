# Status: real

"""Assessment request and response DTOs."""

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


class AssessmentRunResponse(BaseModel):
    score: float
    feedback: str
    updated_capabilities: list[CapabilityDTO] = Field(default_factory=list)


class AssessmentResultDTO(AssessmentRunResponse):
    pass
