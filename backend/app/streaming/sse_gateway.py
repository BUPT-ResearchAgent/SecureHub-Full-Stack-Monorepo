# Status: real

"""Durable SSE gateway: replay first, then poll/replay live gaps from PostgreSQL."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from app.runtime.contracts import EventEnvelope
from app.services.workflow_application_service import WorkflowApplicationService


class WorkflowSSEGateway:
    """A slow consumer never blocks the Worker or becomes event truth."""

    def __init__(
        self,
        service: WorkflowApplicationService,
        *,
        poll_interval_seconds: float = 0.25,
        notifier: Any | None = None,
    ) -> None:
        self.service = service
        self.poll_interval_seconds = poll_interval_seconds
        # The service obtains this shared notifier from RuntimeSupervisor. A
        # direct/test service simply has no Redis acceleration and continues
        # to use the PostgreSQL polling fallback.
        self.notifier = notifier if notifier is not None else getattr(service, "live_notifier", None)

    async def stream(
        self,
        workflow_run_id: UUID | str,
        *,
        after_sequence: int = 0,
        until_sequence: int | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> AsyncIterator[EventEnvelope]:
        cursor = after_sequence
        stop_listener = asyncio.Event()
        redis_wakeup = asyncio.Event()
        listener = self._start_redis_listener(
            workflow_run_id,
            redis_wakeup,
            stop_listener,
        )
        try:
            while True:
                events = await self.service.replay(
                    workflow_run_id,
                    after_sequence=cursor,
                    until_sequence=until_sequence,
                    actor_user_id=actor_user_id,
                )
                if events:
                    for event in events:
                        if event.sequence <= cursor:
                            continue
                        # PostgreSQL replay is also live-gap recovery. It keeps
                        # sequence ordering when Redis fan-out is lost/duplicated.
                        cursor = event.sequence
                        yield event
                        if event.terminal or (until_sequence is not None and cursor >= until_sequence):
                            return
                    continue
                status = await self.service.get(workflow_run_id, actor_user_id=actor_user_id)
                if status.status in {"succeeded", "failed", "blocked", "cancelled"}:
                    # Run state can commit immediately before its terminal
                    # event becomes visible. Do not end an SSE stream without
                    # the durable done/error envelope the client relies on.
                    await self._wait_for_live_hint_or_poll(redis_wakeup)
                    continue
                if until_sequence is not None and cursor >= until_sequence:
                    return
                await self._wait_for_live_hint_or_poll(redis_wakeup)
        finally:
            stop_listener.set()
            if listener is not None:
                listener.cancel()
                await asyncio.gather(listener, return_exceptions=True)

    def _start_redis_listener(
        self,
        workflow_run_id: UUID | str,
        wakeup: asyncio.Event,
        stop_requested: asyncio.Event,
    ) -> asyncio.Task[None] | None:
        listen = getattr(self.notifier, "listen_events", None)
        if not callable(listen):
            return None

        def wake(_payload: str) -> None:
            # The message is intentionally not decoded into an SSE event. It
            # is only a hint to replay the ordered PostgreSQL outbox rows.
            wakeup.set()

        return asyncio.create_task(
            listen(
                workflow_run_id,
                wake,
                stop_requested=stop_requested.is_set,
            ),
            name=f"securehub-sse-redis-{workflow_run_id}",
        )

    async def _wait_for_live_hint_or_poll(self, wakeup: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(wakeup.wait(), timeout=self.poll_interval_seconds)
        except TimeoutError:
            pass
        finally:
            # Redis duplicates can only save or cost one poll cycle. They can
            # never advance the cursor because replay owns that decision.
            wakeup.clear()


__all__ = ["WorkflowSSEGateway"]
