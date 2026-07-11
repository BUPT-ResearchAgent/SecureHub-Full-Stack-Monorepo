# Status: real

"""Durable COS/local Artifact Saga without remote rename assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.storage.storage_object import StorageObject
from app.db.models.workflow_runtime import WorkflowEvent
from app.runtime.persistence.common import as_uuid, mapping, optional_uuid, utcnow, validate_event_payload
from app.runtime.persistence.event_store import EventStore


class ArtifactStorageProvider(Protocol):
    provider_name: str
    bucket: str | None

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None: ...

    async def get_bytes(self, object_key: str) -> bytes | None: ...

    async def exists(self, object_key: str) -> bool: ...

    async def delete(self, object_key: str) -> None: ...


@dataclass(frozen=True, slots=True)
class StagedArtifact:
    storage_object_id: UUID
    resource_id: UUID
    artifact_event_id: UUID
    staging_key: str
    checksum: str


class ArtifactSaga:
    """Stages bytes first, then atomically records metadata and a hidden event.

    Activation is an idempotent DB metadata promotion. It never promises a
    remote object rename, which is not reliably transactional across COS/S3
    compatible providers.
    """

    def __init__(self, session: AsyncSession, storage: ArtifactStorageProvider | Any) -> None:
        self.session = session
        # StorageService exposes its provider; tests and production may also
        # pass a StorageProvider directly.
        self.provider: ArtifactStorageProvider = getattr(storage, "provider", storage)
        self.events = EventStore(session)

    async def stage(
        self,
        *,
        workflow_run_id: UUID | str,
        step_attempt_id: UUID | str | None,
        agent_run_id: UUID | str | None,
        resource_type: str,
        title: str,
        content: bytes,
        resource_content: dict[str, Any] | None = None,
        user_id: UUID | str | None = None,
        course_id: UUID | str | None = None,
        kp_id: UUID | str | None = None,
        evidence_chunk_ids: list[UUID] | None = None,
        quality_score: float | None = None,
        mime_type: str | None = "application/octet-stream",
        object_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        lease_epoch: int | None = None,
    ) -> StagedArtifact:
        if not resource_type.strip() or not title.strip():
            raise ValueError("resource_type and title are required")
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        resource_id = uuid4()
        storage_id = uuid4()
        staging_key = object_key or f"runtime/staging/{run_id}/{resource_id}/artifact.bin"
        checksum = sha256(content).hexdigest()
        provider_metadata = {"checksum": checksum, "resource_id": str(resource_id)}
        await self.provider.put_bytes(
            object_key=staging_key,
            content=content,
            mime_type=mime_type,
            metadata=provider_metadata,
        )

        try:
            async with self.session.begin_nested():
                event = await self.events.append_event(
                    run_id,
                    "artifact",
                    {
                        "resource_id": str(resource_id),
                        "resource_type": resource_type,
                        "title": title,
                        "object_key": staging_key,
                        "storage_status": "active",
                        "quality_score": quality_score,
                    },
                    step_attempt_id=step_attempt_id,
                    agent_run_id=agent_run_id,
                    lease_epoch=lease_epoch,
                    publish_ready=False,
                )
                saga_metadata = validate_event_payload(metadata or {})
                saga_metadata.update(
                    {
                        "artifact_event_id": str(event.id),
                        "workflow_run_id": str(run_id),
                        "resource_id": str(resource_id),
                    }
                )
                storage_object = StorageObject(
                    id=storage_id,
                    provider=str(getattr(self.provider, "provider_name", "unknown")),
                    bucket=getattr(self.provider, "bucket", None),
                    object_key=staging_key,
                    mime_type=mime_type,
                    size_bytes=len(content),
                    content_hash=checksum,
                    staging_key=staging_key,
                    active_key=None,
                    checksum=checksum,
                    status="staging",
                    metadata_=saga_metadata,
                )
                resource = GeneratedResource(
                    id=resource_id,
                    user_id=optional_uuid(user_id, field="user_id"),
                    course_id=optional_uuid(course_id, field="course_id"),
                    kp_id=optional_uuid(kp_id, field="kp_id"),
                    agent_run_id=optional_uuid(agent_run_id, field="agent_run_id"),
                    workflow_run_id=run_id,
                    step_attempt_id=optional_uuid(step_attempt_id, field="step_attempt_id"),
                    version=1,
                    resource_type=resource_type,
                    title=title,
                    content=mapping(resource_content or {}, field="resource_content"),
                    object_key=None,
                    evidence_chunk_ids=list(evidence_chunk_ids or []),
                    quality_score=quality_score,
                    status="staging",
                    metadata_=saga_metadata,
                )
                self.session.add_all((storage_object, resource))
                await self.session.flush()
        except Exception:
            # Best effort only; a remote staging object without a DB row is
            # still discoverable by provider-prefix retention/operations.
            try:
                await self.provider.delete(staging_key)
            except Exception:  # noqa: BLE001
                pass
            raise
        return StagedArtifact(storage_id, resource_id, event.id, staging_key, checksum)

    async def stage_artifact(self, **kwargs: Any) -> StagedArtifact:
        return await self.stage(**kwargs)

    async def activate(
        self,
        storage_object_id: UUID | str,
        *,
        resource_id: UUID | str | None = None,
        artifact_event_id: UUID | str | None = None,
        lease_epoch: int | None = None,
    ) -> StagedArtifact:
        storage_id = as_uuid(storage_object_id, field="storage_object_id")
        storage = await self.session.get(StorageObject, storage_id)
        if storage is None:
            raise KeyError(str(storage_id))
        if storage.status == "active":
            return StagedArtifact(
                storage.id,
                as_uuid((storage.metadata_ or {}).get("resource_id"), field="resource_id"),
                as_uuid((storage.metadata_ or {}).get("artifact_event_id"), field="artifact_event_id"),
                storage.staging_key or storage.object_key,
                storage.checksum or storage.content_hash or "",
            )
        if storage.status != "staging":
            raise ValueError(f"cannot activate storage object in status={storage.status!r}")
        staging_key = storage.staging_key or storage.object_key
        actual = await self.provider.get_bytes(staging_key)
        if actual is None or sha256(actual).hexdigest() != (storage.checksum or storage.content_hash):
            await self.mark_orphaned(storage.id, reason="staging object missing or checksum mismatch")
            raise RuntimeError("artifact staging verification failed")

        metadata = dict(storage.metadata_ or {})
        await self._assert_root_epoch(metadata, lease_epoch)
        resolved_resource_id = optional_uuid(resource_id, field="resource_id") or as_uuid(
            metadata.get("resource_id"), field="resource_id"
        )
        resolved_event_id = optional_uuid(artifact_event_id, field="artifact_event_id") or as_uuid(
            metadata.get("artifact_event_id"), field="artifact_event_id"
        )
        resource = await self.session.get(GeneratedResource, resolved_resource_id)
        if resource is None:
            await self.mark_orphaned(storage.id, reason="generated resource row is missing")
            raise RuntimeError("artifact generated resource is missing")
        now = utcnow()
        async with self.session.begin_nested():
            storage.status = "active"
            storage.active_key = staging_key
            storage.object_key = staging_key
            storage.activated_at = now
            resource.status = "active"
            resource.object_key = staging_key
            if not await self.events.mark_publish_ready(resolved_event_id):
                raise RuntimeError("artifact outbox event is missing or already terminal")
            await self.session.flush()
        return StagedArtifact(storage.id, resource.id, resolved_event_id, staging_key, storage.checksum or "")

    async def activate_artifact(self, *args: Any, **kwargs: Any) -> StagedArtifact:
        return await self.activate(*args, **kwargs)

    async def mark_orphaned(self, storage_object_id: UUID | str, *, reason: str) -> bool:
        """Tombstone a failed staging object and unblock any later error event."""
        storage = await self.session.get(
            StorageObject, as_uuid(storage_object_id, field="storage_object_id")
        )
        if storage is None or storage.status in {"orphaned", "deleted"}:
            return False
        metadata = dict(storage.metadata_ or {})
        now = utcnow()
        storage.status = "orphaned"
        storage.orphaned_at = now
        metadata["orphan_reason"] = str(reason)[:400]
        storage.metadata_ = metadata
        resource_id = optional_uuid(metadata.get("resource_id"), field="resource_id")
        if resource_id is not None:
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is not None:
                resource.status = "failed"
        event_id = optional_uuid(metadata.get("artifact_event_id"), field="artifact_event_id")
        if event_id is not None:
            # A hidden artifact event must not leave a public sequence hole.
            # Convert it to a non-terminal trace fact rather than suppressing
            # it behind the final error event. This preserves contiguous SSE
            # replay without ever claiming that an artifact became active.
            await self.session.execute(
                update(WorkflowEvent)
                .where(WorkflowEvent.id == event_id, WorkflowEvent.published_at.is_(None))
                .values(
                    event_type="trace",
                    payload={
                        "artifact_recovery": "orphaned",
                        "storage_status": "orphaned",
                        "reason": str(reason)[:400],
                    },
                    publish_ready_at=now,
                    last_publish_error=str(reason)[:400],
                )
            )
        await self.session.flush()
        return True

    async def _assert_root_epoch(self, metadata: dict[str, Any], lease_epoch: int | None) -> None:
        if lease_epoch is None:
            return
        from app.db.models.workflow_runtime import WorkflowRun
        from app.runtime.persistence.common import LeaseFencedError, lease_is_active

        run_id = as_uuid(metadata.get("workflow_run_id"), field="workflow_run_id")
        current = await self.session.get(WorkflowRun, run_id)
        if (
            current is None
            or current.lease_epoch != lease_epoch
            or not lease_is_active(current.lease_expires_at)
        ):
            raise LeaseFencedError(
                f"artifact activation fenced for run={run_id} epoch={lease_epoch}"
            )


__all__ = ["ArtifactSaga", "ArtifactStorageProvider", "StagedArtifact"]
