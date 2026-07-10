# Status: partial-real

"""Course endpoints with real-first service adapters and skill fallbacks."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.competition_advisor.skills.generate_quiz import (
    GenerateQuiz,
    GenerateQuizInput,
)
from app.agents.doc_archivist.skills.generate_course_doc import (
    GenerateCourseDoc,
    GenerateCourseDocInput,
)
from app.agents.doc_archivist.skills.generate_course_ppt import (
    GenerateCoursePPT,
    GenerateCoursePPTInput,
)
from app.agents.doc_archivist.skills.generate_mindmap import (
    GenerateMindmap,
    GenerateMindmapInput,
)
from app.agents.doc_archivist.skills.generate_video_storyboard import (
    GenerateVideoStoryboard,
    GenerateVideoStoryboardInput,
)
from app.agents.task_orchestrator.skills.generate_learning_path import (
    GenerateLearningPath,
    GenerateLearningPathInput,
)
from app.agents.topic_explorer.skills.generate_hands_on_lab import (
    GenerateHandsOnLab,
    GenerateHandsOnLabInput,
)
from app.agents.topic_explorer.skills.recommend_readings import (
    RecommendReadings,
    RecommendReadingsInput,
)
from app.api.v1.endpoints.streaming import (
    call_json_service,
    call_streaming_service,
    make_event_source_response,
    normalize_error,
    raise_mapped_error,
    service_kwargs,
)
from app.runtime.harness import HarnessContext
from app.schemas.course import CoursePlanRequest, CoursePlanResponse
from app.schemas.resource import ResourceGenerateRequest

router = APIRouter()

try:
    from app.services.agent import generate_learning_path as real_generate_learning_path
except ImportError:
    real_generate_learning_path = None

try:
    from app.services.resources import generate_resource as real_generate_resource
except ImportError:
    try:
        from app.services.resource import generate_resource as real_generate_resource
    except ImportError:
        real_generate_resource = None

ResourceType = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video", "readings"]

SKILL_MAP: dict[str, tuple[type, type]] = {
    "doc": (GenerateCourseDoc, GenerateCourseDocInput),
    "ppt": (GenerateCoursePPT, GenerateCoursePPTInput),
    "mindmap": (GenerateMindmap, GenerateMindmapInput),
    "video": (GenerateVideoStoryboard, GenerateVideoStoryboardInput),
    "quiz": (GenerateQuiz, GenerateQuizInput),
    "lab": (GenerateHandsOnLab, GenerateHandsOnLabInput),
    "readings": (RecommendReadings, RecommendReadingsInput),
}


class CourseSummary(BaseModel):
    id: str
    code: str
    title: str
    domain: str
    description: str | None = None


_DEMO_COURSES: list[CourseSummary] = [
    CourseSummary(
        id="course-websec",
        code="WEB-SEC-101",
        title="Web security fundamentals",
        domain="course_websec",
        description="OWASP Top 10, hands-on labs, quizzes, and guided resources.",
    ),
]

DEMO_COURSE_UUID = UUID("00000000-0000-0000-0000-000000000101")


def _contract_course_id(course_id: str) -> UUID:
    try:
        return UUID(course_id)
    except ValueError:
        return DEMO_COURSE_UUID


def _contract_path_nodes(result: dict[str, object]) -> list[dict[str, object]]:
    raw_path = result.get("path")
    if isinstance(raw_path, list):
        return raw_path

    raw_nodes = result.get("nodes")
    if not isinstance(raw_nodes, list):
        return []

    nodes: list[dict[str, object]] = []
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            continue
        node_id = raw_node.get("node_id") or raw_node.get("id") or raw_node.get("kp_id") or str(uuid4())
        title = raw_node.get("title") or raw_node.get("label") or f"学习节点 {index + 1}"
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


def _course_plan_response(course_id: str, result: object) -> CoursePlanResponse:
    plain = result if isinstance(result, dict) else {}
    return CoursePlanResponse(
        course_id=_contract_course_id(course_id),
        path=_contract_path_nodes(plain),
    )


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses() -> list[CourseSummary]:
    return _DEMO_COURSES


@router.get("/courses/{course_id}", response_model=CourseSummary)
async def get_course(course_id: str) -> CourseSummary:
    for course in _DEMO_COURSES:
        if course.id == course_id or course.code == course_id:
            return course
    return _DEMO_COURSES[0]


@router.post("/courses/{course_id}/plan", response_model=CoursePlanResponse)
async def plan_learning_path(course_id: str, payload: CoursePlanRequest) -> CoursePlanResponse:
    if real_generate_learning_path is not None:
        result = await call_json_service(
            real_generate_learning_path,
            kwargs=service_kwargs(payload, course_id=course_id),
        )
        return _course_plan_response(course_id, result)

    try:
        ctx = HarnessContext(
            user_id=str(payload.user_id),
            workflow_name="course_learning",
        )
        skill = GenerateLearningPath()
        query_option = (payload.options or {}).get("query")
        inp = GenerateLearningPathInput(
            user_id=str(payload.user_id),
            query=str(query_option) if query_option else f"Generate a personalized path for {course_id}",
            course_id=course_id,
        )
        out = await skill.run(inp, ctx)
        return _course_plan_response(course_id, out.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - normalized API boundary
        raise_mapped_error(exc)


async def _resource_event_bus(
    course_id: str,
    payload: ResourceGenerateRequest,
    resource_type: ResourceType,
) -> AsyncIterator[dict]:
    queue: asyncio.Queue[dict] = asyncio.Queue()
    done = asyncio.Event()

    async def emit(event: dict) -> None:
        await queue.put(event)

    skill_cls, input_cls = SKILL_MAP[resource_type]
    ctx = HarnessContext(
        user_id=str(payload.user_id),
        workflow_name=f"course_{course_id}_resource_{resource_type}",
        stream=True,
        emit=emit,
    )
    query_option = (payload.options or {}).get("query")
    query = str(query_option) if query_option else f"Generate {resource_type} resource for {course_id}"
    if "kp_id" in input_cls.model_fields:
        inp = input_cls(user_id=str(payload.user_id), query=query, kp_id=str(payload.kp_id))
    else:
        inp = input_cls(user_id=str(payload.user_id), query=query)

    final_output: dict = {}

    async def run_skill() -> None:
        nonlocal final_output
        try:
            out = await skill_cls().run(inp, ctx)
            final_output = out.model_dump(mode="json")
            await emit(
                {
                    "event": "artifact",
                    "resource_id": None,
                    "resource_type": resource_type,
                    "object_key": None,
                    "title": f"{course_id}:{resource_type}",
                }
            )
        except Exception as exc:  # noqa: BLE001 - propagate to SSE error frame
            mapped = normalize_error(exc)
            detail = mapped.detail if isinstance(mapped.detail, dict) else {}
            await emit(
                {
                    "event": "error",
                    "code": detail.get("code", "InternalError"),
                    "message": detail.get("message", str(exc)),
                    "recoverable": False,
                }
            )
        finally:
            await emit(
                {
                    "event": "done",
                    "run_id": str(uuid4()),
                    "resource_type": resource_type,
                    "final_output_ref": None,
                    "quality_score": final_output.get("quality_score") if final_output else None,
                    "final_text": final_output.get("content") if final_output else None,
                }
            )
            done.set()

    task = asyncio.create_task(run_skill())
    try:
        while not done.is_set() or not queue.empty():
            try:
                yield await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
    finally:
        await task


@router.post("/courses/{course_id}/resources/generate")
async def generate_resource(
    course_id: str,
    payload: ResourceGenerateRequest,
    type: ResourceType | None = Query(None),
):
    resource_type = type or payload.type
    if real_generate_resource is not None:
        return await make_event_source_response(
            call_streaming_service(
                real_generate_resource,
                kwargs=service_kwargs(payload, course_id=course_id, resource_type=resource_type),
            )
        )
    return await make_event_source_response(_resource_event_bus(course_id, payload, resource_type))
