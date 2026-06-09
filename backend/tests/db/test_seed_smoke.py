# Status: real

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.auth.security import verify_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.agent.agent import Agent
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.seeds._constants import DEMO_USER_EMAIL, DEMO_USER_PASSWORD
from app.db.seeds.seed_smoke import USER_DEMO_ID, seed_smoke


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # type: ignore[no-untyped-def]
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element, _compiler, **_kw):  # type: ignore[no-untyped-def]
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(_element, _compiler, **_kw):  # type: ignore[no-untyped-def]
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(_element, _compiler, **_kw):  # type: ignore[no-untyped-def]
    return "BLOB"


@pytest.mark.anyio
async def test_seed_smoke_is_idempotent_and_has_core_counts() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        await seed_smoke(session)
        await session.commit()
        await seed_smoke(session)
        await session.commit()

        agents = (await session.execute(select(Agent))).scalars().all()
        capabilities = (
            await session.execute(
                select(UserCapability).where(UserCapability.user_id == USER_DEMO_ID)
            )
        ).scalars().all()
        nodes = (await session.execute(select(KnowledgeNode))).scalars().all()
        chunks = (await session.execute(select(Chunk))).scalars().all()
        demo_user = (
            await session.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        smoke_user = await session.get(User, USER_DEMO_ID)

    await engine.dispose()

    assert len(agents) == 9
    assert len(capabilities) == 6
    assert len(nodes) == 3
    assert len(chunks) == 10
    assert demo_user is not None
    assert verify_password(DEMO_USER_PASSWORD, demo_user.hashed_password)
    assert smoke_user is not None
    assert verify_password(DEMO_USER_PASSWORD, smoke_user.hashed_password)
