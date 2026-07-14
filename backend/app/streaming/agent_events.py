# Status: partial-real

"""SSE serialization for the fixed workflow Run API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from app.runtime.contracts import EventEnvelope

async def serialize_workflow_events(events: AsyncIterator[EventEnvelope]) -> AsyncIterator[str]:
    """Serialize the durable EventEnvelope, using sequence as SSE id."""
    async for envelope in events:
        payload = envelope.as_sse_payload()
        yield (
            f"id: {envelope.sequence}\n"
            f"event: {envelope.event_type}\n"
            f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        )


def workflow_event_response(events: AsyncIterator[EventEnvelope]) -> StreamingResponse:
    return StreamingResponse(
        serialize_workflow_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
