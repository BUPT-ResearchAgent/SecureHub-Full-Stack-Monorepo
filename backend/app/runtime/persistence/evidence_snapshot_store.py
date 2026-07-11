# Status: real

"""Immutable evidence snapshots for durable RAG provenance."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.runtime.persistence.common import (
    as_snapshot_mapping,
    as_uuid,
    mapping,
    optional_uuid,
)


class EvidenceSnapshotStore:
    """Persists only the cited excerpt and provenance, never a full corpus copy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_many(
        self,
        records: Iterable[dict[str, Any]] | None = None,
        *,
        snapshots: Iterable[dict[str, Any]] | None = None,
    ) -> list[WorkflowEvidenceSnapshot]:
        items = list(records if records is not None else snapshots or ())
        result: list[WorkflowEvidenceSnapshot] = []
        for record in items:
            result.append(self._new_snapshot(record))
        self.session.add_all(result)
        await self.session.flush()
        return result

    async def create_many(
        self,
        records: Iterable[dict[str, Any]] | None = None,
        *,
        snapshots: Iterable[dict[str, Any]] | None = None,
    ) -> list[WorkflowEvidenceSnapshot]:
        return await self.save_many(records, snapshots=snapshots)

    async def create_snapshots(
        self,
        snapshots: Iterable[dict[str, Any]],
    ) -> list[WorkflowEvidenceSnapshot]:
        return await self.save_many(snapshots=snapshots)

    async def save(self, record: dict[str, Any]) -> WorkflowEvidenceSnapshot:
        return (await self.save_many([record]))[0]

    async def list_for_run(
        self,
        workflow_run_id: UUID | str,
        *,
        step_attempt_id: UUID | str | None = None,
    ) -> list[WorkflowEvidenceSnapshot]:
        stmt = (
            select(WorkflowEvidenceSnapshot)
            .where(WorkflowEvidenceSnapshot.workflow_run_id == as_uuid(workflow_run_id, field="workflow_run_id"))
            .order_by(WorkflowEvidenceSnapshot.rank.asc().nulls_last(), WorkflowEvidenceSnapshot.created_at.asc())
        )
        if step_attempt_id is not None:
            stmt = stmt.where(
                WorkflowEvidenceSnapshot.step_attempt_id
                == optional_uuid(step_attempt_id, field="step_attempt_id")
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, snapshot_id: UUID | str) -> WorkflowEvidenceSnapshot | None:
        return await self.session.get(
            WorkflowEvidenceSnapshot, as_uuid(snapshot_id, field="snapshot_id")
        )

    @staticmethod
    def _new_snapshot(record: dict[str, Any]) -> WorkflowEvidenceSnapshot:
        data = dict(record)
        excerpt = data.get("excerpt")
        if excerpt is not None:
            excerpt = str(excerpt)[:4_000]
        digest = data.get("content_digest")
        if not digest:
            digest = hashlib.sha256((excerpt or "").encode("utf-8")).hexdigest()
        return WorkflowEvidenceSnapshot(
            id=optional_uuid(data.get("id"), field="id") or uuid4(),
            workflow_run_id=as_uuid(data.get("workflow_run_id"), field="workflow_run_id"),
            step_attempt_id=optional_uuid(data.get("step_attempt_id"), field="step_attempt_id"),
            agent_run_id=optional_uuid(data.get("agent_run_id"), field="agent_run_id"),
            chunk_id=(str(data["chunk_id"]) if data.get("chunk_id") is not None else None),
            document_id=(str(data["document_id"]) if data.get("document_id") is not None else None),
            chunk_version=(str(data["chunk_version"]) if data.get("chunk_version") else None),
            content_digest=str(digest),
            excerpt=excerpt,
            citation=as_snapshot_mapping(data.get("citation")),
            source=as_snapshot_mapping(data.get("source")),
            rights=as_snapshot_mapping(data.get("rights")),
            rank=(int(data["rank"]) if data.get("rank") is not None else None),
        )


__all__ = ["EvidenceSnapshotStore"]
