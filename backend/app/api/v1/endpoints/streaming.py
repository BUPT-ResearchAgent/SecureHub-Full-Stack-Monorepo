# Status: partial-real

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette import status

from app.streaming.events import ErrorEvent, SSEEvent
from app.streaming.sse import sse_response

try:
    from sse_starlette.sse import EventSourceResponse
    HAS_SSE_STARLETTE = True
except ImportError:  # pragma: no cover - optional dependency in this repo
    HAS_SSE_STARLETTE = False

    class EventSourceResponse(StreamingResponse):  # type: ignore[no-redef]
        """Small compatibility wrapper when sse-starlette is not installed."""

router = APIRouter()

ERROR_STATUS_BY_NAME = {
    "InsufficientEvidence": 422,
    "SkillTimeout": status.HTTP_504_GATEWAY_TIMEOUT,
    "LLMProviderError": status.HTTP_502_BAD_GATEWAY,
    "QualityCheckFailed": 422,
    "BudgetExceeded": status.HTTP_429_TOO_MANY_REQUESTS,
}

ERROR_CODE_BY_NAME = {
    "InsufficientEvidence": "InsufficientEvidence",
    "SkillTimeout": "SkillTimeout",
    "LLMProviderError": "LLMProviderError",
    "QualityCheckFailed": "QualityCheckFailed",
    "BudgetExceeded": "BudgetExceeded",
}


async def task_event_bus(task_id: str) -> AsyncIterator[SSEEvent]:
    yield ErrorEvent(code="not_implemented", message=f"TODO: stream task {task_id}", recoverable=True)


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    return sse_response(task_event_bus(task_id))


def to_plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump(mode="json")
    return value


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def service_kwargs(payload: BaseModel | dict[str, Any], **extra: Any) -> dict[str, Any]:
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else dict(payload)
    data.update(extra)
    return data


def normalize_error(exc: Exception) -> HTTPException:
    name = exc.__class__.__name__
    code = ERROR_CODE_BY_NAME.get(name) or getattr(exc, "code", None) or "InternalError"
    return HTTPException(
        status_code=ERROR_STATUS_BY_NAME.get(name, status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail={
            "message": str(exc) or name,
            "code": code,
        },
    )


def raise_mapped_error(exc: Exception) -> None:
    raise normalize_error(exc) from exc


def _coerce_event(item: Any) -> dict[str, Any]:
    plain = to_plain(item)
    if isinstance(plain, dict):
        return plain
    return {"event": "token", "content": str(plain)}


async def iter_events(source: Any) -> AsyncIterator[dict[str, Any]]:
    resolved = await maybe_await(source)
    if hasattr(resolved, "__aiter__"):
        async for item in resolved:
            yield _coerce_event(item)
        return
    if isinstance(resolved, Iterable) and not isinstance(resolved, (str, bytes, dict)):
        for item in resolved:
            yield _coerce_event(item)
        return
    yield {"event": "done", "result": to_plain(resolved)}


async def _serialize_events(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    async for event in events:
        payload = dict(event)
        event_name = str(payload.pop("event", "message"))
        yield f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def make_event_source_response(events: AsyncIterator[dict[str, Any]]):
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if not HAS_SSE_STARLETTE:
        return EventSourceResponse(
            _serialize_events(events),
            media_type="text/event-stream",
            headers=headers,
        )

    async def wrapped() -> AsyncIterator[dict[str, Any]]:
        async for event in events:
            payload = dict(event)
            event_name = str(payload.pop("event", "message"))
            yield {"event": event_name, "data": payload}

    return EventSourceResponse(wrapped(), headers=headers)


async def call_streaming_service(
    func: Callable[..., Any],
    *,
    kwargs: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    try:
        async for event in iter_events(func(**kwargs)):
            yield event
    except Exception as exc:  # noqa: BLE001 - SSE failures are emitted in-band
        mapped = normalize_error(exc)
        detail = mapped.detail if isinstance(mapped.detail, dict) else {}
        yield {
            "event": "error",
            "message": detail.get("message", str(exc)),
            "code": detail.get("code", "InternalError"),
            "recoverable": False,
        }


async def call_json_service(func: Callable[..., Awaitable[Any] | Any], *, kwargs: dict[str, Any]) -> Any:
    try:
        return to_plain(await maybe_await(func(**kwargs)))
    except Exception as exc:  # noqa: BLE001 - normalized API boundary
        raise_mapped_error(exc)
