# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.agent.agent_run import AgentRun
from app.repositories.base import UUIDPKRepository


class AgentRunRepository(UUIDPKRepository[AgentRun]):
    """P0 methods per task brief §5.2. Every skill writes here through this
    repository — that contract is enforced by rule §3.7 (``ctx.log_run``).
    """

    model = AgentRun

    async def create(
        self,
        *,
        run_id: UUID,
        workflow_name: str,
        status: str = "running",
        user_id: UUID | None = None,
        agent_id: UUID | None = None,
        skill_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        input_summary: dict[str, Any] | None = None,
    ) -> AgentRun:
        row = AgentRun(
            id=run_id,
            workflow_name=workflow_name,
            user_id=user_id,
            agent_id=agent_id,
            skill_id=skill_id,
            parent_run_id=parent_run_id,
            input_summary=input_summary or {},
            output_summary={},
            evidence_chunk_ids=[],
            status=status,
            token_usage={},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def mark_success(
        self,
        run_id: UUID,
        *,
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID] | None = None,
        quality_score: float | None = None,
        duration_ms: int | None = None,
        token_usage: dict[str, Any] | None = None,
    ) -> AgentRun | None:
        row = await self.get_by_id(run_id)
        if row is None:
            return None
        row.status = "success"
        row.output_summary = output_summary
        if evidence_chunk_ids is not None:
            row.evidence_chunk_ids = evidence_chunk_ids
        row.quality_score = quality_score
        row.duration_ms = duration_ms
        if token_usage is not None:
            row.token_usage = token_usage
        await self.session.flush()
        return row

    async def mark_failed(
        self,
        run_id: UUID,
        *,
        output_summary: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> AgentRun | None:
        row = await self.get_by_id(run_id)
        if row is None:
            return None
        row.status = "failed"
        if output_summary is not None:
            row.output_summary = output_summary
        row.duration_ms = duration_ms
        await self.session.flush()
        return row

    async def list_by_workflow(
        self,
        workflow_name: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.workflow_name == workflow_name)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
