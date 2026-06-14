# Status: real

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.identity.user_profile import UserProfile
from app.repositories.base import BaseRepository


class UserProfileRepository(BaseRepository):
    """Owns ``user_profiles`` — the merged-persona JSONB row keyed by ``user_id``."""

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: UUID,
        dimensions: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> UserProfile:
        existing = await self.get_by_user_id(user_id)
        if existing is None:
            row = UserProfile(
                user_id=user_id,
                dimensions=dimensions,
                embedding=embedding,
            )
            self.session.add(row)
            await self.session.flush()
            return row
        existing.dimensions = dimensions
        if embedding is not None:
            existing.embedding = embedding
        await self.session.flush()
        return existing

    async def update_dimensions(
        self, user_id: UUID, dimensions_patch: dict[str, Any]
    ) -> UserProfile | None:
        """Shallow-merge ``dimensions_patch`` into the existing JSONB. Returns
        ``None`` when no profile row exists for ``user_id``."""
        existing = await self.get_by_user_id(user_id)
        if existing is None:
            return None
        merged = {**(existing.dimensions or {}), **dimensions_patch}
        existing.dimensions = merged
        await self.session.flush()
        return existing
