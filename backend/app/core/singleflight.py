"""Per-process coalescing for identical in-flight read projections.

Completed values are never cached.  A key exists only while its factory is
running, so callers share current work without accepting a stale-result TTL.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, TypeVar

from fastapi import Request


T = TypeVar("T")


class AsyncSingleFlight:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: dict[Hashable, asyncio.Task[Any]] = {}

    async def run(self, key: Hashable, factory: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            existing = self._tasks.get(key)
            if existing is None:
                task: asyncio.Task[T] = asyncio.create_task(factory())
                self._tasks[key] = task
                task.add_done_callback(
                    lambda completed, task_key=key: self._discard(task_key, completed)
                )
            else:
                task = existing
        return await asyncio.shield(task)

    def _discard(self, key: Hashable, task: asyncio.Task[Any]) -> None:
        # Task callbacks and ``run`` execute on the same event loop.  Neither
        # dictionary section contains an await, so identity-checked removal is
        # atomic without scheduling a cleanup coroutine (and without leaving a
        # completed-value cache window after every waiter was cancelled).
        if self._tasks.get(key) is task:
            self._tasks.pop(key, None)


def request_singleflight(request: Request) -> AsyncSingleFlight:
    coalescer = getattr(request.app.state, "read_singleflight", None)
    if isinstance(coalescer, AsyncSingleFlight):
        return coalescer
    coalescer = AsyncSingleFlight()
    request.app.state.read_singleflight = coalescer
    return coalescer


async def run_request_singleflight(
    request: Request,
    key: Hashable,
    factory: Callable[[], Awaitable[T]],
) -> T:
    return await request_singleflight(request).run(key, factory)


__all__ = ["AsyncSingleFlight", "request_singleflight", "run_request_singleflight"]
