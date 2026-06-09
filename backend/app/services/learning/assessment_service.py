# Status: planned

"""Per task brief §6.2 — AssessmentService grades a quiz, writes
``quiz_attempts`` + ``learning_events``, then triggers CapabilityService."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class AssessmentResult:
    attempt_id: UUID
    is_correct: bool | None
    score: float | None
    capability_delta: dict[str, float]


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def grade_attempt(
        self,
        *,
        user_id: UUID,
        quiz_item_id: UUID,
        submitted_answer: dict[str, Any],
    ) -> AssessmentResult:
        raise NotImplementedError(
            "planned: P1 — outcome_evaluator.RunAssessment + capability rollup"
        )
