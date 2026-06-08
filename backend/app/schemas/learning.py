# Status: partial-real

"""Pydantic schemas for ``/api/v1/quiz-attempts`` etc. (P1 surface; the P0
endpoints don't need them yet but the file is kept here so the P0 → P1 jump
doesn't have to invent a new module).
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QuizAttemptIn(BaseModel):
    quiz_item_id: UUID
    submitted_answer: dict[str, Any]


class QuizAttemptOut(BaseModel):
    id: UUID
    quiz_item_id: UUID
    user_id: UUID
    is_correct: bool | None
    score: float | None
    feedback: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
