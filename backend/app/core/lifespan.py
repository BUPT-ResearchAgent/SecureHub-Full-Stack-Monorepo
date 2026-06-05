# Status: [planned]

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.runtime.capability_manifest import register_agents


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    register_agents()
    yield
