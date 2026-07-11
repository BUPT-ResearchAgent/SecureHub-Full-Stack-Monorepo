# Status: real

"""AgentRunService — agent_runs 表的唯一写入者（规则 §3.7）。

RuntimeEngine 通过 AgentRunRecorder 调用此 service，记录
workflow / agent / skill / status / duration_ms / token_usage。
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentRunResolutionError(RuntimeError):
    """A strict real run could not resolve its required seeded entities."""


class AgentRunInvalidUserId(ValueError):
    """A real workflow request did not contain a valid UUID user id."""


class AgentRunPrerequisitesUnavailable(RuntimeError):
    """A real workflow's database user, agent, or skill prerequisite is absent."""


class AgentRunService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def normalize_user_id(user_id: UUID | str) -> UUID:
        try:
            return user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        except (TypeError, ValueError) as exc:
            raise AgentRunInvalidUserId("user_id must be a UUID") from exc

    async def ensure_real_workflow_prerequisites(
        self,
        *,
        user_id: UUID | str,
        nodes: Sequence[tuple[str, str, str]],
    ) -> UUID:
        normalized_user_id = self.normalize_user_id(user_id)
        try:
            if await self._resolve_user_id(normalized_user_id) is None:
                raise AgentRunPrerequisitesUnavailable(
                    "real workflow user prerequisite is unavailable"
                )
            for _node_id, agent_name, skill_name in nodes:
                agent_id = await self._resolve_agent_id(agent_name)
                if agent_id is None or await self._resolve_skill_id(agent_id, skill_name) is None:
                    raise AgentRunPrerequisitesUnavailable(
                        "real workflow agent skill prerequisite is unavailable"
                    )
        except AgentRunPrerequisitesUnavailable:
            raise
        except Exception as exc:
            raise AgentRunPrerequisitesUnavailable(
                "real workflow database prerequisites are unavailable"
            ) from exc
        return normalized_user_id

    async def begin_run(
        self,
        *,
        workflow_name: str,
        agent_name: str | None = None,
        skill_name: str | None = None,
        user_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        input_summary: dict[str, Any] | None = None,
        run_id: UUID | None = None,
        require_resolution: bool = False,
        workflow_run_id: UUID | None = None,
        step_attempt_id: UUID | None = None,
        attempt: int | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> UUID:
        """插入一条 status='running' 的 agent_runs 行，返回 run_id。"""
        from app.db.models.agent.agent_run import AgentRun

        agent_id = await self._resolve_agent_id(agent_name)
        skill_id = await self._resolve_skill_id(agent_id, skill_name)
        if require_resolution:
            missing = [
                name
                for name, value in (
                    ("user", user_id and await self._resolve_user_id(user_id)),
                    ("agent", agent_id),
                    ("agent_skill", skill_id),
                )
                if not value
            ]
            if missing:
                raise AgentRunResolutionError(
                    "strict agent_runs resolution failed: " + ", ".join(missing)
                )

        run = AgentRun(
            id=run_id or uuid4(),
            workflow_name=workflow_name,
            user_id=user_id,
            agent_id=agent_id,
            skill_id=skill_id,
            parent_run_id=parent_run_id,
            workflow_run_id=workflow_run_id,
            step_attempt_id=step_attempt_id,
            attempt=attempt,
            provider=provider,
            model=model,
            started_at=datetime.now(timezone.utc),
            input_summary=input_summary or {},
            output_summary={},
            evidence_chunk_ids=[],
            status="running",
            token_usage={},
        )
        self.session.add(run)
        await self.session.flush()
        return run.id

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
        """更新 run 状态为 success，填充输出字段。"""
        from app.db.models.agent.agent_run import AgentRun

        run = await self.session.get(AgentRun, run_id)
        if run is None:
            logger.warning("finish_success: run_id %s not found", run_id)
            return
        resolved_evidence_ids: list[UUID | str] = evidence_chunk_ids or []
        if self.session.bind is not None and self.session.bind.dialect.name == "sqlite":
            resolved_evidence_ids = [str(chunk_id) for chunk_id in resolved_evidence_ids]
        run.status = "success"
        run.output_summary = output_summary
        run.evidence_chunk_ids = resolved_evidence_ids
        run.quality_score = quality_score
        run.duration_ms = duration_ms
        run.token_usage = token_usage or {}
        run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def finish_failed(
        self,
        run_id: UUID,
        *,
        error_summary: dict[str, Any],
        duration_ms: int | None = None,
        error_code: str | None = None,
    ) -> None:
        """更新 run 状态为 failed，填充错误摘要。"""
        from app.db.models.agent.agent_run import AgentRun

        run = await self.session.get(AgentRun, run_id)
        if run is None:
            logger.warning("finish_failed: run_id %s not found", run_id)
            return
        run.status = "failed"
        run.output_summary = error_summary
        run.duration_ms = duration_ms
        run.error_code = error_code or str(error_summary.get("code") or "INTERNAL")
        run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def list_runs(
        self,
        *,
        workflow_name: str | None = None,
        user_id: UUID | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        """查询 agent_runs，返回摘要字典列表（供 B 的 /agent-runs endpoint 使用）。"""
        from app.db.models.agent.agent_run import AgentRun

        stmt = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
        if workflow_name:
            stmt = stmt.where(AgentRun.workflow_name == workflow_name)
        if user_id:
            stmt = stmt.where(AgentRun.user_id == user_id)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "run_id": str(row.id),
                "workflow_name": row.workflow_name,
                "status": row.status,
                "quality_score": row.quality_score,
                "duration_ms": row.duration_ms,
                "evidence_count": len(row.evidence_chunk_ids or []),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _resolve_agent_id(self, agent_name: str | None) -> UUID | None:
        if not agent_name:
            return None
        try:
            from app.db.models.agent.agent import Agent

            result = await self.session.execute(
                select(Agent.id).where(Agent.name == agent_name).limit(1)
            )
            row = result.scalar_one_or_none()
            return row
        except Exception:
            return None

    async def _resolve_skill_id(self, agent_id: UUID | None, skill_name: str | None) -> UUID | None:
        if not agent_id or not skill_name:
            return None
        try:
            from app.db.models.agent.agent_skill import AgentSkill

            result = await self.session.execute(
                select(AgentSkill.id)
                .where(AgentSkill.agent_id == agent_id, AgentSkill.skill_name == skill_name)
                .limit(1)
            )
            resolved = result.scalar_one_or_none()
            if resolved is not None:
                return resolved

            fallback = await self.session.execute(
                select(AgentSkill.id)
                .where(
                    cast(AgentSkill.agent_id, String) == str(agent_id),
                    AgentSkill.skill_name == skill_name,
                )
                .limit(1)
            )
            return fallback.scalar_one_or_none()
        except Exception:
            return None

    async def _resolve_user_id(self, user_id: UUID) -> UUID | None:
        try:
            from app.db.models.identity.user import User

            result = await self.session.execute(
                select(User.id).where(User.id == user_id).limit(1)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None
