# Status: partial-real

"""``GET /api/v1/agent-runs`` + ``GET /api/v1/agent-runs/{run_id}``.

Powers the "agent activity" trace visualisation panel referenced in AGENTS.md
§7.1 and CLAUDE.md §2.7. Read-only — the write path is owned by
``AgentRunService`` (planned) and the SSE generation pipeline.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import SessionDep
from app.repositories.agent.agent_runs import AgentRunRepository
from app.schemas.agent import AgentRunListOut, AgentRunOut

router = APIRouter()


def _to_out(row) -> AgentRunOut:
    return AgentRunOut(
        id=row.id,
        workflow_name=row.workflow_name,
        agent_id=row.agent_id,
        skill_id=row.skill_id,
        user_id=row.user_id,
        parent_run_id=row.parent_run_id,
        status=row.status,
        input_summary=row.input_summary or {},
        output_summary=row.output_summary or {},
        evidence_chunk_ids=list(row.evidence_chunk_ids or []),
        quality_score=row.quality_score,
        duration_ms=row.duration_ms,
        created_at=row.created_at,
    )


@router.get("/agent-runs", response_model=AgentRunListOut)
async def list_agent_runs(
    session: SessionDep,
    workflow_name: str | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AgentRunListOut:
    repo = AgentRunRepository(session)
    if workflow_name is not None:
        rows = await repo.list_by_workflow(workflow_name, limit=limit, offset=offset)
    elif user_id is not None:
        rows = await repo.list_by_user(user_id, limit=limit, offset=offset)
    else:
        # No filter ⇒ default to course_learning, the A3 demo workflow.
        rows = await repo.list_by_workflow("course_learning", limit=limit, offset=offset)
    return AgentRunListOut(
        items=[_to_out(row) for row in rows],
        total=len(rows),
    )


@router.get("/agent-runs/{run_id}", response_model=AgentRunOut)
async def get_agent_run(run_id: UUID, session: SessionDep) -> AgentRunOut:
    repo = AgentRunRepository(session)
    row = await repo.get_by_id(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found"
        )
    return _to_out(row)


__all__ = ["router"]
