# Status: [planned]

from typing import Any
from uuid import UUID


async def log_agent_run(
    *,
    workflow_name: str,
    user_id: UUID | str | None,
    agent_id: UUID | str | None,
    skill_id: UUID | str | None,
    parent_run_id: UUID | str | None,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    evidence_chunk_ids: list[UUID | str],
    quality_score: float | None,
    status: str,
    duration_ms: int | None,
    token_usage: dict[str, Any],
) -> None:
    raise NotImplementedError("TODO: persist this call into agent_runs with AsyncSession")
