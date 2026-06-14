# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models.identity.user_capability import UserCapability
from app.repositories.base import BaseRepository


class UserCapabilityRepository(BaseRepository):
    """Owns ``user_capabilities`` — radar-chart dimensions per user."""

    async def list_by_user(self, user_id: UUID) -> Sequence[UserCapability]:
        result = await self.session.execute(
            select(UserCapability)
            .where(UserCapability.user_id == user_id)
            .order_by(UserCapability.dimension)
        )
        return result.scalars().all()

    async def get(self, user_id: UUID, dimension: str) -> UserCapability | None:
        result = await self.session.execute(
            select(UserCapability).where(
                UserCapability.user_id == user_id,
                UserCapability.dimension == dimension,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_score(
        self,
        *,
        user_id: UUID,
        dimension: str,
        score: float,
        confidence: float = 0.0,
        evidence_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> UserCapability:
        existing = await self.get(user_id, dimension)
        if existing is None:
            row = UserCapability(
                id=uuid4(),
                user_id=user_id,
                dimension=dimension,
                score=score,
                confidence=confidence,
                evidence_count=evidence_count,
                metadata_=metadata or {},
            )
            self.session.add(row)
            await self.session.flush()
            return row
        existing.score = score
        existing.confidence = confidence
        existing.evidence_count = evidence_count
        if metadata is not None:
            existing.metadata_ = metadata
        await self.session.flush()
        return existing
