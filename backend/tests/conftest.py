# Status: real

import pytest
from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.db import models  # noqa: F401
from app.db.base import Base
from app.main import app


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


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_xfyun() -> None:
    return None


@pytest.fixture
def seeded_kg() -> None:
    return None


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
    await engine.dispose()
