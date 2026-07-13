# Status: real

"""Tutor HTTP adapter for the durable ``tutor_routing_v3`` workflow."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.api.v1.endpoints.workflow_adapter import (
    durable_sse_response,
    start_product_workflow,
    workflow_service,
)
from app.deps import CurrentUserDep
from app.schemas.tutor import TutorAskRequest
from app.services.workflow_application_service import WorkflowApplicationService


router = APIRouter()


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


@router.post("/tutor/ask")
async def tutor_ask(
    payload: TutorAskRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="tutor_routing_v3",
        actor_user_id=current_user_id,
        course_id=payload.course_id,
        input_payload={
            "question": payload.question,
            "context": dict(payload.context),
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return durable_sse_response(service, start, actor_user_id=current_user_id)
