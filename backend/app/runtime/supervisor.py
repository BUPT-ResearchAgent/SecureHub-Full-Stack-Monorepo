# Status: real

"""Process supervisor for PostgreSQL-scanning Worker and Outbox publisher."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.runtime.contracts import RuntimeSemanticVersion
from app.runtime.execution.lease import Lease
from app.runtime.execution.recovery import RecoveryService
from app.runtime.execution.worker import RuntimeWorker
from app.runtime.factory import build_runtime_engine
from app.runtime.persistence.checkpoint_store import CheckpointStore
from app.runtime.persistence.outbox_publisher import EventOutboxPublisher
from app.runtime.persistence.provider_call_store import ProviderCallStore
from app.runtime.persistence.run_store import RunStore
from app.runtime.redis_notify import RedisRuntimeNotifier
from app.runtime.versioning.compatibility import CompatibilityPolicy

logger = logging.getLogger(__name__)


class RuntimeSupervisor:
    def __init__(self, *, owner: str | None = None) -> None:
        settings = get_settings()
        self.sessionmaker = get_sessionmaker()
        self.owner = owner or f"{socket.gethostname()}:{id(self)}"
        self.notifier = RedisRuntimeNotifier(settings.REDIS_URL)
        self._stopped = False
        self._tasks: list[asyncio.Task[None]] = []
        self._worker_wakeup = asyncio.Event()
        self.worker = RuntimeWorker(
            self.sessionmaker,
            self._execute_claim,
            owner=self.owner,
            lease_seconds=30.0,
        )
        self.publisher = EventOutboxPublisher(
            self.sessionmaker,
            self.notifier.publish_event,
            owner=f"{self.owner}:outbox",
        )

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._worker_loop(), name="securehub-runtime-worker"),
            asyncio.create_task(self._publisher_loop(), name="securehub-runtime-outbox"),
            asyncio.create_task(self._redis_run_listener(), name="securehub-runtime-redis-wakeup"),
        ]

    async def stop(self) -> None:
        self._stopped = True
        self.worker.stop()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self.notifier.close()

    async def notify(self, run_id: Any) -> None:
        # A locally-created root should not wait for the next scanner tick.
        # Redis is only the cross-process acceleration path below.
        self._worker_wakeup.set()
        await self.notifier.notify_run(run_id)

    async def _execute_claim(self, run: Any, lease: Lease, session: Any) -> None:
        engine = build_runtime_engine(session)
        if run.status != "queued":
            recovery = RecoveryService(
                RunStore(session),
                CheckpointStore(session),
                ProviderCallStore(session),
                compatibility_policy=CompatibilityPolicy(),
            )
            decision = await recovery.prepare_resume(
                run,
                lease,
                target_semantic_version=self._target_semantic_version(engine, run),
            )
            if decision.action != "resume":
                await session.commit()
                return
        await engine.execute(run.id, lease_owner=lease.owner)

    @staticmethod
    def _target_semantic_version(engine: Any, run: Any) -> RuntimeSemanticVersion | None:
        """Build the only acceptable resume target from the registered definition.

        Unknown/malformed workflows continue to RuntimeEngine, which records
        the normal INVALID_WORKFLOW failure. Known workflows must compare their
        frozen semantic identifiers before any resumed side effect can run.
        """
        try:
            version = int(str(run.workflow_version or "1").removeprefix("v"))
            definition = engine.workflow_registry.get(run.workflow_name, version)
        except Exception:  # RuntimeEngine owns the user-visible invalid-workflow result.
            return None
        return RuntimeSemanticVersion(
            workflow_definition_digest=definition.definition_digest,
            catalog_version=definition.catalog_version,
            provider_policy_version=definition.provider_policy_version,
            checkpoint_schema_version=definition.checkpoint_schema_version,
            runtime_build_sha=engine.runtime_build_sha,
        )

    async def _worker_loop(self) -> None:
        while not self._stopped:
            try:
                did_work = await self.worker.run_once()
                if not did_work:
                    await self._wait_for_worker_wakeup()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # unreachable DB/Redis must not kill scanner guarantees
                logger.warning("runtime worker loop recovered from error: %s", exc)
                await asyncio.sleep(1.0)

    async def _redis_run_listener(self) -> None:
        """Turn Redis notifications into an early scan, never into a claim."""
        while not self._stopped:
            try:
                await self.notifier.listen_runs(
                    self._on_redis_run_notification,
                    stop_requested=lambda: self._stopped,
                )
                if not self._stopped:
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # Redis loss only falls back to the DB scanner.
                logger.debug("runtime redis wake-up listener recovered: %s", exc)
                await asyncio.sleep(0.5)

    async def _on_redis_run_notification(self, _payload: str) -> None:
        self._worker_wakeup.set()

    async def _wait_for_worker_wakeup(self) -> None:
        try:
            await asyncio.wait_for(self._worker_wakeup.wait(), timeout=0.25)
        except TimeoutError:
            pass
        finally:
            # A duplicated/lost notification only changes latency. The next
            # PostgreSQL scan is still guaranteed by the timeout above.
            self._worker_wakeup.clear()

    async def _publisher_loop(self) -> None:
        while not self._stopped:
            try:
                published = await self.publisher.publish_once()
                if not published:
                    await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # publisher retries from durable outbox
                logger.warning("runtime outbox loop recovered from error: %s", exc)
                await asyncio.sleep(1.0)


__all__ = ["RuntimeSupervisor"]
