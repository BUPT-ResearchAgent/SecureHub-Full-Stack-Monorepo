# Status: planned

"""Per task brief §6.2 — CapabilityService updates ``user_capabilities`` from
quiz attempts and learning events; backs the radar chart in the Profile UI.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class CapabilityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_user_capabilities(
        self, user_id: UUID
    ) -> Sequence[dict[str, Any]]:
        raise NotImplementedError("planned: P0")

    async def apply_quiz_attempt(
        self, user_id: UUID, quiz_attempt_id: UUID
    ) -> dict[str, float]:
        """Mutate ``user_capabilities`` according to the attempt result and
        return ``{dimension: new_score}`` deltas."""
        raise NotImplementedError("planned: P1")

    async def apply_learning_event(
        self, user_id: UUID, learning_event_id: UUID
    ) -> dict[str, float]:
        raise NotImplementedError("planned: P1")
