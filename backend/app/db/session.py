# Status: real

import json
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _json_default(value: Any) -> Any:
    """UUID / datetime aware fallback for ``json.dumps``.

    SQLAlchemy's JSON type binds with ``json.dumps`` under SQLite (and under
    every dialect that doesn't override the bind processor). Without this
    helper, columns like ``agent_runs.evidence_chunk_ids`` (a UUID list mapped
    to JSON via ``with_variant``) raise ``TypeError: UUID not serializable``.
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_serializer(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def init_engine(database_url: str | None = None) -> AsyncEngine:
    global _engine, _sessionmaker
    settings = get_settings()
    _engine = create_async_engine(
        database_url or settings.DATABASE_URL,
        pool_pre_ping=True,
        json_serializer=_json_serializer,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        return init_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
