# Status: partial-real

"""``GET /api/v1/resources`` + ``GET /api/v1/resources/{resource_id}``.

The actual write path lives in ``courses.generate_resource`` (SSE); this
module is the read-only retrieval side a frontend page would call after the
``done`` SSE event lands.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import SessionDep
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.schemas.resource import GeneratedResourceListOut, GeneratedResourceOut

router = APIRouter()


def _to_out(row) -> GeneratedResourceOut:
    return GeneratedResourceOut(
        id=row.id,
        resource_type=row.resource_type,
        title=row.title,
        user_id=row.user_id,
        course_id=row.course_id,
        kp_id=row.kp_id,
        agent_run_id=row.agent_run_id,
        content=row.content or {},
        object_key=row.object_key,
        evidence_chunk_ids=row.evidence_chunk_ids or [],
        quality_score=row.quality_score,
        status=row.status,
        metadata=row.metadata_ or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/resources", response_model=GeneratedResourceListOut)
async def list_resources(
    session: SessionDep,
    course_id: UUID | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> GeneratedResourceListOut:
    repo = GeneratedResourceRepository(session)
    items = await repo.list_by_user_course(
        user_id=user_id,
        course_id=course_id,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )
    return GeneratedResourceListOut(
        items=[_to_out(row) for row in items],
        total=len(items),
    )


@router.get("/resources/{resource_id}", response_model=GeneratedResourceOut)
async def get_resource(
    resource_id: UUID, session: SessionDep
) -> GeneratedResourceOut:
    repo = GeneratedResourceRepository(session)
    row = await repo.get_by_id(resource_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="resource not found"
        )
    return _to_out(row)


__all__ = ["router"]
