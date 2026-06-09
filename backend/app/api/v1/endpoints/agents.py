# Status: partial-real

"""``GET /api/v1/agents`` — list the 9 canonical agents."""

from fastapi import APIRouter

from app.deps import SessionDep
from app.repositories.agent.agents import AgentRepository
from app.schemas.agent import AgentListOut, AgentOut

router = APIRouter()


@router.get("/agents", response_model=AgentListOut)
async def list_agents(session: SessionDep) -> AgentListOut:
    repo = AgentRepository(session)
    rows = await repo.list_all()
    return AgentListOut(
        items=[
            AgentOut(
                id=row.id,
                name=row.name,
                role_description=row.role_description,
                risk_level=row.risk_level,
                tools=list(row.tools or []),
                enabled=row.enabled,
            )
            for row in rows
        ],
        total=len(rows),
    )


__all__ = ["router"]
