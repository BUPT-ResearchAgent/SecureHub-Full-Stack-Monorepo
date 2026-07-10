# Status: partial-real

"""Process-local lifecycle registry for workflow runs and SSE observation.

The registry deliberately does not introduce a ``workflow_runs`` table.  It
keeps a bounded event history for replay and gives every active SSE subscriber
its own queue, so one observer never consumes another observer's trace.
Completed runs are pruned after a configurable TTL; process restarts do not
restore this state.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4


TERMINAL_STATUSES = frozenset({"succeeded", "failed", "blocked", "cancelled"})
ACTIVE_STATUSES = frozenset({"queued", "running", "cancelling"})


class WorkflowRunNotFound(KeyError):
    pass


class WorkflowRunNotActive(RuntimeError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_terminal_event(event: dict[str, Any]) -> bool:
    return event.get("event") == "done" or (
        event.get("event") == "error" and bool(event.get("_terminal"))
    )


@dataclass
class _Subscriber:
    queue: asyncio.Queue[dict[str, Any]]


@dataclass
class WorkflowNodeRecord:
    node_id: str
    agent_name: str
    skill_name: str
    status: str = "pending"
    agent_run_id: UUID | None = None
    persistence: str = "registry"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    quality_score: float | None = None
    evidence_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_name": self.agent_name,
            "skill_name": self.skill_name,
            "status": self.status,
            "agent_run_id": self.agent_run_id,
            "persistence": self.persistence,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "quality_score": self.quality_score,
            "evidence_count": self.evidence_count,
        }


@dataclass
class WorkflowRunRecord:
    run_id: UUID
    workflow: str
    user_id: str
    mode: str
    provider: str
    model: str | None
    input_payload: dict[str, Any]
    nodes: dict[str, WorkflowNodeRecord]
    status: str = "queued"
    created_at: datetime = field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    final_output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancellation_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    event_history: deque[dict[str, Any]] = field(default_factory=deque, repr=False)
    subscribers: dict[UUID, _Subscriber] = field(default_factory=dict, repr=False)
    event_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    next_event_id: int = 1
    task: asyncio.Task[None] | None = field(default=None, repr=False)

    def as_dict(self) -> dict[str, Any]:
        children = [node.as_dict() for node in self.nodes.values()]
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "status": self.status,
            "mode": self.mode,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancellation_event.is_set(),
            "child_runs": children,
            "child_run_count": len(children),
            "final_output": self.final_output,
            "error": self.error,
        }


class RunRegistry:
    """Single-process run registry with bounded SSE replay and fan-out."""

    def __init__(
        self,
        *,
        event_history_limit: int = 2048,
        subscriber_queue_limit: int = 256,
        completed_ttl_seconds: int = 3600,
    ) -> None:
        if event_history_limit < 1:
            raise ValueError("event_history_limit must be positive")
        if subscriber_queue_limit < 1:
            raise ValueError("subscriber_queue_limit must be positive")
        if completed_ttl_seconds < 1:
            raise ValueError("completed_ttl_seconds must be positive")

        self._runs: dict[UUID, WorkflowRunRecord] = {}
        self._lock = asyncio.Lock()
        self._event_history_limit = event_history_limit
        self._subscriber_queue_limit = subscriber_queue_limit
        self._completed_ttl = timedelta(seconds=completed_ttl_seconds)

    async def create(
        self,
        *,
        workflow: str,
        user_id: str,
        mode: str,
        provider: str,
        model: str | None,
        input_payload: dict[str, Any],
        nodes: Iterable[tuple[str, str, str]],
    ) -> WorkflowRunRecord:
        record = WorkflowRunRecord(
            run_id=uuid4(),
            workflow=workflow,
            user_id=user_id,
            mode=mode,
            provider=provider,
            model=model,
            input_payload=dict(input_payload),
            nodes={
                node_id: WorkflowNodeRecord(
                    node_id=node_id,
                    agent_name=agent_name,
                    skill_name=skill_name,
                )
                for node_id, agent_name, skill_name in nodes
            },
            event_history=deque(maxlen=self._event_history_limit),
        )
        async with self._lock:
            self._cleanup_expired_locked()
            self._runs[record.run_id] = record
        return record

    async def cleanup_expired(self) -> int:
        """Discard terminal, unsubscribed records after the configured TTL."""
        async with self._lock:
            return self._cleanup_expired_locked()

    def _cleanup_expired_locked(self) -> int:
        cutoff = _utcnow() - self._completed_ttl
        expired = [
            run_id
            for run_id, record in self._runs.items()
            if record.finished_at is not None
            and record.finished_at < cutoff
            and not record.subscribers
        ]
        for run_id in expired:
            del self._runs[run_id]
        return len(expired)

    async def get(self, run_id: UUID) -> WorkflowRunRecord:
        async with self._lock:
            record = self._runs.get(run_id)
        if record is None:
            raise WorkflowRunNotFound(str(run_id))
        return record

    async def snapshot(self, run_id: UUID) -> dict[str, Any]:
        return (await self.get(run_id)).as_dict()

    async def active_count(self, *, mode: str | None = None) -> int:
        async with self._lock:
            return sum(
                1
                for record in self._runs.values()
                if record.status in ACTIVE_STATUSES and (mode is None or record.mode == mode)
            )

    async def attach_task(self, run_id: UUID, task: asyncio.Task[None]) -> None:
        record = await self.get(run_id)
        record.task = task

    async def mark_running(self, run_id: UUID) -> bool:
        record = await self.get(run_id)
        if record.cancellation_event.is_set():
            record.status = "cancelling"
            return False
        record.status = "running"
        record.started_at = record.started_at or _utcnow()
        return True

    async def begin_node(self, run_id: UUID, node_id: str) -> bool:
        record = await self.get(run_id)
        if record.cancellation_event.is_set():
            return False
        node = record.nodes[node_id]
        node.status = "running"
        node.started_at = _utcnow()
        return True

    async def record_node_result(
        self,
        run_id: UUID,
        node_id: str,
        *,
        status: str,
        agent_run_id: UUID | None = None,
        persistence: str | None = None,
        duration_ms: int | None = None,
        quality_score: float | None = None,
        evidence_count: int = 0,
    ) -> None:
        record = await self.get(run_id)
        node = record.nodes[node_id]
        node.status = {"success": "succeeded", "blocked": "failed"}.get(status, status)
        node.agent_run_id = agent_run_id or node.agent_run_id
        if persistence is not None:
            node.persistence = persistence
        node.duration_ms = duration_ms
        node.quality_score = quality_score
        node.evidence_count = evidence_count
        if node.status in {"succeeded", "failed", "cancelled", "skipped"}:
            node.finished_at = _utcnow()

    async def request_cancel(self, run_id: UUID) -> WorkflowRunRecord:
        record = await self.get(run_id)
        if record.status not in ACTIVE_STATUSES:
            raise WorkflowRunNotActive(record.status)
        record.cancellation_event.set()
        if record.status != "cancelled":
            record.status = "cancelling"
        return record

    async def mark_cancelled(self, run_id: UUID) -> None:
        record = await self.get(run_id)
        record.cancellation_event.set()
        record.status = "cancelled"
        record.finished_at = _utcnow()
        for node in record.nodes.values():
            if node.status == "running":
                node.status = "cancelled"
                node.finished_at = record.finished_at
            elif node.status == "pending":
                node.status = "skipped"
                node.finished_at = record.finished_at

    async def mark_succeeded(self, run_id: UUID, final_output: dict[str, Any]) -> None:
        record = await self.get(run_id)
        record.status = "succeeded"
        record.final_output = final_output
        record.finished_at = _utcnow()

    async def mark_failed(
        self,
        run_id: UUID,
        *,
        code: str,
        message: str,
        blocked: bool = False,
    ) -> None:
        record = await self.get(run_id)
        record.status = "blocked" if blocked else "failed"
        record.error = {"code": code, "message": message}
        record.finished_at = _utcnow()

    async def publish(self, run_id: UUID, event: dict[str, Any]) -> None:
        """Append one event to history and fan it out to active subscribers."""
        record = await self.get(run_id)
        async with record.event_lock:
            payload = dict(event)
            payload["event_id"] = record.next_event_id
            record.next_event_id += 1
            record.event_history.append(payload)
            terminal = _is_terminal_event(payload)
            for subscriber in record.subscribers.values():
                self._enqueue_subscriber_event(subscriber.queue, payload, terminal=terminal)

    def _enqueue_subscriber_event(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        event: dict[str, Any],
        *,
        terminal: bool,
    ) -> None:
        try:
            queue.put_nowait(dict(event))
            return
        except asyncio.QueueFull:
            pass

        if terminal:
            while True:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        else:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(dict(event))

    async def iter_events(
        self,
        run_id: UUID,
        *,
        after_event_id: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay retained events after a cursor, then stream a private fan-out queue."""
        if after_event_id is not None and after_event_id < 0:
            raise ValueError("after_event_id must be non-negative")

        record = await self.get(run_id)
        cursor = after_event_id or 0
        subscriber_id = uuid4()
        subscriber = _Subscriber(
            queue=asyncio.Queue(maxsize=self._subscriber_queue_limit),
        )

        async with record.event_lock:
            replay = [
                dict(event)
                for event in record.event_history
                if int(event["event_id"]) > cursor
            ]
            terminal_exists = any(_is_terminal_event(event) for event in record.event_history)
            if not terminal_exists:
                record.subscribers[subscriber_id] = subscriber

        try:
            for event in replay:
                cursor = max(cursor, int(event["event_id"]))
                yield event
                if _is_terminal_event(event):
                    return

            if terminal_exists:
                return

            while True:
                event = await subscriber.queue.get()
                event_id = int(event["event_id"])
                if event_id <= cursor:
                    continue

                if event_id > cursor + 1:
                    async with record.event_lock:
                        recovery = [
                            dict(item)
                            for item in record.event_history
                            if cursor < int(item["event_id"]) <= event_id
                        ]
                    for recovered in recovery:
                        recovered_id = int(recovered["event_id"])
                        if recovered_id <= cursor:
                            continue
                        cursor = recovered_id
                        yield recovered
                        if _is_terminal_event(recovered):
                            return
                    if event_id <= cursor:
                        continue

                cursor = event_id
                yield dict(event)
                if _is_terminal_event(event):
                    return
        finally:
            async with record.event_lock:
                record.subscribers.pop(subscriber_id, None)


def _global_registry() -> RunRegistry:
    from app.core.config import get_settings

    settings = get_settings()
    return RunRegistry(
        event_history_limit=settings.AGENT_RUN_EVENT_HISTORY_LIMIT,
        subscriber_queue_limit=settings.AGENT_RUN_EVENT_SUBSCRIBER_QUEUE_LIMIT,
        completed_ttl_seconds=settings.AGENT_RUN_COMPLETED_TTL_SECONDS,
    )


GLOBAL_RUN_REGISTRY = _global_registry()
