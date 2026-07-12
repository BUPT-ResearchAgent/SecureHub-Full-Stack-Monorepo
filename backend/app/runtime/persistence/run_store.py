# Status: real

"""Fenced durable root and step-attempt persistence operations."""

from __future__ import annotations

from datetime import timedelta
from collections.abc import Callable
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowRun, WorkflowStepAttempt
from app.runtime.persistence.common import (
    LeaseFencedError,
    PersistenceConflictError,
    RunNotFoundError,
    as_uuid,
    enum_value,
    lease_is_active,
    mapping,
    optional_uuid,
    utcnow,
)
from app.runtime.persistence.event_store import EventStore


_ACTIVE_OR_RECOVERABLE = ("queued", "running", "reworking", "pausing", "cancelling")
_TERMINAL = frozenset({"succeeded", "failed", "blocked", "cancelled"})
_RUN_MUTABLE_FIELDS = frozenset(
    {
        "status",
        "output_ref",
        "budget",
        "error",
        "requested_provider",
        "requested_model",
        "cancel_requested_at",
        "lease_owner",
        "lease_expires_at",
        "started_at",
        "finished_at",
    }
)
_STEP_MUTABLE_FIELDS = frozenset(
    {
        "status",
        "agent_run_id",
        "input_ref",
        "output_ref",
        "quality",
        "quality_score",
        "error_code",
        "error",
        "started_at",
        "finished_at",
        "duration_ms",
    }
)


