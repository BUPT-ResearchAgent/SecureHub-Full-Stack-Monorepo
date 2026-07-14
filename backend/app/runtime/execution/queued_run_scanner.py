# Status: real

"""PostgreSQL queued-run scanner; Redis can only wake this scanner early."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.workflow_runtime import WorkflowRun
from app.runtime.persistence.run_store import RunStore


class QueuedRunScanner:
    """Claims from PostgreSQL even when every Redis notification is lost."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        owner: str,
        lease_seconds: float = 30.0,
    ) -> None:
        self.session_factory = session_factory
        self.owner = owner
        self.lease_seconds = lease_seconds
        self._wake = asyncio.Event()

    def notify(self) -> None:
        """Redis/listener acceleration hook; it carries no durable state."""
        self._wake.set()

    async def wait_for_work(self, timeout_seconds: float) -> None:
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=timeout_seconds)
        except TimeoutError:
            return
        finally:
            self._wake.clear()

    async def claim_once(self) -> WorkflowRun | None:
        async with self.session_factory() as session:
            run = await RunStore(session).claim_next(self.owner, self.lease_seconds)
            await session.commit()
            return run


__all__ = ["QueuedRunScanner"]
