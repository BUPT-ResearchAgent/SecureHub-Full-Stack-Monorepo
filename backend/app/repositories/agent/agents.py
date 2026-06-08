# Status: real

from collections.abc import Sequence

from sqlalchemy import select

from app.db.models.agent.agent import Agent
from app.repositories.base import UUIDPKRepository


class AgentRepository(UUIDPKRepository[Agent]):
    """P0 methods per task brief §5.2."""

    model = Agent

    async def get_by_name(self, name: str) -> Agent | None:
        result = await self.session.execute(select(Agent).where(Agent.name == name))
        return result.scalar_one_or_none()

    async def list_enabled(self) -> Sequence[Agent]:
        result = await self.session.execute(
            select(Agent).where(Agent.enabled.is_(True)).order_by(Agent.name)
        )
        return result.scalars().all()

    async def list_all(self) -> Sequence[Agent]:
        result = await self.session.execute(select(Agent).order_by(Agent.name))
        return result.scalars().all()
