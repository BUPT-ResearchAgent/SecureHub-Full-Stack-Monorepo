# Status: real

"""Tutor request and response DTOs."""

from uuid import UUID

from pydantic import BaseModel, Field


class TutorAskRequest(BaseModel):
    user_id: UUID
    course_id: UUID
    question: str = Field(min_length=1)
    context: dict[str, object] = Field(default_factory=dict)


class TutorAskResponse(BaseModel):
    task_id: str
    status: str = "ok"
    routing: dict[str, object]
