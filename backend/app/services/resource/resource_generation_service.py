# Status: planned

"""Per task brief §6.4 — ResourceGenerationService takes a finished agent run
output and writes a ``generated_resources`` row, bound to ``evidence_chunk_ids``
and ``agent_run_id`` for the citation chain.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ResourceGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self,
        *,
        resource_type: str,
        title: str,
        user_id: UUID | None,
        course_id: UUID | None,
        kp_id: UUID | None,
        agent_run_id: UUID | None,
        content: dict[str, Any] | None,
        object_key: str | None,
        evidence_chunk_ids: list[UUID],
        quality_score: float | None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """Return the newly created ``generated_resources.id``."""
        raise NotImplementedError("planned: P0")

    async def mark_status(self, resource_id: UUID, status: str) -> None:
        raise NotImplementedError("planned: P0")
