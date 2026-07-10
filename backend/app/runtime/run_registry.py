# Status: partial-real

"""In-memory lifecycle registry for active workflow runs.

Agent-Run-1 deliberately avoids a ``workflow_runs`` migration.  The registry
keeps active status, cancellation state, replayable SSE history, and child-run
trace metadata while the existing ``agent_runs`` table remains the persistence
target for real skill executions.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    event_queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=asyncio.Queue,
        repr=False,
    )
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
    """Registry scoped to one process; it is intentionally not restart-safe."""

    def __init__(self) -> None:
        self._runs: dict[UUID, WorkflowRunRecord] = {}
        self._lock = asyncio.Lock()

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
        )
        async with self._lock:
            self._runs[record.run_id] = record
        return record

    async def get(self, run_id: UUID) -> WorkflowRunRecord:
        async with self._lock:
            record = self._runs.get(run_id)
        if record is None:
            raise WorkflowRunNotFound(str(run_id))
        return record

    async def snapshot(self, run_id: UUID) -> dict[str, Any]:
        return (await self.get(run_id)).as_dict()

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
        persistence: str = "registry",
        duration_ms: int | None = None,
        quality_score: float | None = None,
        evidence_count: int = 0,
    ) -> None:
        record = await self.get(run_id)
        node = record.nodes[node_id]
        node.status = {"success": "succeeded", "blocked": "failed"}.get(status, status)
        node.agent_run_id = agent_run_id or node.agent_run_id
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
        record = await self.get(run_id)
        await record.event_queue.put(dict(event))

    async def iter_events(self, run_id: UUID) -> AsyncIterator[dict[str, Any]]:
        record = await self.get(run_id)
        while True:
            event = await record.event_queue.get()
            yield dict(event)
            if _is_terminal_event(event):
                return


GLOBAL_RUN_REGISTRY = RunRegistry()
