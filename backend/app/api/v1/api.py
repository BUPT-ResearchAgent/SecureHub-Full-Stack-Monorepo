from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent_control,
    agents,
    admin,
    assessment,
    auth,
    benchmarks,
    courses,
    course_updates,
    ctftime,
    education,
    fairness,
    fund_recommendations,
    health,
    llm,
    messages,
    placeholder,
    policy,
    profile,
    provider_credentials,
    rag,
    research,
    resources,
    security,
    system,
    teaching,
    tutor,
    teacher,
    uploads,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(security.router, tags=["security-governance"])
api_router.include_router(fairness.router, tags=["fairness-governance"])
api_router.include_router(benchmarks.router, tags=["benchmarks"])
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
api_router.include_router(fund_recommendations.router, tags=["fund-recommendations"])
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
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(messages.router, tags=["messages"])
api_router.include_router(course_updates.router, tags=["course-updates"])
api_router.include_router(teacher.router, tags=["teacher"])
api_router.include_router(education.router, tags=["education"])
api_router.include_router(teaching.router, tags=["teaching"])
api_router.include_router(provider_credentials.router, tags=["provider-credentials"])
api_router.include_router(courses.router, tags=["courses"])
api_router.include_router(resources.router, tags=["resources"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(agent_control.router, tags=["agent-control"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(tutor.router, tags=["tutor"])
api_router.include_router(assessment.router, tags=["assessment"])
api_router.include_router(llm.router, tags=["llm"])
api_router.include_router(uploads.router, tags=["uploads"])