class RunStore:
    """The PostgreSQL truth for root, step and lease state.

    The store deliberately does not validate lifecycle graphs. RuntimeEngine is
    the only production caller allowed to use SecureHubStateMachine. This layer
    only enforces state-version and lease-epoch compare-and-swap semantics.
    """

    def __init__(self, session: AsyncSession, *, event_store: EventStore | None = None) -> None:
        self.session = session
        self.events = event_store or EventStore(session)

    async def create_run(
        self,
        payload: dict[str, Any] | None = None,
        *,
        return_created: bool = False,
        **kwargs: Any,
    ) -> WorkflowRun | tuple[WorkflowRun, bool]:
        """Create an idempotent durable root without starting execution."""
        data = dict(payload or {})
        data.update(kwargs)
        workflow_name = str(data.get("workflow_name") or data.get("workflow") or "").strip()
        if not workflow_name:
            raise ValueError("workflow_name is required")
        mode = enum_value(data.get("mode", "real"))
        if mode not in {"real", "fixture"}:
            raise ValueError("mode must be real or fixture")
        user_id = optional_uuid(data.get("user_id"), field="user_id")
        idempotency_key = data.get("idempotency_key")
        if idempotency_key is not None:
            idempotency_key = str(idempotency_key).strip()
            if not idempotency_key:
                idempotency_key = None
            elif len(idempotency_key) > 128:
                raise ValueError("idempotency_key exceeds 128 characters")

        if idempotency_key is not None:
            existing = await self._find_idempotent_run(user_id, workflow_name, idempotency_key)
            if existing is not None:
                return (existing, False) if return_created else existing

        run = WorkflowRun(
            id=optional_uuid(data.get("id"), field="id") or uuid4(),
            workflow_name=workflow_name,
            workflow_version=str(data.get("workflow_version") or data.get("version") or "v1"),
            workflow_definition_digest=str(data.get("workflow_definition_digest") or ""),
            catalog_version=str(data.get("catalog_version") or "v1"),
            provider_policy_version=str(data.get("provider_policy_version") or "v1"),
            checkpoint_schema_version=str(data.get("checkpoint_schema_version") or "v1"),
            runtime_build_sha=str(data.get("runtime_build_sha") or "unknown"),
            user_id=user_id,
            status=enum_value(data.get("status", "queued")),
            mode=mode,
            requested_provider=(str(data["requested_provider"]) if data.get("requested_provider") else None),
            requested_model=(str(data["requested_model"]) if data.get("requested_model") else None),
            input_payload=mapping(data.get("input_payload", data.get("input", {})), field="input_payload"),
            output_ref=mapping(data.get("output_ref", {}), field="output_ref"),
            budget=mapping(data.get("budget", {}), field="budget"),
            error=mapping(data.get("error", {}), field="error"),
            idempotency_key=idempotency_key,
        )
        try:
            # Savepoint lets a duplicate idempotency race recover without
            # rolling back unrelated root/event work in the caller's session.
            async with self.session.begin_nested():
                self.session.add(run)
                await self.session.flush()
        except IntegrityError:
            if idempotency_key is None:
                raise
            existing = await self._find_idempotent_run(user_id, workflow_name, idempotency_key)
            if existing is None:
                raise
            return (existing, False) if return_created else existing
        return (run, True) if return_created else run

    async def get_run(self, workflow_run_id: UUID | str, *, required: bool = True) -> WorkflowRun | None:
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        # A long-lived worker session must observe pause/cancel/approval
        # decisions committed by a control-plane session. ``session.get`` can
        # otherwise return a stale identity-map instance indefinitely.
        run = await self.session.scalar(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .execution_options(populate_existing=True)
        )
        if run is None and required:
            raise RunNotFoundError(str(workflow_run_id))
        return run

    async def list_runs(
        self,
        *,
        statuses: Iterable[str] | None = None,
        user_id: UUID | str | None = None,
        limit: int = 100,
    ) -> list[WorkflowRun]:
        if limit < 1:
            raise ValueError("limit must be positive")
        stmt = select(WorkflowRun).order_by(WorkflowRun.created_at.asc()).limit(limit)
        if statuses is not None:
            names = [enum_value(status) for status in statuses]
            stmt = stmt.where(WorkflowRun.status.in_(names))
        if user_id is not None:
            stmt = stmt.where(WorkflowRun.user_id == as_uuid(user_id, field="user_id"))
        return list((await self.session.execute(stmt)).scalars().all())

    async def claim_next(
        self,
        owner: str,
        lease_seconds: float = 30.0,
        *,
        statuses: Iterable[str] | None = None,
    ) -> WorkflowRun | None:
        """Atomically claim an unleased queued or expired recoverable root."""
        if not owner.strip() or lease_seconds <= 0:
            raise ValueError("owner and positive lease_seconds are required")
        names = tuple(enum_value(status) for status in (statuses or _ACTIVE_OR_RECOVERABLE))
        if not names:
            return None
        now = utcnow()
        expiry = now + timedelta(seconds=lease_seconds)
        # The short retry loop handles a concurrent candidate being claimed
        # between SELECT and fenced UPDATE without requiring Redis correctness.
        for _ in range(4):
            # Claiming does not immediately change a root to ``running``: the
            # worker must first enter RuntimeEngine. Treating every queued row
            # as claimable would therefore allow a second worker to steal the
            # short queued-to-running window despite a fresh lease.
            queued = and_(
                WorkflowRun.status == "queued",
                or_(
                    WorkflowRun.lease_expires_at.is_(None),
                    WorkflowRun.lease_expires_at <= now,
                ),
            )
            expired_active = and_(
                WorkflowRun.status.in_(tuple(name for name in names if name != "queued")),
                or_(
                    WorkflowRun.lease_expires_at.is_(None),
                    WorkflowRun.lease_expires_at <= now,
                ),
            )
            stmt = (
                select(WorkflowRun)
                .where(WorkflowRun.status.in_(names), or_(queued, expired_active))
                .order_by(WorkflowRun.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            candidate = (await self.session.execute(stmt)).scalar_one_or_none()
            if candidate is None:
                return None
            result = await self.session.execute(
                update(WorkflowRun)
                .where(
                    WorkflowRun.id == candidate.id,
                    WorkflowRun.state_version == candidate.state_version,
                    WorkflowRun.status.in_(names),
                    or_(queued, expired_active),
                )
                .values(
                    lease_owner=owner,
                    lease_expires_at=expiry,
                    lease_epoch=WorkflowRun.lease_epoch + 1,
                    state_version=WorkflowRun.state_version + 1,
                    updated_at=now,
                )
                # The candidate was loaded above. On SQLite, evaluating the
                # timezone-aware lease predicate against its naive hydrated
                # datetime raises before SQL executes after a worker restart.
                # The returned row is authoritative, so no identity-map
                # evaluation is needed here.
                .execution_options(synchronize_session=False)
                .returning(WorkflowRun.id)
            )
            claimed_id = result.scalar_one_or_none()
            if claimed_id is not None:
                # `synchronize_session=False` deliberately leaves the
                # candidate's identity-map instance stale. Reload through the
                # store's populate-existing path before exposing the claimed
                # root to RuntimeEngine.
                claimed = await self.get_run(claimed_id)
                assert claimed is not None
                await self.session.flush()
                return claimed
        return None

    async def renew_lease(
        self,
        workflow_run_id: UUID | str,
        owner: str,
        epoch: int,
        lease_seconds: float = 30.0,
    ) -> WorkflowRun:
        if not owner.strip() or epoch < 1 or lease_seconds <= 0:
            raise ValueError("invalid lease renewal arguments")
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        now = utcnow()
        result = await self.session.execute(
            update(WorkflowRun)
            .where(
                WorkflowRun.id == run_id,
                WorkflowRun.lease_owner == owner,
                WorkflowRun.lease_epoch == epoch,
                WorkflowRun.lease_expires_at.is_not(None),
                WorkflowRun.lease_expires_at > now,
            )
            .values(lease_expires_at=now + timedelta(seconds=lease_seconds), updated_at=now)
            .returning(WorkflowRun)
        )
        renewed = result.scalar_one_or_none()
        if renewed is None:
            await self._raise_fenced_or_missing(run_id, epoch)
        await self.session.flush()
        assert renewed is not None
        return renewed

    async def mutate_budget(
        self,
        workflow_run_id: UUID | str,
        *,
        lease_epoch: int,
        mutate: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> WorkflowRun:
        """Apply one fenced budget-ledger mutation under the root row lock.

        A fan-out branch must not use the root lifecycle CAS merely to update
        accounting: sibling branches legitimately share an epoch, but not a
        stale ``state_version``.  The root row lock serialises the ledger while
        preserving the StateMachine as the only owner of lifecycle changes.
        """
        if lease_epoch < 1:
            raise ValueError("budget mutations require a positive lease_epoch")
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        root = await self.session.scalar(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if root is None:
            raise RunNotFoundError(str(run_id))
        if root.lease_epoch != lease_epoch or not lease_is_active(root.lease_expires_at):
            raise LeaseFencedError(
                f"budget mutation fenced for run={run_id} epoch={lease_epoch}"
            )
        root.budget = mapping(mutate(dict(root.budget or {})), field="budget")
        root.updated_at = utcnow()
        await self.session.flush()
        return root

    async def transition_run(
        self,
        workflow_run_id: UUID | str,
        *,
        expected_state_version: int,
        lease_epoch: int | None,
        status: str | None = None,
        changes: dict[str, Any] | None = None,
        event_type: str | None = None,
        event_payload: dict[str, Any] | None = None,
        step_attempt_id: UUID | str | None = None,
        agent_run_id: UUID | str | None = None,
        provider_call_id: UUID | str | None = None,
        publish_ready: bool = True,
    ) -> WorkflowRun:
        """Fenced root CAS plus optional same-transaction outbox event."""
        if expected_state_version < 0:
            raise ValueError("expected_state_version must be non-negative")
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        values = self._run_values(status=status, changes=changes)
        now = utcnow()
        values["state_version"] = WorkflowRun.state_version + 1
        values["updated_at"] = now
        target_status = values.get("status")
        if target_status == "running":
            values.setdefault("started_at", now)
        if target_status in _TERMINAL:
            values.setdefault("finished_at", now)

        where = [WorkflowRun.id == run_id, WorkflowRun.state_version == expected_state_version]
        if lease_epoch is not None:
            # An epoch by itself is not sufficient once its lease has elapsed:
            # a worker that wakes up before a replacement claim must still be
            # fenced out.  Control-plane writes deliberately pass ``None``
            # here, because they persist user intent rather than worker work.
            where.extend(
                (
                    WorkflowRun.lease_epoch == lease_epoch,
                    WorkflowRun.lease_expires_at.is_not(None),
                    WorkflowRun.lease_expires_at > now,
                )
            )
        async with self.session.begin_nested():
            result = await self.session.execute(
                update(WorkflowRun)
                .where(*where)
                .values(**values)
                # SQLite returns naive values for timezone columns. Let the
                # database evaluate the lease predicate rather than asking
                # SQLAlchemy's in-memory evaluator to compare them to UTC.
                .execution_options(synchronize_session=False, populate_existing=True)
                .returning(WorkflowRun)
            )
            updated = result.scalar_one_or_none()
            if updated is None:
                await self._raise_fenced_or_conflict(run_id, expected_state_version, lease_epoch)
            if event_type is not None:
                await self.events.append_event(
                    run_id,
                    event_type,
                    event_payload or {},
                    step_attempt_id=step_attempt_id,
                    agent_run_id=agent_run_id,
                    provider_call_id=provider_call_id,
                    lease_epoch=lease_epoch,
                    publish_ready=publish_ready,
                )
        await self.session.flush()
        assert updated is not None
        return updated

    async def request_cancel(
        self,
        workflow_run_id: UUID | str,
        *,
        event_payload: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Idempotently persist cancel intent; a worker converges the terminal state."""
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        existing = await self.get_run(run_id)
        assert existing is not None
        if existing.status in _TERMINAL:
            return existing
        # Repair a pre-v1.1 cancel intent that was persisted while the root
        # stayed `running`. Repeating cancel remains idempotent but upgrades
        # that legacy state to the legal cancelling transition.
        if existing.cancel_requested_at is not None:
            if existing.status == "cancelling":
                return existing
            result = await self.session.execute(
                update(WorkflowRun)
                .where(
                    WorkflowRun.id == run_id,
                    WorkflowRun.state_version == existing.state_version,
                    WorkflowRun.status.not_in(_TERMINAL),
                )
                .values(status="cancelling", state_version=WorkflowRun.state_version + 1, updated_at=utcnow())
                .returning(WorkflowRun)
            )
            updated = result.scalar_one_or_none()
            if updated is not None:
                await self.events.append_event(
                    run_id,
                    "progress",
                    {"status": "cancelling", "root_status": "cancelling", "cancel_requested": True},
                    publish_ready=True,
                )
                await self.session.flush()
                return updated
            current = await self.get_run(run_id)
            assert current is not None
            return current
        now = utcnow()
        async with self.session.begin_nested():
            result = await self.session.execute(
                update(WorkflowRun)
                .where(
                    WorkflowRun.id == run_id,
                    WorkflowRun.state_version == existing.state_version,
                    WorkflowRun.cancel_requested_at.is_(None),
                    WorkflowRun.status.not_in(_TERMINAL),
                )
                .values(
                    cancel_requested_at=now,
                    # The state machine requires every non-terminal cancel to
                    # converge through cancelling, including an in-flight
                    # running node. Leaving it as running makes the worker's
                    # legal running -> cancelled transition impossible.
                    status="cancelling",
                    state_version=WorkflowRun.state_version + 1,
                    updated_at=now,
                )
                .returning(WorkflowRun)
            )
            updated = result.scalar_one_or_none()
            if updated is not None:
                await self.events.append_event(
                    run_id,
                    "progress",
                    event_payload
                    or {"status": "cancelling", "cancel_requested": True},
                    publish_ready=True,
                )
        if updated is None:
            current = await self.get_run(run_id)
            assert current is not None
            return current
        await self.session.flush()
        return updated

    async def create_step_attempt(
        self,
        payload: dict[str, Any] | None = None,
        *,
        lease_epoch: int | None = None,
        **kwargs: Any,
    ) -> WorkflowStepAttempt:
        """Create or return the idempotent ``(run,node,attempt)`` row."""
        data = dict(payload or {})
        data.update(kwargs)
        run_id = as_uuid(data.get("workflow_run_id"), field="workflow_run_id")
        node_id = str(data.get("node_id") or "").strip()
        attempt = int(data.get("attempt") or 1)
        if not node_id or attempt < 1:
            raise ValueError("node_id and positive attempt are required")
        active_epoch = lease_epoch if lease_epoch is not None else data.get("lease_epoch")
        if active_epoch is not None:
            await self._assert_epoch(run_id, int(active_epoch))
        existing = await self.session.scalar(
            select(WorkflowStepAttempt).where(
                WorkflowStepAttempt.workflow_run_id == run_id,
                WorkflowStepAttempt.node_id == node_id,
                WorkflowStepAttempt.attempt == attempt,
            )
        )
        if existing is not None:
            return existing
        step = WorkflowStepAttempt(
            id=optional_uuid(data.get("id"), field="id") or uuid4(),
            workflow_run_id=run_id,
            node_id=node_id,
            attempt=attempt,
            agent_id=optional_uuid(data.get("agent_id"), field="agent_id"),
            skill_id=optional_uuid(data.get("skill_id"), field="skill_id"),
            agent_name=(str(data["agent_name"]) if data.get("agent_name") else None),
            skill_name=(str(data["skill_name"]) if data.get("skill_name") else None),
            skill_version=(str(data["skill_version"]) if data.get("skill_version") is not None else None),
            skill_definition_digest=(str(data["skill_definition_digest"]) if data.get("skill_definition_digest") else None),
            prompt_version=(str(data["prompt_version"]) if data.get("prompt_version") else None),
            prompt_digest=(str(data["prompt_digest"]) if data.get("prompt_digest") else None),
            agent_run_id=optional_uuid(data.get("agent_run_id"), field="agent_run_id"),
            status=enum_value(data.get("status", "pending")),
            lease_epoch=int(active_epoch or 0),
            input_ref=mapping(data.get("input_ref", {}), field="input_ref"),
            output_ref=mapping(data.get("output_ref", {}), field="output_ref"),
            quality=mapping(data.get("quality", {}), field="quality"),
            quality_score=data.get("quality_score"),
            error_code=(str(data["error_code"]) if data.get("error_code") else None),
            error=mapping(data.get("error", {}), field="error"),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(step)
                await self.session.flush()
        except IntegrityError:
            raced = await self.session.scalar(
                select(WorkflowStepAttempt).where(
                    WorkflowStepAttempt.workflow_run_id == run_id,
                    WorkflowStepAttempt.node_id == node_id,
                    WorkflowStepAttempt.attempt == attempt,
                )
            )
            if raced is None:
                raise
            return raced
        return step

    async def get_step_attempt(
        self, step_attempt_id: UUID | str, *, required: bool = True
    ) -> WorkflowStepAttempt | None:
        step = await self.session.get(
            WorkflowStepAttempt, as_uuid(step_attempt_id, field="step_attempt_id")
        )
        if step is None and required:
            raise KeyError(str(step_attempt_id))
        return step

    async def transition_step_attempt(
        self,
        step_attempt_id: UUID | str,
        *,
        expected_state_version: int,
        lease_epoch: int,
        status: str | None = None,
        changes: dict[str, Any] | None = None,
        event_type: str | None = None,
        event_payload: dict[str, Any] | None = None,
        agent_run_id: UUID | str | None = None,
        provider_call_id: UUID | str | None = None,
        publish_ready: bool = True,
    ) -> WorkflowStepAttempt:
        if expected_state_version < 0 or lease_epoch < 1:
            raise ValueError("expected_state_version and lease_epoch are required")
        step_id = as_uuid(step_attempt_id, field="step_attempt_id")
        values = self._step_values(status=status, changes=changes)
        now = utcnow()
        values["state_version"] = WorkflowStepAttempt.state_version + 1
        values["updated_at"] = now
        target_status = values.get("status")
        if target_status == "running":
            values.setdefault("started_at", now)
        if target_status in {"succeeded", "failed", "blocked", "cancelled", "skipped"}:
            values.setdefault("finished_at", now)

        async with self.session.begin_nested():
            result = await self.session.execute(
                update(WorkflowStepAttempt)
                .where(
                    WorkflowStepAttempt.id == step_id,
                    WorkflowStepAttempt.state_version == expected_state_version,
                    WorkflowStepAttempt.lease_epoch == lease_epoch,
                    WorkflowStepAttempt.workflow_run_id.in_(
                        select(WorkflowRun.id).where(
                            WorkflowRun.lease_epoch == lease_epoch,
                            WorkflowRun.lease_expires_at.is_not(None),
                            WorkflowRun.lease_expires_at > now,
                        )
                    ),
                )
                .values(**values)
                .returning(WorkflowStepAttempt)
            )
            updated = result.scalar_one_or_none()
            if updated is None:
                await self._raise_step_fenced_or_conflict(step_id, expected_state_version, lease_epoch)
            if event_type is not None:
                await self.events.append_event(
                    updated.workflow_run_id,
                    event_type,
                    event_payload or {},
                    step_attempt_id=updated.id,
                    agent_run_id=agent_run_id or updated.agent_run_id,
                    provider_call_id=provider_call_id,
                    lease_epoch=lease_epoch,
                    publish_ready=publish_ready,
                )
        await self.session.flush()
        assert updated is not None
        return updated

    async def adopt_step_attempt(
        self,
        step_attempt_id: UUID | str,
        *,
        lease_epoch: int,
    ) -> WorkflowStepAttempt:
        """Transfer an incomplete step to the currently claimed root epoch.

        This narrow recovery operation is the only cross-epoch mutation. It
        makes a late write from the expired worker fail its step fence while
        preserving the step identity needed to reuse a completed provider
        result.
        """
        if lease_epoch < 1:
            raise ValueError("lease_epoch must be positive")
        step_id = as_uuid(step_attempt_id, field="step_attempt_id")
        current = await self.get_step_attempt(step_id)
        assert current is not None
        if current.lease_epoch == lease_epoch:
            return current
        if current.lease_epoch > lease_epoch:
            raise LeaseFencedError(
                f"step={step_id} belongs to newer epoch={current.lease_epoch}"
            )
        now = utcnow()
        result = await self.session.execute(
            update(WorkflowStepAttempt)
            .where(
                WorkflowStepAttempt.id == step_id,
                WorkflowStepAttempt.lease_epoch < lease_epoch,
                WorkflowStepAttempt.workflow_run_id.in_(
                    select(WorkflowRun.id).where(
                        WorkflowRun.lease_epoch == lease_epoch,
                        WorkflowRun.lease_expires_at.is_not(None),
                        WorkflowRun.lease_expires_at > now,
                    )
                ),
            )
            .values(lease_epoch=lease_epoch, updated_at=now)
            .returning(WorkflowStepAttempt)
        )
        adopted = result.scalar_one_or_none()
        if adopted is None:
            await self._raise_step_fenced_or_conflict(step_id, current.state_version, lease_epoch)
        await self.session.flush()
        assert adopted is not None
        return adopted

    async def _find_idempotent_run(
        self, user_id: UUID | None, workflow_name: str, idempotency_key: str
    ) -> WorkflowRun | None:
        user_clause = WorkflowRun.user_id.is_(None) if user_id is None else WorkflowRun.user_id == user_id
        return await self.session.scalar(
            select(WorkflowRun).where(
                user_clause,
                WorkflowRun.workflow_name == workflow_name,
                WorkflowRun.idempotency_key == idempotency_key,
            )
        )

    async def _assert_epoch(self, run_id: UUID, epoch: int) -> None:
        current = await self.session.execute(
            select(WorkflowRun.lease_epoch, WorkflowRun.lease_expires_at).where(
                WorkflowRun.id == run_id
            )
        )
        row = current.one_or_none()
        if row is None:
            raise RunNotFoundError(str(run_id))
        current_epoch, expires_at = row
        if int(current_epoch) != epoch or not lease_is_active(expires_at):
            raise LeaseFencedError(
                f"run={run_id} lease is not active for epoch={epoch}"
            )

    async def _raise_fenced_or_missing(self, run_id: UUID, epoch: int) -> None:
        run = await self.get_run(run_id, required=False)
        if run is None:
            raise RunNotFoundError(str(run_id))
        raise LeaseFencedError(f"run={run_id} epoch={epoch} is no longer lease owner")

    async def _raise_fenced_or_conflict(
        self, run_id: UUID, expected_state_version: int, lease_epoch: int | None
    ) -> None:
        run = await self.get_run(run_id, required=False)
        if run is None:
            raise RunNotFoundError(str(run_id))
        if lease_epoch is not None and (
            run.lease_epoch != lease_epoch
            or not lease_is_active(run.lease_expires_at)
        ):
            raise LeaseFencedError(
                f"run={run_id} lease epoch {lease_epoch} is no longer active"
            )
        raise PersistenceConflictError(
            f"run={run_id} expected state_version={expected_state_version}, current={run.state_version}"
        )

    async def _raise_step_fenced_or_conflict(
        self, step_id: UUID, expected_state_version: int, lease_epoch: int
    ) -> None:
        step = await self.get_step_attempt(step_id, required=False)
        if step is None:
            raise KeyError(str(step_id))
        await self._assert_epoch(step.workflow_run_id, lease_epoch)
        if step.lease_epoch != lease_epoch:
            raise LeaseFencedError(
                f"step={step_id} lease epoch {lease_epoch} fenced by {step.lease_epoch}"
            )
        raise PersistenceConflictError(
            f"step={step_id} expected state_version={expected_state_version}, current={step.state_version}"
        )

    @staticmethod
    def _run_values(*, status: str | None, changes: dict[str, Any] | None) -> dict[str, Any]:
        values = dict(changes or {})
        if status is not None:
            values["status"] = enum_value(status)
        unknown = set(values).difference(_RUN_MUTABLE_FIELDS)
        if unknown:
            raise ValueError(f"unsupported run mutation fields: {sorted(unknown)!r}")
        for key in ("output_ref", "budget", "error"):
            if key in values:
                values[key] = mapping(values[key], field=key)
        return values

    @staticmethod
    def _step_values(*, status: str | None, changes: dict[str, Any] | None) -> dict[str, Any]:
        values = dict(changes or {})
        if status is not None:
            values["status"] = enum_value(status)
        unknown = set(values).difference(_STEP_MUTABLE_FIELDS)
        if unknown:
            raise ValueError(f"unsupported step mutation fields: {sorted(unknown)!r}")
        for key in ("input_ref", "output_ref", "quality", "error"):
            if key in values:
                values[key] = mapping(values[key], field=key)
        if "agent_run_id" in values:
            values["agent_run_id"] = optional_uuid(values["agent_run_id"], field="agent_run_id")
        return values


__all__ = ["RunStore"]
