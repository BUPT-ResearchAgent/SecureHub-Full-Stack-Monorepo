# Status: [planned]

from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from app.streaming.events import SSEEvent


async def _serialize_events(events: AsyncIterator[SSEEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield event.to_sse()


def sse_response(events: AsyncIterator[SSEEvent]) -> StreamingResponse:
    return StreamingResponse(
        _serialize_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
