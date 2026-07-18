# Status: real

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.runtime.capability_manifest import register_agents
from app.core.config import get_settings
from app.db.session import dispose_engines, get_sessionmaker
from app.runtime.skill_catalog import (
    assert_persisted_catalog_integrity,
    build_production_skill_catalog,
)
from app.runtime.supervisor import RuntimeSupervisor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    register_agents()
    supervisor: RuntimeSupervisor | None = None
    if get_settings().RUNTIME_SUPERVISOR_ENABLED:
        # Production workers cannot start against a drifted enabled DB catalog.
        # The database remains the audited catalog mirror while source owns the
        # executable SkillDefinition objects.
        async with get_sessionmaker()() as session:
            await assert_persisted_catalog_integrity(
                session,
                build_production_skill_catalog(),
            )
        supervisor = RuntimeSupervisor()
        await supervisor.start()
        app.state.runtime_supervisor = supervisor
    try:
        yield
    finally:
        try:
            if supervisor is not None:
                await supervisor.stop()
        finally:
            await dispose_engines()
