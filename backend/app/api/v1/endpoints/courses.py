# Status: real

"""Course HTTP adapters backed exclusively by durable workflow roots."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.v1.endpoints.workflow_adapter import (
    accepted_root_response,
    completed_root_response,
    durable_sse_response,
    require_successful_terminal,
    start_product_workflow,
    wait_for_terminal,
    workflow_service,
)
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.deps import CurrentUserDep
from app.schemas.agent_control import WorkflowRunStartResponse
from app.schemas.course import CoursePlanRequest, CoursePlanResponse
from app.schemas.resource import ResourceGenerateRequest
from app.services.workflow_application_service import WorkflowApplicationService


router = APIRouter()

ResourceType = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video", "readings"]


class CourseSummary(BaseModel):
    id: str
    code: str
    title: str
    domain: str
    description: str | None = None


class CourseResourceBundleRequest(BaseModel):
    kp_id: UUID
    options: dict[str, Any] | None = None
    mode: Literal["fixture", "real"] = "real"
    provider: str | None = None
    model: str | None = None


_DEMO_COURSES: list[CourseSummary] = [
    CourseSummary(
        id="course-websec",
        code="WEB-SEC-101",
        title="Web security fundamentals",
        domain="course_websec",
        description="OWASP Top 10, hands-on labs, quizzes, and guided resources.",
    ),
]

DEMO_COURSE_UUID = COURSE_WEBSEC_ID


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


def _contract_course_id(course_id: str) -> UUID:
    if course_id in {"course-websec", "WEB-SEC-101", str(COURSE_WEBSEC_ID)}:
        return COURSE_WEBSEC_ID
    try:
        return UUID(course_id)
    except ValueError:
        return DEMO_COURSE_UUID


def _contract_path_nodes(result: dict[str, object]) -> list[dict[str, object]]:
    raw_path = result.get("path")
    raw_nodes = raw_path if isinstance(raw_path, list) else result.get("nodes")
    if not isinstance(raw_nodes, list):
        raise ValueError("workflow output does not contain a learning path")

    nodes: list[dict[str, object]] = []
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            raise ValueError("learning path contains a non-object node")
        node_id = raw_node.get("node_id") or raw_node.get("id") or raw_node.get("kp_id")
        title = raw_node.get("title") or raw_node.get("label")
        if node_id is None or title is None:
            raise ValueError(f"learning path node {index} is incomplete")
        status_value = raw_node.get("status")
        status_text = status_value if isinstance(status_value, str) else "ready"
        if status_text == "active":
            status_text = "in_progress"
        if status_text not in {"locked", "ready", "in_progress", "done"}:
            status_text = "ready"
        prerequisites = raw_node.get("prerequisites")
        nodes.append(
            {
                "node_id": str(node_id),
                "title": str(title),
                "status": status_text,
                "prerequisites": prerequisites if isinstance(prerequisites, list) else [],
            }
        )
    return nodes


def _course_plan_response(course_id: UUID, result: dict[str, object]) -> CoursePlanResponse:
    try:
        path = _contract_path_nodes(result)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "WORKFLOW_OUTPUT_INVALID", "message": str(exc)},
        ) from exc
    return CoursePlanResponse(course_id=course_id, path=path)


def _option_query(options: dict[str, object] | None, fallback: str) -> str:
    value = (options or {}).get("query")
    return value.strip() if isinstance(value, str) and value.strip() else fallback


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses() -> list[CourseSummary]:
    return _DEMO_COURSES


@router.get("/courses/{course_id}", response_model=CourseSummary)
async def get_course(course_id: str) -> CourseSummary:
    for course in _DEMO_COURSES:
        if course.id == course_id or course.code == course_id:
            return course
    return _DEMO_COURSES[0]


@router.post(
    "/courses/{course_id}/plan",
    response_model=CoursePlanResponse | WorkflowRunStartResponse,
    responses={202: {"model": WorkflowRunStartResponse, "description": "Durable workflow remains in progress."}},
)
async def plan_learning_path(
    course_id: str,
    payload: CoursePlanRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CoursePlanResponse | JSONResponse:
    canonical_course_id = _contract_course_id(course_id)
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="course_plan_v1",
        actor_user_id=current_user_id,
        course_id=canonical_course_id,
        input_payload={
            "target_node_id": str(payload.target_node_id),
            "query": _option_query(payload.options, f"Generate a personalised path for {course_id}"),
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    terminal = await wait_for_terminal(service, start.run_id, actor_user_id=current_user_id)
    if terminal is None:
        return accepted_root_response(start)
    completed = _course_plan_response(canonical_course_id, require_successful_terminal(terminal))
    return completed_root_response(start, completed.model_dump(mode="json"))


@router.post("/courses/{course_id}/resources/generate")
async def generate_resource(
    course_id: str,
    payload: ResourceGenerateRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    type: ResourceType | None = Query(None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    resource_type = type or payload.type
    canonical_course_id = _contract_course_id(course_id)
    options = dict(payload.options or {})
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="resource_generate_v1",
        actor_user_id=current_user_id,
        course_id=canonical_course_id,
        input_payload={
            "resource_type": resource_type,
            "kp_id": str(payload.kp_id),
            "query": _option_query(options, f"Generate {resource_type} resource for {course_id}"),
            "options": options,
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return durable_sse_response(service, start, actor_user_id=current_user_id)


@router.post("/courses/{course_id}/resources/generate-bundle")
async def generate_resource_bundle(
    course_id: str,
    payload: CourseResourceBundleRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    """Create one v2 root for the default six-resource course bundle."""
    canonical_course_id = _contract_course_id(course_id)
    options = dict(payload.options or {})
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="course_learning_full_v2",
        actor_user_id=current_user_id,
        course_id=canonical_course_id,
        input_payload={
            "kp_id": str(payload.kp_id),
            "query": _option_query(options, f"Generate the complete course resource pack for {course_id}"),
            "options": options,
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return durable_sse_response(service, start, actor_user_id=current_user_id)
