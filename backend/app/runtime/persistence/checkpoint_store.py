# Status: real

"""Fenced checkpoints owned exclusively by RuntimeEngine."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowCheckpoint, WorkflowRun
from app.runtime.persistence.common import LeaseFencedError, RunNotFoundError, as_uuid, lease_is_active, mapping, utcnow


_FORBIDDEN_STATE_KEYS = frozenset(
    {
        "prompt",
        "full_prompt",
        "messages",
        "reasoning",
        "reasoning_content",
        "raw_model_output",
        "api_key",
        "authorization",
    }
)


class CheckpointStore:
    """Writes version-pinned state only while the caller holds the root lease."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        payload: dict[str, Any] | None = None,
        *,
        workflow_run_id: UUID | str | None = None,
        checkpoint_seq: int | None = None,
        state_json: dict[str, Any] | None = None,
        event_cursor: int = 0,
        lease_epoch: int | None = None,
        **kwargs: Any,
    ) -> WorkflowCheckpoint:
        data = dict(payload or {})
        data.update(kwargs)
        run_id = as_uuid(workflow_run_id or data.get("workflow_run_id"), field="workflow_run_id")
        epoch = lease_epoch if lease_epoch is not None else data.get("lease_epoch")
        if epoch is None or int(epoch) < 1:
            raise ValueError("checkpoint writes require a positive lease_epoch")
        state = mapping(state_json if state_json is not None else data.get("state_json", {}), field="state_json")
        self._assert_safe_state(state)

        # Lock/read the durable root before deriving version fields. PostgreSQL
        # receives a row lock; SQLite's single-writer semantics cover tests.
        root = await self.session.scalar(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .with_for_update()
        )
        if root is None:
            raise RunNotFoundError(str(run_id))
        if (
            root.lease_epoch != int(epoch)
            or not lease_is_active(root.lease_expires_at)
        ):
            raise LeaseFencedError(
                f"checkpoint write fenced for run={run_id}: inactive epoch={epoch}"
            )
        sequence = checkpoint_seq if checkpoint_seq is not None else data.get("checkpoint_seq")
        if sequence is None:
            sequence = int(
                await self.session.scalar(
                    select(func.coalesce(func.max(WorkflowCheckpoint.checkpoint_seq), 0)).where(
                        WorkflowCheckpoint.workflow_run_id == run_id
                    )
                )
                or 0
            ) + 1
        sequence = int(sequence)
        if sequence < 1:
            raise ValueError("checkpoint_seq must be positive")

        checkpoint = WorkflowCheckpoint(
            id=uuid4(),
            workflow_run_id=run_id,
            checkpoint_seq=sequence,
            workflow_definition_digest=str(
                data.get("workflow_definition_digest") or root.workflow_definition_digest
            ),
            catalog_version=str(data.get("catalog_version") or root.catalog_version),
            checkpoint_schema_version=str(
                data.get("checkpoint_schema_version") or root.checkpoint_schema_version
            ),
            runtime_build_sha=str(data.get("runtime_build_sha") or root.runtime_build_sha),
            state_json=state,
            event_cursor=int(data.get("event_cursor", event_cursor)),
            lease_epoch=int(epoch),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(checkpoint)
                await self.session.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"checkpoint already exists for run={run_id} sequence={sequence}"
            ) from exc
        return checkpoint

    async def save_checkpoint(self, *args: Any, **kwargs: Any) -> WorkflowCheckpoint:
        return await self.save(*args, **kwargs)

    async def latest(self, workflow_run_id: UUID | str) -> WorkflowCheckpoint | None:
        result = await self.session.execute(
            select(WorkflowCheckpoint)
            .where(
                WorkflowCheckpoint.workflow_run_id
                == as_uuid(workflow_run_id, field="workflow_run_id")
            )
            .order_by(WorkflowCheckpoint.checkpoint_seq.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_run(self, workflow_run_id: UUID | str) -> list[WorkflowCheckpoint]:
        result = await self.session.execute(
            select(WorkflowCheckpoint)
            .where(
                WorkflowCheckpoint.workflow_run_id
                == as_uuid(workflow_run_id, field="workflow_run_id")
            )
            .order_by(WorkflowCheckpoint.checkpoint_seq.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _assert_safe_state(state: dict[str, Any]) -> None:
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if str(key).lower() in _FORBIDDEN_STATE_KEYS:
                        raise ValueError(f"checkpoint contains forbidden field: {key!r}")
                    walk(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    walk(child)

        walk(state)


__all__ = ["CheckpointStore"]
