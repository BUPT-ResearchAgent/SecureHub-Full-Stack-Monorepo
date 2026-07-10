# Status: partial-real

"""Tutor endpoint with real-first service adapter and skill fallback."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import APIRouter

from app.agents.career_planner.skills.route_tutor_question import (
    RouteTutorQuestion,
    RouteTutorQuestionInput,
)
from app.api.v1.endpoints.streaming import (
    call_streaming_service,
    make_event_source_response,
    normalize_error,
    service_kwargs,
)
from app.runtime.harness import HarnessContext
from app.schemas.tutor import TutorAskRequest

router = APIRouter()

try:
    from app.services.agent import ask_tutor as real_ask_tutor
except ImportError:
    real_ask_tutor = None


async def _tutor_events(payload: TutorAskRequest):
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    done = asyncio.Event()

    async def emit(event: dict[str, Any]) -> None:
        await queue.put(event)

    async def run_skill() -> None:
        try:
            ctx = HarnessContext(
                user_id=str(payload.user_id),
                workflow_name="tutor_routing",
                stream=True,
                emit=emit,
            )
            out = await RouteTutorQuestion().run(
                RouteTutorQuestionInput(
                    user_id=str(payload.user_id),
                    query=payload.question,
                    question=payload.question,
                ),
                ctx,
            )
            await emit(
                {
                    "event": "done",
                    "run_id": str(uuid4()),
                    "quality_score": out.quality_score,
                    "routing": out.model_dump(mode="json"),
                }
            )
        except Exception as exc:  # noqa: BLE001 - propagate to SSE
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


@router.post("/tutor/ask")
async def tutor_ask(payload: TutorAskRequest):
    if real_ask_tutor is not None:
        return await make_event_source_response(
            call_streaming_service(real_ask_tutor, kwargs=service_kwargs(payload))
        )
    return await make_event_source_response(_tutor_events(payload))
