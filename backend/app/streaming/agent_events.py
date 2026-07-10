# Status: partial-real

"""SSE serialization for the fixed workflow Run API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.responses import StreamingResponse


AGENT_EVENT_TYPES = frozenset(
    {"progress", "evidence", "token", "artifact", "trace", "done", "error"}
)


def validate_agent_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    event_name = payload.get("event")
    if event_name not in AGENT_EVENT_TYPES:
        raise ValueError(f"unsupported agent SSE event: {event_name!r}")
    return payload


async def serialize_agent_events(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    async for raw_event in events:
        event = validate_agent_event(raw_event)
        event_name = str(event.pop("event"))
        event.pop("_terminal", None)
        yield f"event: {event_name}\ndata: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


def agent_event_response(events: AsyncIterator[dict[str, Any]]) -> StreamingResponse:
    return StreamingResponse(
        serialize_agent_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
