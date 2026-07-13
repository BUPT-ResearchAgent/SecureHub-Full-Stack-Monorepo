from app.db.session import _async_database_url


def test_async_session_normalises_plain_postgresql_urls() -> None:
    assert _async_database_url("postgresql://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("postgres://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("postgresql+asyncpg://user:pass@db.example/app") == "postgresql+asyncpg://user:pass@db.example/app"
    assert _async_database_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"
