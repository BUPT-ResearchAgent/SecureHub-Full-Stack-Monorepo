import pytest

import app.db.session as session_module
from app.core.config import Settings
from app.db.session import _async_database_url


def test_async_session_normalises_plain_postgresql_urls() -> None:
    assert _async_database_url("postgresql://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("postgres://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("postgresql+asyncpg://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"


@pytest.mark.anyio
async def test_postgresql_engine_applies_bounded_pool_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        DATABASE_POOL_SIZE=2,
        DATABASE_MAX_OVERFLOW=3,
        DATABASE_POOL_TIMEOUT_SECONDS=4.0,
    )
    monkeypatch.setattr(session_module, "get_settings", lambda: settings)

    engine = session_module.init_engine(
        "postgresql+asyncpg://pool_user:pool_password@127.0.0.1:5432/pool_test"
    )
    try:
        pool = engine.sync_engine.pool
        assert pool.size() == 2  # type: ignore[attr-defined]
        assert pool._max_overflow == 3  # type: ignore[attr-defined]
        assert pool._timeout == 4.0  # type: ignore[attr-defined]
    finally:
        await engine.dispose()
        session_module._engine = None
        session_module._sessionmaker = None


@pytest.mark.anyio
async def test_api_risk_engine_uses_a_separate_non_overflowing_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        API_RISK_AUDIT_POOL_SIZE=6,
        DATABASE_POOL_TIMEOUT_SECONDS=4.0,
    )
    monkeypatch.setattr(session_module, "get_settings", lambda: settings)

    engine = session_module.init_audit_engine(
        "postgresql+asyncpg://pool_user:pool_password@127.0.0.1:5432/audit_pool_test"
    )
    try:
        pool = engine.sync_engine.pool
        assert pool.size() == 6  # type: ignore[attr-defined]
        assert pool._max_overflow == 0  # type: ignore[attr-defined]
        assert pool._timeout == 4.0  # type: ignore[attr-defined]
    finally:
        await engine.dispose()
        session_module._audit_engine = None
        session_module._audit_sessionmaker = None
