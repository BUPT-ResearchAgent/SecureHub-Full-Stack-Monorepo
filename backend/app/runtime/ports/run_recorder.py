# Status: real

"""Runtime Port that records one accepted Skill invocation in ``agent_runs``."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession


class RunRecordingError(RuntimeError):
    code = "AGENT_RUN_PERSIST_FAILED"


class AgentRunRecorder:
    """Thin port over AgentRunService with v1.1 root/step correlation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(
        self,
        *,
        workflow_run_id: UUID,
        step_attempt_id: UUID,
        workflow_name: str,
        user_id: UUID | str | None,
        agent_name: str,
        skill_name: str,
        attempt: int,
        provider: str | None,
        model: str | None,
        input_summary: dict[str, Any],
        require_resolution: bool,
    ) -> UUID:
        if user_id is None:
            raise RunRecordingError("accepted runtime skill call requires user identity")
        from app.services.agent.agent_run_service import AgentRunService

        try:
            run_id = uuid4()
            stored = await AgentRunService(self._session).begin_run(
                run_id=run_id,
                workflow_name=workflow_name,
                agent_name=agent_name,
                skill_name=skill_name,
                user_id=AgentRunService.normalize_user_id(user_id),
                input_summary=input_summary,
                require_resolution=require_resolution,
                workflow_run_id=workflow_run_id,
                step_attempt_id=step_attempt_id,
                attempt=attempt,
                provider=provider,
                model=model,
            )
            if stored != run_id:
                raise RunRecordingError("agent_runs primary key mismatch")
            return stored
        except RunRecordingError:
            raise
        except Exception as exc:
            raise RunRecordingError("unable to persist running agent_runs record") from exc

    async def succeed(
        self,
        agent_run_id: UUID,
        *,
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID],
        quality_score: float | None,
        duration_ms: int | None,
        token_usage: dict[str, Any],
    ) -> None:
        from app.services.agent.agent_run_service import AgentRunService

        try:
            await AgentRunService(self._session).finish_success(
                agent_run_id,
                output_summary=output_summary,
                evidence_chunk_ids=evidence_chunk_ids,
                quality_score=quality_score,
                duration_ms=duration_ms,
                token_usage=token_usage,
            )
        except Exception as exc:
            raise RunRecordingError("unable to persist successful agent run") from exc

    async def fail(
        self,
        agent_run_id: UUID,
        *,
        error_code: str,
        error_summary: dict[str, Any],
        duration_ms: int | None,
    ) -> None:
        from app.services.agent.agent_run_service import AgentRunService

        try:
            await AgentRunService(self._session).finish_failed(
                agent_run_id,
                error_summary=error_summary,
                duration_ms=duration_ms,
                error_code=error_code,
            )
        except Exception as exc:
            raise RunRecordingError("unable to converge failed agent run") from exc


__all__ = ["AgentRunRecorder", "RunRecordingError"]
