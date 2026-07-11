# Status: real

"""Best-effort Redis acceleration for durable run wake-up and event fan-out."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.runtime.contracts import EventEnvelope

logger = logging.getLogger(__name__)

NotificationCallback = Callable[[str], Awaitable[None] | None]
StopRequested = Callable[[], bool]


class RedisRuntimeNotifier:
    """Redis failures are intentionally non-fatal; PostgreSQL remains truth."""

    RUN_CHANNEL = "securehub:runtime:queued"
    EVENT_CHANNEL_PREFIX = "securehub:runtime:event:"

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client: Any | None = None

    async def notify_run(self, run_id: UUID) -> None:
        client = await self._get_client()
        if client is None:
            return
        try:
            await client.publish(self.RUN_CHANNEL, str(run_id))
        except Exception as exc:  # noqa: BLE001
            logger.debug("redis run notification unavailable: %s", exc)

    async def publish_event(self, envelope: EventEnvelope) -> None:
        client = await self._get_client()
        if client is None:
            return
        try:
            payload = json.dumps(envelope.as_sse_payload(), ensure_ascii=False, default=str)
            await client.publish(f"{self.EVENT_CHANNEL_PREFIX}{envelope.workflow_run_id}", payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("redis event fan-out unavailable: %s", exc)

    async def listen_runs(
        self,
        callback: NotificationCallback,
        *,
        stop_requested: StopRequested,
        poll_timeout_seconds: float = 1.0,
    ) -> None:
        """Best-effort run wake-up subscription; PostgreSQL still decides work."""
        await self._listen(
            self.RUN_CHANNEL,
            callback,
            stop_requested=stop_requested,
            poll_timeout_seconds=poll_timeout_seconds,
        )

    async def listen_events(
        self,
        workflow_run_id: UUID | str,
        callback: NotificationCallback,
        *,
        stop_requested: StopRequested,
        poll_timeout_seconds: float = 1.0,
    ) -> None:
        """Wake an SSE gateway after a Redis fan-out hint, never trust its payload."""
        await self._listen(
            f"{self.EVENT_CHANNEL_PREFIX}{workflow_run_id}",
            callback,
            stop_requested=stop_requested,
            poll_timeout_seconds=poll_timeout_seconds,
        )

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    async def _listen(
        self,
        channel: str,
        callback: NotificationCallback,
        *,
        stop_requested: StopRequested,
        poll_timeout_seconds: float,
    ) -> None:
        if poll_timeout_seconds <= 0:
            raise ValueError("poll_timeout_seconds must be positive")
        client = await self._get_client()
        if client is None:
            return
        pubsub: Any | None = None
        try:
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            await pubsub.subscribe(channel)
            while not stop_requested():
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=poll_timeout_seconds,
                )
                if message is None:
                    # Some redis-py versions return immediately when no data
                    # is available. Back off so an unavailable broker cannot
                    # spin a core while PostgreSQL polling remains the fallback.
                    await asyncio.sleep(min(0.05, poll_timeout_seconds))
                    continue
                raw = message.get("data") if isinstance(message, dict) else None
                if raw is None:
                    continue
                payload = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                result = callback(payload)
                if inspect.isawaitable(result):
                    await result
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a broken hint channel is non-fatal
            logger.debug("redis runtime subscription unavailable: %s", exc)
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:  # noqa: BLE001 - close must not affect durable paths
                    pass

    async def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=0.2)
            await self._client.ping()
            return self._client
        except Exception as exc:  # noqa: BLE001
            logger.debug("redis acceleration disabled: %s", exc)
            self._client = None
            return None


__all__ = ["RedisRuntimeNotifier"]
