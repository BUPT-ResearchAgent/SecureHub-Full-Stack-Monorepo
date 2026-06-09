# Status: planned

"""Per task brief §6.3 — AgentRunService is the **only** writer of
``agent_runs`` rows. Every skill calls into it via ``ctx.log_run`` (rule §3.7).
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class AgentRunService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def begin_run(
        self,
        *,
        workflow_name: str,
        agent_name: str | None = None,
        skill_name: str | None = None,
        user_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        input_summary: dict[str, Any] | None = None,
    ) -> UUID:
        raise NotImplementedError("planned: P0")

    async def finish_success(
        self,
        run_id: UUID,
        *,
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID] | None = None,
        quality_score: float | None = None,
        duration_ms: int | None = None,
        token_usage: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError("planned: P0")

    async def finish_failed(
        self,
        run_id: UUID,
        *,
        error_summary: dict[str, Any],
        duration_ms: int | None = None,
    ) -> None:
        raise NotImplementedError("planned: P0")

    async def list_runs(
        self,
        *,
        workflow_name: str | None = None,
        user_id: UUID | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        raise NotImplementedError("planned: P0")
