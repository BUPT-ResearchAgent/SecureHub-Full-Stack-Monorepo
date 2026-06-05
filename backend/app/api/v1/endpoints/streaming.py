# Status: [planned]

from collections.abc import AsyncIterator

from fastapi import APIRouter

from app.streaming.events import ErrorEvent, SSEEvent
from app.streaming.sse import sse_response

router = APIRouter()


async def task_event_bus(task_id: str) -> AsyncIterator[SSEEvent]:
    yield ErrorEvent(code="not_implemented", message=f"TODO: stream task {task_id}", recoverable=True)


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    return sse_response(task_event_bus(task_id))
