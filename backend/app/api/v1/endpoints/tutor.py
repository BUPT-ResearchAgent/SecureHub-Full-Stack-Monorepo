# Status: real

"""Tutor HTTP adapter for the durable ``tutor_routing_v3`` workflow."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.v1.endpoints.workflow_adapter import (
    durable_sse_response,
    start_product_workflow,
    workflow_service,
)
from app.db.seeds._constants import resolve_course_product
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
    product = resolve_course_product(payload.course_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "COURSE_NOT_FOUND", "message": "课程不存在或链接已失效。"})
    if product.content_status != "ready":
        raise HTTPException(status_code=409, detail={"code": "COURSE_CONTENT_NOT_READY", "message": product.unavailable_reason or "课程内容正在建设中，暂不能启动真实学习工作流。"})
    start = await start_product_workflow(
        service,
        workflow="tutor_routing_v3",
        actor_user_id=current_user_id,
        course_id=payload.course_id,
        input_payload={
            "question": payload.question,
            "context": dict(payload.context),
            "domain": product.domain,
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return durable_sse_response(service, start, actor_user_id=current_user_id)
