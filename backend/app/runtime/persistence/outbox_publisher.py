# Status: real

"""Reliable publisher for the PostgreSQL workflow_events Transactional Outbox."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.runtime.persistence.event_store import EventStore


PublishCallback = Callable[[Any], Awaitable[None] | None]
SessionSource = AsyncSession | async_sessionmaker[AsyncSession]


class EventOutboxPublisher:
    """Publishes durable facts at-least-once, with per-run outbox ordering.

    If a process dies after the external publish and before ``published_at`` is
    committed, the event is intentionally republished after its DB lease
    expires. SSE consumers deduplicate by ``(workflow_run_id, sequence)``.
    """

    def __init__(
        self,
        session_source: SessionSource,
        publish: PublishCallback,
        *,
        owner: str,
        lease_seconds: float = 30.0,
        max_retry_seconds: float = 60.0,
    ) -> None:
        if not owner.strip() or lease_seconds <= 0 or max_retry_seconds <= 0:
            raise ValueError("invalid publisher configuration")
        self._session_source = session_source
        self._publish = publish
        self.owner = owner
        self.lease_seconds = lease_seconds
        self.max_retry_seconds = max_retry_seconds

    async def publish_once(self, *, batch_size: int = 32) -> int:
        if isinstance(self._session_source, AsyncSession):
            return await self._publish_with_session(self._session_source, batch_size=batch_size)
        async with self._session_source() as session:
            return await self._publish_with_session(session, batch_size=batch_size)

    async def run_forever(
        self,
        *,
        poll_interval_seconds: float = 0.5,
        stop_requested: Callable[[], bool] | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        while stop_requested is None or not stop_requested():
            count = await self.publish_once()
            if count == 0:
                await asyncio.sleep(poll_interval_seconds)

    async def _publish_with_session(self, session: AsyncSession, *, batch_size: int) -> int:
        store = EventStore(session)
        claimed = await store.claim_publishable(
            self.owner,
            batch_size=batch_size,
            lease_seconds=self.lease_seconds,
        )
        # Persist the claim before sending anything to an external projection.
        claimed_ids = [event.id for event in claimed]
        await session.commit()
        completed = 0
        for event_id in claimed_ids:
            # Avoid accessing an expired ORM instance after commit when a
            # caller supplied a sessionmaker with expire_on_commit=True.
            event = await session.get(type(claimed[0]), event_id)
            if event is None:
                continue
            try:
                envelope = await store.event_envelope(event)
                result = self._publish(envelope)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # noqa: BLE001 - publisher failures are retried durably
                delay = min(
                    self.max_retry_seconds,
                    float(2 ** max(0, int(event.publish_attempts) - 1)),
                )
                await store.mark_publish_failed(
                    event.id,
                    owner=self.owner,
                    error=exc,
                    retry_after_seconds=delay,
                )
                await session.commit()
                continue
            if await store.mark_published(event.id, owner=self.owner):
                completed += 1
            await session.commit()
        return completed


__all__ = ["EventOutboxPublisher", "PublishCallback"]
