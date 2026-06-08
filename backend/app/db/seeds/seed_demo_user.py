# Status: real

"""Idempotent seed for the demo student account, persona, and capability vector."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds._constants import (
    DEMO_USER_CAPABILITIES,
    DEMO_USER_DIMENSIONS,
    DEMO_USER_EMAIL,
    DEMO_USER_ID,
    DEMO_USER_NAME,
)
from app.db.session import get_sessionmaker
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository


async def _seed(session: AsyncSession) -> None:
    users = UserRepository(session)
    profiles = UserProfileRepository(session)
    caps = UserCapabilityRepository(session)

    if await users.get_by_id(DEMO_USER_ID) is None:
        await users.create(
            user_id=DEMO_USER_ID,
            email=DEMO_USER_EMAIL,
            display_name=DEMO_USER_NAME,
            is_active=True,
        )

    await profiles.upsert(user_id=DEMO_USER_ID, dimensions=DEMO_USER_DIMENSIONS)

    for dimension, score, confidence in DEMO_USER_CAPABILITIES:
        await caps.upsert_score(
            user_id=DEMO_USER_ID,
            dimension=dimension,
            score=score,
            confidence=confidence,
            evidence_count=0,
        )


async def run(session: AsyncSession | None = None) -> int:
    if session is not None:
        await _seed(session)
        return len(DEMO_USER_CAPABILITIES)

    sm = get_sessionmaker()
    async with sm() as own_session:
        await _seed(own_session)
        await own_session.commit()
    return len(DEMO_USER_CAPABILITIES)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run())
