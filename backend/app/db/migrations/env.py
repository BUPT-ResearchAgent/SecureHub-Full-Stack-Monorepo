# Status: [planned]

"""Alembic environment with a SQLite fallback.

Both v1 and v2 migrations target PostgreSQL + pgvector in production, but the
local dev / CI loop must be able to run ``alembic upgrade head`` against a
SQLite file (``DATABASE_URL=sqlite+aiosqlite:///...``) without spinning up
Postgres. To keep those PG-only types compatible, this module registers
``@compiles(<type>, "sqlite")`` fallbacks for ``Vector`` / ``JSONB`` / ``ARRAY``
/ ``UUID`` so SQLAlchemy emits the closest SQLite-native column type instead of
failing with ``CompileError``.

Migrations that wrap pgvector indexes (HNSW / IVFFlat) or ``CREATE EXTENSION
vector`` must additionally guard those calls with
``op.get_bind().dialect.name == "postgresql"`` — the v1 ``20260610_0900_init``
migration is patched accordingly; every v2 migration does the same.
"""

import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles

from app.core.config import get_settings
from app.db import models  # noqa: F401  — populate Base.metadata
from app.db.base import Base

try:  # pgvector is a hard dependency; the import is wrapped only to make this
    # file safe when running with a stripped-down test environment.
    from pgvector.sqlalchemy import Vector

    _HAS_PGVECTOR = True
except ImportError:  # pragma: no cover — pyproject pins pgvector
    Vector = None  # type: ignore[assignment]
    _HAS_PGVECTOR = False


# ---------------------------------------------------------------------------
# SQLite fallbacks for PostgreSQL-only column types
# ---------------------------------------------------------------------------
# SQLAlchemy compiler dispatch is per (type, dialect_name); registering these
# only affects the SQLite backend, so production PG behaviour is unchanged.

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "CHAR(36)"


if _HAS_PGVECTOR:

    @compiles(Vector, "sqlite")  # type: ignore[arg-type]
    def _compile_vector_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
        return "BLOB"


# ---------------------------------------------------------------------------
# Alembic boilerplate
# ---------------------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


_ASYNC_DRIVER_RE = re.compile(r"\+(?:asyncpg|aiosqlite|aiomysql|asyncmy)")


def _sync_url(url: str) -> str:
    """Strip ``+asyncpg`` / ``+aiosqlite`` / etc. so Alembic can use a sync engine."""
    return _ASYNC_DRIVER_RE.sub("", url)


def get_url() -> str:
    return _sync_url(get_settings().DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
