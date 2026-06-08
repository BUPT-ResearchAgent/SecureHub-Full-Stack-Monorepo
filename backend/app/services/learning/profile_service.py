# Status: planned

"""Per task brief §6.2 — ProfileService manages ``user_profiles.dimensions``
(merged persona JSONB) and the persona embedding."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_persona(self, user_id: UUID) -> dict[str, Any] | None:
        raise NotImplementedError("planned: P0")

    async def upsert_persona(
        self,
        user_id: UUID,
        dimensions: dict[str, Any],
        *,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError("planned: P0")

    async def apply_event_update(
        self, user_id: UUID, dimensions_patch: dict[str, Any]
    ) -> dict[str, Any]:
        """Called by ``career_planner.UpdatePersona`` to roll a learning
        event into the persona — implements the public side of the
        ``learning_events → user_profiles`` chain (rule §3.4)."""
        raise NotImplementedError("planned: P1")
