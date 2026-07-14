# Status: real

"""Append-only per-run events and Transactional Outbox operations."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models.workflow_runtime import WorkflowEvent, WorkflowRun
from app.runtime.contracts import EventEnvelope, SSE_EVENT_TYPES
from app.runtime.persistence.common import (
    EventValidationError,
    LeaseFencedError,
    RunNotFoundError,
    as_uuid,
    compact_error,
    enum_value,
    optional_uuid,
    utcnow,
    validate_event_payload,
)


class EventStore:
    """Owns the only durable public event stream.

    Methods flush but do not commit unless an outbox publisher explicitly
    commits a claim. This lets ``RunStore`` place a lifecycle CAS and an event
    allocation in one caller-owned database transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append_event(
        self,
        workflow_run_id: UUID | str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        step_attempt_id: UUID | str | None = None,
        agent_run_id: UUID | str | None = None,
        provider_call_id: UUID | str | None = None,
        lease_epoch: int | None = None,
        publish_ready: bool = True,
    ) -> WorkflowEvent:
        """Atomically allocate ``next_event_sequence`` then append one event."""
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        event_name = enum_value(event_type)
        if event_name not in SSE_EVENT_TYPES:
            raise EventValidationError(f"unsupported SSE event type: {event_name!r}")
        safe_payload = validate_event_payload(payload or {})

        # A terminal event is a durable convergence barrier. No later token or
        # artifact can become visible after it, even when an old provider task
        # continues in memory.
        terminal_exists = await self.session.scalar(
            select(WorkflowEvent.id)
            .where(
                WorkflowEvent.workflow_run_id == run_id,
                WorkflowEvent.event_type.in_(("done", "error")),
            )
            .limit(1)
        )
        if terminal_exists is not None:
            raise EventValidationError("cannot append an event after terminal convergence")

        where = [WorkflowRun.id == run_id]
        if lease_epoch is not None:
            where.extend(
                (
                    WorkflowRun.lease_epoch == lease_epoch,
                    WorkflowRun.lease_expires_at.is_not(None),
                    WorkflowRun.lease_expires_at > utcnow(),
                )
            )
        allocated = await self.session.execute(
            update(WorkflowRun)
            .where(*where)
            .values(next_event_sequence=WorkflowRun.next_event_sequence + 1)
            .execution_options(synchronize_session=False)
            .returning((WorkflowRun.next_event_sequence - 1).label("sequence"))
        )
        sequence = allocated.scalar_one_or_none()
        if sequence is None:
            exists_run = await self.session.get(WorkflowRun, run_id)
            if exists_run is None:
                raise RunNotFoundError(str(run_id))
            raise LeaseFencedError(
                f"event append fenced for run={run_id} epoch={lease_epoch}"
            )

        event = WorkflowEvent(
            id=uuid4(),
            workflow_run_id=run_id,
            sequence=int(sequence),
            event_type=event_name,
            payload=safe_payload,
            step_attempt_id=optional_uuid(step_attempt_id, field="step_attempt_id"),
            agent_run_id=optional_uuid(agent_run_id, field="agent_run_id"),
            provider_call_id=optional_uuid(provider_call_id, field="provider_call_id"),
            publish_ready_at=utcnow() if publish_ready else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def replay_events(
        self,
        workflow_run_id: UUID | str,
        *,
        after_sequence: int | None = None,
        limit: int = 512,
        ready_only: bool = True,
    ) -> list[WorkflowEvent]:
        if limit < 1:
            raise ValueError("limit must be positive")
        cursor = after_sequence or 0
        if cursor < 0:
            raise ValueError("after_sequence must be non-negative")
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_run_id == run_id, WorkflowEvent.sequence > cursor)
            .order_by(WorkflowEvent.sequence.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        if not ready_only:
            return rows

        # A staged artifact deliberately has an allocated sequence but remains
        # invisible until activation. Filtering it in SQL would expose later
        # ready rows and make an SSE client observe e.g. 1, 3. Return only the
        # contiguous ready prefix; PostgreSQL replay can then fill the gap once
        # ArtifactSaga activates or orphan recovery publishes the trace fact.
        visible: list[WorkflowEvent] = []
        for row in rows:
            if row.publish_ready_at is None:
                break
            visible.append(row)
        return visible

    async def event_envelope(self, event: WorkflowEvent) -> EventEnvelope:
        payload = dict(event.payload or {})
        # Artifact/recovery events intentionally carry only their own fact.
        # The root remains the authority for execution mode and requested
        # provider, so every one of the fixed SSE event types still exposes a
        # stable envelope contract without duplicating root metadata at each
        # producer.
        run = await self.session.get(WorkflowRun, event.workflow_run_id)
        return EventEnvelope(
            workflow_run_id=event.workflow_run_id,
            sequence=event.sequence,
            event_type=event.event_type,
            payload=payload,
            created_at=event.created_at or utcnow(),
            mode=payload.get("mode") or (run.mode if run is not None else None),
            requested_provider=payload.get("requested_provider") or (
                run.requested_provider if run is not None else None
            ),
            requested_model=payload.get("requested_model") or (
                run.requested_model if run is not None else None
            ),
            actual_provider=payload.get("actual_provider"),
            actual_model=payload.get("actual_model"),
        )

    async def mark_publish_ready(self, event_id: UUID | str) -> bool:
        result = await self.session.execute(
            update(WorkflowEvent)
            .where(
                WorkflowEvent.id == as_uuid(event_id, field="event_id"),
                WorkflowEvent.published_at.is_(None),
            )
            .values(publish_ready_at=utcnow())
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def claim_publishable(
        self,
        owner: str,
        *,
        batch_size: int = 32,
        lease_seconds: float = 30.0,
    ) -> list[WorkflowEvent]:
        """Claim at most one earliest event per root, preserving run order.

        PostgreSQL receives ``FOR UPDATE SKIP LOCKED``. SQLite ignores the
        lock clause but is still protected by the conditional update used for
        each candidate, which is sufficient for its single-writer test mode.
        """
        if not owner.strip() or batch_size < 1 or lease_seconds <= 0:
            raise ValueError("invalid outbox claim parameters")
        now = utcnow()
        prior = aliased(WorkflowEvent)
        ready = and_(
            WorkflowEvent.published_at.is_(None),
            WorkflowEvent.publish_ready_at.is_not(None),
            WorkflowEvent.publish_ready_at <= now,
            or_(WorkflowEvent.next_publish_at.is_(None), WorkflowEvent.next_publish_at <= now),
            or_(
                WorkflowEvent.publish_lease_expires_at.is_(None),
                WorkflowEvent.publish_lease_expires_at <= now,
            ),
        )
        no_earlier_unpublished = ~exists(
            select(prior.id).where(
                prior.workflow_run_id == WorkflowEvent.workflow_run_id,
                prior.sequence < WorkflowEvent.sequence,
                prior.published_at.is_(None),
            )
        )
        stmt = (
            select(WorkflowEvent)
            .where(ready, no_earlier_unpublished)
            .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.sequence.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        candidates = list((await self.session.execute(stmt)).scalars().all())
        claimed: list[WorkflowEvent] = []
        expiry = now + timedelta(seconds=lease_seconds)
        for candidate in candidates:
            result = await self.session.execute(
                update(WorkflowEvent)
                .where(
                    WorkflowEvent.id == candidate.id,
                    WorkflowEvent.published_at.is_(None),
                    or_(
                        WorkflowEvent.publish_lease_expires_at.is_(None),
                        WorkflowEvent.publish_lease_expires_at <= now,
                    ),
                )
                .values(
                    publish_lease_owner=owner,
                    publish_lease_expires_at=expiry,
                    publish_attempts=WorkflowEvent.publish_attempts + 1,
                )
                .returning(WorkflowEvent.id)
            )
            if result.scalar_one_or_none() is None:
                continue
            row = await self.session.get(WorkflowEvent, candidate.id, populate_existing=True)
            if row is not None:
                claimed.append(row)
        await self.session.flush()
        return claimed

    async def mark_published(self, event_id: UUID | str, *, owner: str) -> bool:
        now = utcnow()
        result = await self.session.execute(
            update(WorkflowEvent)
            .where(
                WorkflowEvent.id == as_uuid(event_id, field="event_id"),
                WorkflowEvent.published_at.is_(None),
                WorkflowEvent.publish_lease_owner == owner,
            )
            .values(
                published_at=now,
                publish_lease_owner=None,
                publish_lease_expires_at=None,
                next_publish_at=None,
                last_publish_error=None,
            )
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def mark_publish_failed(
        self,
        event_id: UUID | str,
        *,
        owner: str,
        error: BaseException | str,
        retry_after_seconds: float,
    ) -> bool:
        if retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be non-negative")
        now = utcnow()
        result = await self.session.execute(
            update(WorkflowEvent)
            .where(
                WorkflowEvent.id == as_uuid(event_id, field="event_id"),
                WorkflowEvent.published_at.is_(None),
                WorkflowEvent.publish_lease_owner == owner,
            )
            .values(
                publish_lease_owner=None,
                publish_lease_expires_at=None,
                next_publish_at=now + timedelta(seconds=retry_after_seconds),
                last_publish_error=compact_error(error),
            )
        )
        await self.session.flush()
        return bool(result.rowcount)


__all__ = ["EventStore"]
