# Status: real

"""Provider call journal with started/completed/unknown recovery semantics."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowProviderCall, WorkflowRun
from app.runtime.persistence.common import (
    LeaseFencedError,
    RunNotFoundError,
    as_uuid,
    compact_error,
    lease_is_active,
    mapping,
    optional_uuid,
    utcnow,
)


_ALLOWED_STATUSES = frozenset({"started", "completed", "unknown"})
_ALLOWED_OUTCOMES = frozenset(
    {"success", "unavailable", "cancelled", "superseded", "known_error"}
)
_FORBIDDEN_RESPONSE_KEYS = frozenset(
    {"prompt", "messages", "content", "text", "response", "raw_response", "reasoning", "reasoning_content"}
)


class ProviderCallStore:
    """Journals provider boundaries without claiming external exactly-once."""

    def __init__(self, session: AsyncSession, *, commit_started_calls: bool = True) -> None:
        self.session = session
        self.commit_started_calls = commit_started_calls

    async def start(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> WorkflowProviderCall:
        """Persist ``started`` before the caller crosses the Provider boundary.

        The default commit is intentional: a crash after this method returns
        must recover to an auditable unknown outcome rather than repeat an
        opaque billable request. Callers with an explicit durable transaction
        can set ``commit=False`` and commit the transaction before calling out.
        """
        data = dict(payload or {})
        data.update(kwargs)
        status = str(data.get("status") or "started")
        if status != "started":
            raise ValueError("a provider call must begin with status=started")
        workflow_run_id = as_uuid(data.get("workflow_run_id"), field="workflow_run_id")
        lease_epoch = data.get("lease_epoch")
        if lease_epoch is not None:
            await self._assert_active_lease(workflow_run_id, int(lease_epoch))
        record = WorkflowProviderCall(
            id=optional_uuid(data.get("id") or data.get("provider_call_id"), field="provider_call_id") or uuid4(),
            workflow_run_id=workflow_run_id,
            step_attempt_id=optional_uuid(data.get("step_attempt_id"), field="step_attempt_id"),
            agent_run_id=optional_uuid(data.get("agent_run_id"), field="agent_run_id"),
            attempt=int(data.get("attempt") or 1),
            stream_attempt=int(data.get("stream_attempt") or 1),
            provider=str(data.get("provider") or "unknown"),
            model=str(data.get("model") or "unknown"),
            provider_policy_version=str(data.get("provider_policy_version") or "v1"),
            request_digest=str(data.get("request_digest") or ""),
            provider_request_id=(str(data["provider_request_id"]) if data.get("provider_request_id") else None),
            status="started",
            response_ref=self._response_ref(data.get("response_ref")),
        )
        if not record.request_digest:
            raise ValueError("request_digest is required; raw prompts are never persisted")
        self.session.add(record)
        await self.session.flush()
        if bool(data.get("commit", self.commit_started_calls)):
            await self.session.commit()
        return record

    async def create_started(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> WorkflowProviderCall:
        return await self.start(payload, **kwargs)

    async def create(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> WorkflowProviderCall:
        return await self.start(payload, **kwargs)

    async def complete(
        self,
        provider_call_id: UUID | str | None = None,
        *,
        call_id: UUID | str | None = None,
        outcome: str,
        usage: dict[str, Any] | None = None,
        response_ref: dict[str, Any] | None = None,
        response_digest: str | None = None,
        provider_request_id: str | None = None,
        lease_epoch: int | None = None,
    ) -> WorkflowProviderCall:
        target = as_uuid(provider_call_id or call_id, field="provider_call_id")
        outcome_name = str(outcome)
        if outcome_name not in _ALLOWED_OUTCOMES:
            raise ValueError(f"unsupported provider outcome: {outcome_name!r}")
        existing = await self._current_call(target)
        if existing is None:
            raise KeyError(str(target))
        if existing.status == "completed":
            # Replaying completion after a local crash is harmless only when
            # it does not rewrite the historical provider outcome/response.
            if existing.outcome != outcome_name:
                raise ValueError("completed provider call outcome is immutable")
            return existing
        if existing.status != "started":
            raise ValueError(f"cannot complete provider call in status={existing.status!r}")
        if lease_epoch is not None:
            await self._assert_active_lease(existing.workflow_run_id, int(lease_epoch))
        now = utcnow()
        values: dict[str, Any] = {
            "status": "completed",
            "outcome": outcome_name,
            "usage": mapping(usage or {}, field="usage"),
            "completed_at": now,
            "updated_at": now,
        }
        if response_ref is not None:
            values["response_ref"] = self._response_ref(response_ref)
        if response_digest is not None:
            values["response_digest"] = str(response_digest)
        if provider_request_id is not None:
            values["provider_request_id"] = str(provider_request_id)
        where = [
            WorkflowProviderCall.id == target,
            WorkflowProviderCall.status == "started",
        ]
        if lease_epoch is not None:
            where.append(
                WorkflowProviderCall.workflow_run_id.in_(
                    select(WorkflowRun.id).where(
                        WorkflowRun.lease_epoch == int(lease_epoch),
                        WorkflowRun.lease_expires_at.is_not(None),
                        WorkflowRun.lease_expires_at > now,
                    )
                )
            )
        result = await self.session.execute(
            update(WorkflowProviderCall)
            .where(*where)
            .values(**values)
            .returning(WorkflowProviderCall)
        )
        completed = result.scalar_one_or_none()
        if completed is None:
            raise KeyError(str(target))
        await self.session.flush()
        return completed

    async def mark_completed(self, *args: Any, **kwargs: Any) -> WorkflowProviderCall:
        return await self.complete(*args, **kwargs)

    async def mark_unknown(
        self,
        provider_call_id: UUID | str | None = None,
        *,
        call_id: UUID | str | None = None,
        error_message: str | None = None,
        lease_epoch: int | None = None,
    ) -> WorkflowProviderCall:
        target = as_uuid(provider_call_id or call_id, field="provider_call_id")
        existing = await self._current_call(target)
        if existing is None:
            raise KeyError(str(target))
        if lease_epoch is not None:
            await self._assert_active_lease(existing.workflow_run_id, int(lease_epoch))
        now = utcnow()
        unknown_ref = {"recovery_note": compact_error(error_message) or "provider outcome is unknown"}
        where = [WorkflowProviderCall.id == target, WorkflowProviderCall.status == "started"]
        if lease_epoch is not None:
            where.append(
                WorkflowProviderCall.workflow_run_id.in_(
                    select(WorkflowRun.id).where(
                        WorkflowRun.lease_epoch == int(lease_epoch),
                        WorkflowRun.lease_expires_at.is_not(None),
                        WorkflowRun.lease_expires_at > now,
                    )
                )
            )
        result = await self.session.execute(
            update(WorkflowProviderCall)
            .where(*where)
            .values(
                status="unknown",
                outcome=None,
                unknown_at=now,
                response_ref=unknown_ref,
                updated_at=now,
            )
            .returning(WorkflowProviderCall)
        )
        unknown = result.scalar_one_or_none()
        if unknown is None:
            row = await self.session.get(WorkflowProviderCall, target)
            if row is None:
                raise KeyError(str(target))
            return row
        await self.session.flush()
        return unknown

    async def unknown(self, *args: Any, **kwargs: Any) -> WorkflowProviderCall:
        return await self.mark_unknown(*args, **kwargs)

    async def add_visible_tokens(
        self,
        provider_call_id: UUID | str,
        count: int = 1,
        *,
        lease_epoch: int | None = None,
    ) -> bool:
        if count < 1:
            raise ValueError("count must be positive")
        target = as_uuid(provider_call_id, field="provider_call_id")
        existing = await self._current_call(target)
        if existing is None:
            raise KeyError(str(target))
        if lease_epoch is not None:
            await self._assert_active_lease(existing.workflow_run_id, int(lease_epoch))
        where = [
            WorkflowProviderCall.id == target,
            WorkflowProviderCall.status == "started",
        ]
        if lease_epoch is not None:
            where.append(
                WorkflowProviderCall.workflow_run_id.in_(
                    select(WorkflowRun.id).where(
                        WorkflowRun.lease_epoch == int(lease_epoch),
                        WorkflowRun.lease_expires_at.is_not(None),
                        WorkflowRun.lease_expires_at > utcnow(),
                    )
                )
            )
        result = await self.session.execute(
            update(WorkflowProviderCall)
            .where(*where)
            .values(visible_token_count=WorkflowProviderCall.visible_token_count + count, updated_at=utcnow())
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def get(self, provider_call_id: UUID | str) -> WorkflowProviderCall | None:
        return await self._current_call(as_uuid(provider_call_id, field="provider_call_id"))

    async def list_started_for_run(
        self, workflow_run_id: UUID | str, *, older_than_seconds: float | None = None
    ) -> list[WorkflowProviderCall]:
        stmt = select(WorkflowProviderCall).where(
            WorkflowProviderCall.workflow_run_id == as_uuid(workflow_run_id, field="workflow_run_id"),
            WorkflowProviderCall.status == "started",
        )
        if older_than_seconds is not None:
            stmt = stmt.where(WorkflowProviderCall.started_at <= utcnow() - timedelta(seconds=older_than_seconds))
        return list((await self.session.execute(stmt)).scalars().all())

    async def mark_started_unknown_for_run(
        self, workflow_run_id: UUID | str, *, reason: str = "process recovery"
    ) -> list[WorkflowProviderCall]:
        rows = await self.list_started_for_run(workflow_run_id)
        return [await self.mark_unknown(row.id, error_message=reason) for row in rows]

    async def list_completed_success_for_run(
        self, workflow_run_id: UUID | str
    ) -> list[WorkflowProviderCall]:
        result = await self.session.execute(
            select(WorkflowProviderCall)
            .where(
                WorkflowProviderCall.workflow_run_id
                == as_uuid(workflow_run_id, field="workflow_run_id"),
                WorkflowProviderCall.status == "completed",
                WorkflowProviderCall.outcome == "success",
            )
            .order_by(WorkflowProviderCall.started_at.asc())
        )
        return list(result.scalars().all())

    async def completed_success(self, provider_call_id: UUID | str) -> WorkflowProviderCall | None:
        row = await self.get(provider_call_id)
        if row is None or row.status != "completed" or row.outcome != "success":
            return None
        return row

    async def _current_call(self, provider_call_id: UUID) -> WorkflowProviderCall | None:
        return await self.session.get(WorkflowProviderCall, provider_call_id)

    async def _assert_active_lease(self, workflow_run_id: UUID, lease_epoch: int) -> None:
        row = await self.session.execute(
            select(WorkflowRun.lease_epoch, WorkflowRun.lease_expires_at).where(
                WorkflowRun.id == workflow_run_id
            )
        )
        current = row.one_or_none()
        if current is None:
            raise RunNotFoundError(str(workflow_run_id))
        current_epoch, expires_at = current
        if int(current_epoch) != lease_epoch or not lease_is_active(expires_at):
            raise LeaseFencedError(
                f"provider call fenced for run={workflow_run_id} epoch={lease_epoch}"
            )

    @staticmethod
    def _response_ref(value: Any) -> dict[str, Any]:
        result = mapping(value or {}, field="response_ref")
        forbidden = _FORBIDDEN_RESPONSE_KEYS.intersection(str(key).lower() for key in result)
        if forbidden:
            raise ValueError("response_ref may only contain a controlled response reference")
        return result


__all__ = ["ProviderCallStore"]
