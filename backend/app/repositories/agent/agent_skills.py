# Status: real

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.db.models.agent.agent_skill import AgentSkill
from app.repositories.base import UUIDPKRepository


class AgentSkillRepository(UUIDPKRepository[AgentSkill]):
    """P0 methods per task brief §5.2."""

    model = AgentSkill

    async def get_enabled_skill(
        self, agent_id: UUID, skill_name: str
    ) -> AgentSkill | None:
        """Return the highest-version enabled skill row matching the name."""
        stmt = (
            select(AgentSkill)
            .where(
                AgentSkill.agent_id == agent_id,
                AgentSkill.skill_name == skill_name,
                AgentSkill.enabled.is_(True),
            )
            .order_by(AgentSkill.version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_agent(
        self, agent_id: UUID, *, enabled_only: bool = True
    ) -> Sequence[AgentSkill]:
        stmt = select(AgentSkill).where(AgentSkill.agent_id == agent_id)
        if enabled_only:
            stmt = stmt.where(AgentSkill.enabled.is_(True))
        stmt = stmt.order_by(AgentSkill.skill_name, AgentSkill.version.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
