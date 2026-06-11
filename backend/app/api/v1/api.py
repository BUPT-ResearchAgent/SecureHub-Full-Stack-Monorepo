from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    assessment,
    courses,
    ctftime,
    health,
    placeholder,
    policy,
    profile,
    rag,
    research,
    streaming,
    system,
    tutor,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(
    placeholder.router,
    prefix="/placeholder",
    tags=["placeholder"],
)
api_router.include_router(
    research.router,
    prefix="/research",
    tags=["research"],
)
api_router.include_router(
    ctftime.router,
    prefix="/ctftime",
    tags=["ctftime"],
)
api_router.include_router(
    policy.router,
    prefix="/policy",
    tags=["policy"],
)
api_router.include_router(profile.router, tags=["profile"])
api_router.include_router(courses.router, tags=["courses"])
api_router.include_router(streaming.router, tags=["streaming"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(tutor.router, tags=["tutor"])
api_router.include_router(assessment.router, tags=["assessment"])
