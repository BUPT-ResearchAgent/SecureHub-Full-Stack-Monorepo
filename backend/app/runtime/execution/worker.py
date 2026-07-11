# Status: real

"""Small independent worker for durable RuntimeEngine execution."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.workflow_runtime import WorkflowRun
from app.runtime.execution.lease import Lease, LeaseManager
from app.runtime.persistence.common import LeaseFencedError
from app.runtime.persistence.run_store import RunStore


ExecuteClaim = Callable[[WorkflowRun, Lease, AsyncSession], Awaitable[None] | None]


class RuntimeWorker:
    """Claims via PostgreSQL, executes through RuntimeEngine callback, and never
    treats an in-memory queue or Redis delivery as the source of truth.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        execute_claim: ExecuteClaim,
        *,
        owner: str,
        lease_seconds: float = 30.0,
    ) -> None:
        self.session_factory = session_factory
        self.execute_claim = execute_claim
        self.owner = owner
        self.lease_seconds = lease_seconds
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    async def run_once(self) -> bool:
        async with self.session_factory() as session:
            store = RunStore(session)
            run = await store.claim_next(self.owner, self.lease_seconds)
            await session.commit()
            if run is None:
                return False
            lease = Lease.from_run(run)
            stop_heartbeat = asyncio.Event()

            async def invoke_claim() -> None:
                result = self.execute_claim(run, lease, session)
                if inspect.isawaitable(result):
                    await result

            execution = asyncio.create_task(invoke_claim(), name=f"securehub-run-{run.id}")
            heartbeat = asyncio.create_task(
                self._heartbeat(lease, stop_heartbeat),
                name=f"securehub-lease-{run.id}",
            )
            try:
                done, _pending = await asyncio.wait(
                    {execution, heartbeat},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if heartbeat in done:
                    heartbeat_error = heartbeat.exception()
                    if heartbeat_error is not None:
                        execution.cancel()
                        await asyncio.gather(execution, return_exceptions=True)
                        raise heartbeat_error
                # If the execution completed normally, FIRST_COMPLETED leaves
                # the heartbeat pending. Only the execution result decides
                # normal completion; the finally block stops the heartbeat.
                await execution
                await session.commit()
            except LeaseFencedError:
                await session.rollback()
            except Exception:
                # The durable root remains recoverable; RecoveryService owns
                # the next action instead of manufacturing a terminal success.
                await session.rollback()
                raise
            finally:
                stop_heartbeat.set()
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
            return True

    async def _heartbeat(self, lease: Lease, stop_requested: asyncio.Event) -> None:
        """Renew from an independent session while the engine owns its transaction.

        The root CAS still carries ``lease_epoch`` on every write. Heartbeat
        merely prevents a healthy long-running provider stream from becoming
        stale and being claimed by another worker mid-execution.
        """
        interval = max(0.05, min(self.lease_seconds / 3.0, 5.0))
        while not stop_requested.is_set():
            try:
                await asyncio.wait_for(stop_requested.wait(), timeout=interval)
                return
            except TimeoutError:
                pass
            async with self.session_factory() as heartbeat_session:
                manager = LeaseManager(
                    RunStore(heartbeat_session),
                    owner=self.owner,
                    lease_seconds=self.lease_seconds,
                )
                await manager.renew(lease)
                await heartbeat_session.commit()

    async def run_forever(self, *, idle_sleep_seconds: float = 0.5) -> None:
        if idle_sleep_seconds <= 0:
            raise ValueError("idle_sleep_seconds must be positive")
        while not self._stop:
            if not await self.run_once():
                await asyncio.sleep(idle_sleep_seconds)


__all__ = ["RuntimeWorker"]
