# Status: partial-real

"""Course catalogue + knowledge-map + SSE-based resource generation.

P0 surface:
- ``GET    /courses``                           — list courses
- ``GET    /courses/{course_id}``               — single course detail
- ``GET    /courses/{course_id}/knowledge-map`` — full {nodes, edges} graph
- ``POST   /courses/{course_id}/resources/generate`` — 5-event SSE stream
- ``POST   /courses/{course_id}/plan`` (legacy, still NotImplementedError)
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.models.agent.agent import Agent as AgentRow
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.deps import CurrentUserDep, SessionDep
from app.repositories.agent.agent_runs import AgentRunRepository
from app.repositories.knowledge.courses import CourseRepository
from app.repositories.knowledge.knowledge_graph import KnowledgeGraphRepository
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.schemas.knowledge import (
    CourseListOut,
    CourseOut,
    KnowledgeEdgeOut,
    KnowledgeMapOut,
    KnowledgeNodeOut,
)
from app.streaming.events import (
    DoneEvent,
    EvidenceEvent,
    ProgressEvent,
    SSEEvent,
    TokenEvent,
)
from app.streaming.sse import sse_response

router = APIRouter()

ResourceType = Literal[
    "doc", "ppt", "mindmap", "quiz", "lab", "video", "reading_list"
]

# Map the request ``type`` to the corresponding generated_resources.resource_type
# slug + the doc_archivist skill that owns it (per AGENTS.md §7).
_RESOURCE_SLUG: dict[str, tuple[str, str]] = {
    "doc": ("course_doc", "GenerateCourseDoc"),
    "ppt": ("course_ppt", "GenerateCoursePPT"),
    "mindmap": ("mindmap", "GenerateMindmap"),
    "quiz": ("quiz_set", "GenerateQuiz"),
    "lab": ("hands_on_lab", "GenerateHandsOnLab"),
    "video": ("video_storyboard", "GenerateVideoStoryboard"),
    "reading_list": ("reading_list", "RecommendReadings"),
}


# ---------------- legacy planning endpoint ----------------

class CoursePlanRequest(BaseModel):
    user_id: str
    selected_kp_ids: list[str] = Field(default_factory=list)
    time_budget_hours: int | None = None


class CoursePlanResponse(BaseModel):
    task_id: str
    status: str


@router.post("/courses/{course_id}/plan", response_model=CoursePlanResponse)
async def plan_learning_path(
    course_id: str, payload: CoursePlanRequest
) -> CoursePlanResponse:
    raise NotImplementedError("TODO: enqueue task_orchestrator.GenerateLearningPath")


# ---------------- v2 read endpoints ----------------

@router.get("/courses", response_model=CourseListOut)
async def list_courses(
    session: SessionDep,
    domain: str | None = Query(default=None, description="Filter by domain slug"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CourseListOut:
    repo = CourseRepository(session)
    if domain is not None:
        items = await repo.list_by_domain(domain, limit=limit, offset=offset)
    else:
        items = await repo.list_all(limit=limit, offset=offset)
    return CourseListOut(
        items=[
            CourseOut(
                id=row.id,
                code=row.code,
                title=row.title,
                domain=row.domain,
                description=row.description,
            )
            for row in items
        ],
        total=len(items),
    )


@router.get("/courses/{course_id}", response_model=CourseOut)
async def get_course(course_id: UUID, session: SessionDep) -> CourseOut:
    repo = CourseRepository(session)
    row = await repo.get_by_id(course_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="course not found")
    return CourseOut(
        id=row.id,
        code=row.code,
        title=row.title,
        domain=row.domain,
        description=row.description,
    )


@router.get(
    "/courses/{course_id}/knowledge-map",
    response_model=KnowledgeMapOut,
)
async def get_knowledge_map(
    course_id: UUID, session: SessionDep
) -> KnowledgeMapOut:
    courses_repo = CourseRepository(session)
    if await courses_repo.get_by_id(course_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="course not found")

    graph = KnowledgeGraphRepository(session)
    nodes = await graph.list_nodes(course_id=course_id, limit=500)
    node_ids = {n.id for n in nodes}
    # Pull all edges and filter to the course subgraph in Python — keeps the
    # repo abstraction narrow (no per-course edge query needed yet).
    all_edges = (await session.execute(select(KnowledgeEdge))).scalars().all()
    edges = [e for e in all_edges if e.source_id in node_ids and e.target_id in node_ids]
    return KnowledgeMapOut(
        course_id=course_id,
        nodes=[
            KnowledgeNodeOut(
                id=n.id,
                name=n.name,
                node_type=n.node_type,
                level=n.level,
                description=n.description,
                metadata=n.metadata_ or {},
            )
            for n in nodes
        ],
        edges=[
            KnowledgeEdgeOut(
                source_id=e.source_id,
                target_id=e.target_id,
                edge_type=e.edge_type,
                weight=e.weight,
            )
            for e in edges
        ],
    )


# ---------------- v2 SSE generation endpoint ----------------

async def _resource_event_stream(
    *,
    session,
    course_id: UUID,
    resource_type_param: ResourceType,
    user_id: UUID,
) -> AsyncIterator[SSEEvent]:
    """Stub SSE pipeline:

    1. ``progress`` retrieving → look up the doc_archivist agent + skill
    2. open an ``agent_runs`` row
    3. ``evidence`` for up to 3 ``ready`` chunks of this domain
    4. ``progress`` generating → emit 3 short ``token`` events (placeholder)
    5. ``progress`` evaluating → write a ``generated_resources`` stub row
    6. ``done`` carrying ``resource_id``
    """
    slug, skill_name = _RESOURCE_SLUG[resource_type_param]
    started_at = datetime.now(timezone.utc)

    # Locate course → domain.
    course_repo = CourseRepository(session)
    course = await course_repo.get_by_id(course_id)
    if course is None:
        yield ProgressEvent(
            node_name="bootstrap", status="failed", percentage=0
        )
        return
    domain = course.domain

    # Locate doc_archivist for the agent_id field of the run row.
    agent_row = (
        await session.execute(select(AgentRow).where(AgentRow.name == "doc_archivist"))
    ).scalar_one_or_none()

    # 1. retrieving
    yield ProgressEvent(
        node_name="retrieving",
        status="running",
        agent_id=str(agent_row.id) if agent_row else None,
        skill_id=None,
        percentage=10,
    )

    # 2. open agent_runs row
    runs_repo = AgentRunRepository(session)
    run_id = uuid4()
    await runs_repo.create(
        run_id=run_id,
        workflow_name="course_learning",
        status="running",
        user_id=user_id,
        agent_id=agent_row.id if agent_row else None,
        input_summary={
            "course_id": str(course_id),
            "resource_type": resource_type_param,
            "skill": skill_name,
        },
    )
    await session.commit()

    # 3. evidence — surface a few ``ready`` chunks if any; otherwise the
    # pending demo set still gets sampled by chunk_index so the UI has
    # something to render.
    chunks = (
        await session.execute(
            select(Chunk)
            .where(Chunk.domain == domain)
            .order_by(Chunk.chunk_index)
            .limit(3)
        )
    ).scalars().all()
    evidence_chunk_ids: list[UUID] = []
    for ch in chunks:
        evidence_chunk_ids.append(ch.id)
        excerpt = ch.chunk_text if len(ch.chunk_text) <= 160 else ch.chunk_text[:160] + "…"
        yield EvidenceEvent(
            chunk_id=str(ch.id),
            source=f"chunk:{ch.id}",
            excerpt=excerpt,
            reliability=0.9,
        )
        await asyncio.sleep(0)

    # 4. generating — placeholder token stream.
    yield ProgressEvent(
        node_name="generating",
        status="running",
        agent_id=str(agent_row.id) if agent_row else None,
        skill_id=None,
        percentage=60,
    )
    for piece in (
        f"# {course.title} · {resource_type_param.upper()} 占位\n\n",
        "本文档由 doc_archivist 智能体生成（演示桩）。\n\n",
        "真讯飞星火接入后会替换为基于上方证据的真实回答。",
    ):
        yield TokenEvent(content=piece)
        await asyncio.sleep(0)

    # 5. evaluating → write generated_resources row.
    yield ProgressEvent(
        node_name="evaluating", status="running", percentage=85
    )
    resource_id = uuid4()
    resources_repo = GeneratedResourceRepository(session)
    await resources_repo.create(
        resource_id=resource_id,
        resource_type=slug,
        title=f"{course.title} · {resource_type_param}",
        user_id=user_id,
        course_id=course_id,
        agent_run_id=run_id,
        content={"placeholder": True},
        evidence_chunk_ids=evidence_chunk_ids,
        quality_score=0.7,
        status="ready",
        metadata={"skill_name": skill_name},
    )
    duration_ms = int(
        (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
    )
    await runs_repo.mark_success(
        run_id,
        output_summary={"resource_id": str(resource_id)},
        evidence_chunk_ids=evidence_chunk_ids,
        quality_score=0.7,
        duration_ms=duration_ms,
        token_usage={"prompt": 0, "completion": 0, "model": "stub"},
    )
    await session.commit()

    # 6. done
    yield ProgressEvent(node_name="evaluating", status="success", percentage=100)
    yield DoneEvent(
        run_id=str(run_id),
        final_output_ref=str(resource_id),
        quality_score=0.7,
    )


@router.post("/courses/{course_id}/resources/generate")
async def generate_resource(
    course_id: UUID,
    session: SessionDep,
    user_id: CurrentUserDep,
    type: ResourceType = Query(...),
):
    if type not in _RESOURCE_SLUG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported type: {type}",
        )

    async def _bus() -> AsyncIterator[SSEEvent]:
        async for event in _resource_event_stream(
            session=session,
            course_id=course_id,
            resource_type_param=type,
            user_id=user_id,
        ):
            yield event

    return sse_response(_bus())


# Backwards compat: GET /courses/{cid}/resources/generate also works for
# ``curl -N`` smoke tests (CLAUDE.md §5).
@router.get("/courses/{course_id}/resources/generate")
async def generate_resource_get(
    course_id: UUID,
    session: SessionDep,
    user_id: CurrentUserDep,
    type: ResourceType = Query(...),
):
    return await generate_resource(
        course_id=course_id, session=session, user_id=user_id, type=type
    )


__all__ = ["router"]
