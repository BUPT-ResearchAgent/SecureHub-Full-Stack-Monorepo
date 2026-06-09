# Status: real

"""Entry point that runs every demo seeder in dependency order.

Run via ``python -m app.db.seeds.seed_demo`` after ``alembic upgrade head``.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds import seed_agent_skills as seed_agent_skills_mod
from app.db.seeds import seed_agents as seed_agents_mod
from app.db.seeds import seed_course_websec as seed_course_websec_mod
from app.db.seeds import seed_demo_user as seed_demo_user_mod
from app.db.session import get_sessionmaker


async def _run(session: AsyncSession) -> dict[str, object]:
    # Agents / skills first — other seeds may FK-soft-reference them.
    agent_count = await seed_agents_mod(session=session)
    skill_count = await seed_agent_skills_mod(session=session)
    capability_count = await seed_demo_user_mod(session=session)
    course_stats = await seed_course_websec_mod(session=session)
    return {
        "agents": agent_count,
        "skills": skill_count,
        "user_capabilities": capability_count,
        **course_stats,
    }


async def run() -> dict[str, object]:
    sm = get_sessionmaker()
    async with sm() as session:
        stats = await _run(session)
        await session.commit()
    return stats


if __name__ == "__main__":  # pragma: no cover
    stats = asyncio.run(run())
    print("seed_demo done:", stats)
