# Status: real

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_audit_engine: AsyncEngine | None = None
_audit_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _async_database_url(value: str) -> str:
    """Accept a standard PostgreSQL URL while keeping AsyncSession fail-closed."""
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
    if value.startswith("postgres://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgres://")
    return value


def init_engine(database_url: str | None = None) -> AsyncEngine:
    global _engine, _sessionmaker
    settings = get_settings()
    resolved_url = _async_database_url(database_url or settings.DATABASE_URL)
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if not resolved_url.startswith("sqlite"):
        engine_options.update(
            {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT_SECONDS,
            }
        )
    _engine = create_async_engine(
        resolved_url,
        **engine_options,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def init_audit_engine(database_url: str | None = None) -> AsyncEngine:
    """Create the bounded pool reserved for fail-closed API-risk writes."""

    global _audit_engine, _audit_sessionmaker
    settings = get_settings()
    resolved_url = _async_database_url(database_url or settings.DATABASE_URL)
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if not resolved_url.startswith("sqlite"):
        engine_options.update(
            {
                "pool_size": settings.API_RISK_AUDIT_POOL_SIZE,
                "max_overflow": 0,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT_SECONDS,
            }
        )
    _audit_engine = create_async_engine(resolved_url, **engine_options)
    _audit_sessionmaker = async_sessionmaker(_audit_engine, expire_on_commit=False)
    return _audit_engine


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


def get_audit_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _audit_sessionmaker
    if _audit_sessionmaker is None:
        init_audit_engine()
    assert _audit_sessionmaker is not None
    return _audit_sessionmaker


async def dispose_engines() -> None:
    """Dispose both independently bounded pools during application shutdown."""

    global _engine, _sessionmaker, _audit_engine, _audit_sessionmaker
    engines = [engine for engine in (_engine, _audit_engine) if engine is not None]
    for index, engine in enumerate(engines):
        if all(engine is not previous for previous in engines[:index]):
            await engine.dispose()
    _engine = None
    _sessionmaker = None
    _audit_engine = None
    _audit_sessionmaker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
