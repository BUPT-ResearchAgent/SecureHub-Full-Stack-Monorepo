# Status: real

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.seeds.seed_smoke import seed_smoke
from app.db.session import get_sessionmaker


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


async def ensure_sqlite_schema(session) -> None:
    connection = await session.connection()
    if connection.dialect.name != "sqlite":
        return
    existing = await connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    )
    if existing.first() is None:
        await connection.run_sync(Base.metadata.create_all)


async def main() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await ensure_sqlite_schema(session)
        await seed_smoke(session)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
