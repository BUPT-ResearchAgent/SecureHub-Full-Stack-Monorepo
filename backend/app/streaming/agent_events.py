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
    event_id = payload.get("event_id")
    if event_id is not None and (not isinstance(event_id, int) or event_id < 1):
        raise ValueError("agent SSE event_id must be a positive integer")
    return payload


async def serialize_agent_events(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    async for raw_event in events:
        event = validate_agent_event(raw_event)
        event_name = str(event.pop("event"))
        event.pop("_terminal", None)
        event_id = event.get("event_id")
        event_id_line = f"id: {event_id}\n" if event_id is not None else ""
        yield (
            f"{event_id_line}event: {event_name}\n"
            f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
        )


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
