from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent_runs,
    agents,
    courses,
    ctftime,
    health,
    placeholder,
    policy,
    profile,
    rag,
    research,
    resources,
    streaming,
    system,
)

api_router = APIRouter()

# Real / mock endpoints (挑战杯 demo surface, untouched per CLAUDE.md §10).
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(placeholder.router, prefix="/placeholder", tags=["placeholder"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(ctftime.router, prefix="/ctftime", tags=["ctftime"])
api_router.include_router(policy.router, prefix="/policy", tags=["policy"])

# Data-layer v2 partial-real endpoints (A3 P0 surface).
api_router.include_router(profile.router, tags=["profile"])
api_router.include_router(courses.router, tags=["courses"])
api_router.include_router(resources.router, tags=["resources"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(agent_runs.router, tags=["agent-runs"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(streaming.router, tags=["streaming"])
