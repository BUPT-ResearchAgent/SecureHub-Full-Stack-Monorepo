# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.learning.learning_event import LearningEvent
from app.repositories.base import UUIDPKRepository


class LearningEventRepository(UUIDPKRepository[LearningEvent]):
    model = LearningEvent

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[LearningEvent]:
        stmt = select(LearningEvent).where(LearningEvent.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(LearningEvent.event_type == event_type)
        stmt = (
            stmt.order_by(LearningEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        event_type: str,
        kp_id: UUID | None = None,
        resource_id: UUID | None = None,
        result: dict[str, Any] | None = None,
    ) -> LearningEvent:
        row = LearningEvent(
            id=event_id,
            user_id=user_id,
            event_type=event_type,
            kp_id=kp_id,
            resource_id=resource_id,
            result=result or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
