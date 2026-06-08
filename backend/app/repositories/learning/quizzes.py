# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.repositories.base import UUIDPKRepository


class QuizItemRepository(UUIDPKRepository[QuizItem]):
    model = QuizItem

    async def list_by_kp(
        self, kp_id: UUID, *, limit: int = 50
    ) -> Sequence[QuizItem]:
        stmt = (
            select(QuizItem)
            .where(QuizItem.kp_id == kp_id)
            .order_by(QuizItem.difficulty, QuizItem.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        item_id: UUID,
        kp_id: UUID,
        type: str,
        question: str,
        answer: str,
        difficulty: int,
        options: dict[str, Any] | list[Any] | None = None,
        generated_by_skill: UUID | None = None,
    ) -> QuizItem:
        row = QuizItem(
            id=item_id,
            kp_id=kp_id,
            type=type,
            question=question,
            options=options,
            answer=answer,
            difficulty=difficulty,
            generated_by_skill=generated_by_skill,
        )
        self.session.add(row)
        await self.session.flush()
        return row


class QuizAttemptRepository(UUIDPKRepository[QuizAttempt]):
    model = QuizAttempt

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        quiz_item_id: UUID | None = None,
        limit: int = 100,
    ) -> Sequence[QuizAttempt]:
        stmt = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        if quiz_item_id is not None:
            stmt = stmt.where(QuizAttempt.quiz_item_id == quiz_item_id)
        stmt = stmt.order_by(QuizAttempt.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        attempt_id: UUID,
        quiz_item_id: UUID,
        user_id: UUID,
        submitted_answer: dict[str, Any],
        is_correct: bool | None = None,
        score: float | None = None,
        feedback: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QuizAttempt:
        row = QuizAttempt(
            id=attempt_id,
            quiz_item_id=quiz_item_id,
            user_id=user_id,
            submitted_answer=submitted_answer,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
