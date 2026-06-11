# Status: real

"""课程学习相关 endpoint：学习路径生成 + SSE 流式资源生成。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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
from app.runtime.harness import HarnessContext

router = APIRouter()

ResourceType = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video"]


SKILL_MAP: dict[str, tuple[type, type]] = {
    "doc": (GenerateCourseDoc, GenerateCourseDocInput),
    "ppt": (GenerateCoursePPT, GenerateCoursePPTInput),
    "mindmap": (GenerateMindmap, GenerateMindmapInput),
    "video": (GenerateVideoStoryboard, GenerateVideoStoryboardInput),
    "quiz": (GenerateQuiz, GenerateQuizInput),
    "lab": (GenerateHandsOnLab, GenerateHandsOnLabInput),
}


# === 课程列表占位（保留供前端拉取） =========================================


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
        title="Web 安全基础",
        domain="course_websec",
        description="OWASP Top 10 + 实战 Lab + 题库 + 视频脚本一体的入门课程。",
    ),
]


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses() -> list[CourseSummary]:
    return _DEMO_COURSES


@router.get("/courses/{course_id}", response_model=CourseSummary)
async def get_course(course_id: str) -> CourseSummary:
    for course in _DEMO_COURSES:
        if course.id == course_id or course.code == course_id:
            return course
    return _DEMO_COURSES[0]


# === 学习路径生成 ===========================================================


class CoursePlanRequest(BaseModel):
    user_id: str = "demo"
    selected_kp_ids: list[str] = Field(default_factory=list)
    time_budget_hours: int | None = None
    query: str | None = None


class CoursePlanResponse(BaseModel):
    task_id: str
    status: str = "ok"
    path: dict


@router.post("/courses/{course_id}/plan", response_model=CoursePlanResponse)
async def plan_learning_path(course_id: str, payload: CoursePlanRequest) -> CoursePlanResponse:
    ctx = HarnessContext(
        user_id=payload.user_id,
        workflow_name="course_learning",
    )
    skill = GenerateLearningPath()
    inp = GenerateLearningPathInput(
        user_id=payload.user_id,
        query=payload.query or f"为 {course_id} 生成个性化学习路径",
        course_id=course_id,
    )
    out = await skill.run(inp, ctx)
    return CoursePlanResponse(task_id=str(uuid4()), path=out.model_dump())


# === SSE 资源生成 ============================================================


class GenerateResourceRequest(BaseModel):
    user_id: str = "demo"
    kp_id: str | None = None
    query: str | None = None
    preferences: dict[str, str] = Field(default_factory=dict)


async def _resource_event_bus(
    course_id: str,
    payload: GenerateResourceRequest,
    resource_type: ResourceType,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[dict] = asyncio.Queue()
    done = asyncio.Event()

    async def emit(event: dict) -> None:
        await queue.put(event)

    skill_cls, input_cls = SKILL_MAP[resource_type]
    ctx = HarnessContext(
        user_id=payload.user_id,
        workflow_name=f"course_{course_id}_resource_{resource_type}",
        stream=True,
        emit=emit,
    )
    skill = skill_cls()
    inp = input_cls(
        user_id=payload.user_id,
        query=payload.query or f"为 {course_id} 生成 {resource_type} 资源",
        kp_id=payload.kp_id,
    ) if "kp_id" in input_cls.model_fields else input_cls(
        user_id=payload.user_id,
        query=payload.query or f"为 {course_id} 生成 {resource_type} 资源",
    )

    final_output: dict = {}

    async def run_skill() -> None:
        nonlocal final_output
        try:
            out = await skill.run(inp, ctx)
            final_output = out.model_dump()
        except Exception as exc:  # noqa: BLE001 - propagate to SSE error frame
            await emit(
                {
                    "event": "error",
                    "code": getattr(exc, "code", "unknown_error"),
                    "message": str(exc),
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
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            event_name = event.pop("event", "message")
            yield f"event: {event_name}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
    finally:
        await task


@router.post("/courses/{course_id}/resources/generate")
async def generate_resource(
    course_id: str,
    payload: GenerateResourceRequest,
    type: ResourceType = Query("doc"),
) -> StreamingResponse:
    return StreamingResponse(
        _resource_event_bus(course_id, payload, type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
