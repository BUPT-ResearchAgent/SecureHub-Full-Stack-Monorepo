# Status: partial-real

"""``GET /api/v1/resources`` + ``GET /api/v1/resources/{resource_id}``.

The actual write path lives in ``courses.generate_resource`` (SSE); this
module is the read-only retrieval side a frontend page would call after the
``done`` SSE event lands.
"""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from app.api.v1.endpoints.workflow_adapter import accepted_root_response, start_product_workflow, workflow_service
from app.deps import CurrentUserDep, SessionDep
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.schemas.agent_control import WorkflowRunStartResponse
from app.schemas.resource import (
    GeneratedResourceListOut,
    GeneratedResourceOut,
    GeneratedResourceRetryRequest,
)
from app.services.workflow_application_service import WorkflowApplicationService

router = APIRouter()


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


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
    current_user_id: CurrentUserDep,
    course_id: UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> GeneratedResourceListOut:
    repo = GeneratedResourceRepository(session)
    items = await repo.list_by_user_course(
        # The authenticated/demo identity is authoritative.  A query argument
        # must never let a learner enumerate another user's artifacts.
        user_id=current_user_id,
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
    resource_id: UUID, session: SessionDep, current_user_id: CurrentUserDep
) -> GeneratedResourceOut:
    repo = GeneratedResourceRepository(session)
    row = await repo.get_by_id(resource_id)
    if row is None or row.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="resource not found"
        )
    return _to_out(row)


@router.post(
    "/resources/{resource_id}/retry",
    response_model=WorkflowRunStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_resource(
    resource_id: UUID,
    payload: GeneratedResourceRetryRequest,
    request: Request,
    session: SessionDep,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Regenerate one owned artifact without replaying its fan-out root."""
    repo = GeneratedResourceRepository(session)
    row = await repo.get_by_id(resource_id)
    if row is None or row.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    if row.course_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RESOURCE_RETRY_UNAVAILABLE", "message": "resource has no course lineage"},
        )

    options = dict(payload.options or {})
    # Parent lineage is established only from the owned persisted resource,
    # not caller-provided IDs.  The new root's immutable input links it to the
    # source root, while ArtifactSaga creates the child resource version.
    options.update(
        {
            "parent_resource_id": str(row.id),
            "retry_source_resource_id": str(row.id),
            "retry_source_workflow_run_id": str(row.workflow_run_id) if row.workflow_run_id else None,
            "retry_source_step_attempt_id": str(row.step_attempt_id) if row.step_attempt_id else None,
        }
    )
    query = payload.query.strip() if payload.query and payload.query.strip() else f"Regenerate {row.resource_type}: {row.title}"
    start = await start_product_workflow(
        _service(request),
        workflow="resource_generate_v1",
        actor_user_id=current_user_id,
        course_id=row.course_id,
        input_payload={
            "resource_type": row.resource_type,
            "kp_id": str(row.kp_id) if row.kp_id else None,
            "query": query,
            "options": options,
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return accepted_root_response(start)


__all__ = ["router"]
