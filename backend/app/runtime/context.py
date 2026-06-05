# Status: [planned]

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.runtime.logger import log_agent_run


@dataclass
class RunContext:
    user_id: str | None = None
    workflow_name: str = "course_learning"
    persona_summary: str = ""
    stream: bool = False
    config: Any = field(default_factory=get_settings)
    parent_run_id: UUID | str | None = None

    async def log_run(
        self,
        *,
        agent_id: UUID | str | None = None,
        skill_id: UUID | str | None = None,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID | str],
        quality_score: float | None = None,
        status: str = "success",
        duration_ms: int | None = None,
        token_usage: dict[str, Any] | None = None,
    ) -> None:
        await log_agent_run(
            workflow_name=self.workflow_name,
            user_id=self.user_id,
            agent_id=agent_id,
            skill_id=skill_id,
            parent_run_id=self.parent_run_id,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_chunk_ids=evidence_chunk_ids,
            quality_score=quality_score,
            status=status,
            duration_ms=duration_ms,
            token_usage=token_usage or {},
        )
