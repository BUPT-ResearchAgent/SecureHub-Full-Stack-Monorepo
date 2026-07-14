# Status: real

"""Retention cleanup for Artifact Saga orphan tombstones."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.storage.storage_object import StorageObject
from app.runtime.artifacts.saga import ArtifactStorageProvider
from app.runtime.persistence.common import utcnow


class ArtifactCleanup:
    def __init__(self, session: AsyncSession, storage: ArtifactStorageProvider) -> None:
        self.session = session
        self.provider = getattr(storage, "provider", storage)

    async def cleanup_orphaned(self, *, older_than_seconds: float, limit: int = 100) -> dict[str, int]:
        if older_than_seconds < 0 or limit < 1:
            raise ValueError("invalid cleanup parameters")
        cutoff = utcnow() - timedelta(seconds=older_than_seconds)
        rows = list(
            (
                await self.session.execute(
                    select(StorageObject)
                    .where(
                        StorageObject.status == "orphaned",
                        StorageObject.orphaned_at.is_not(None),
                        StorageObject.orphaned_at <= cutoff,
                    )
                    .order_by(StorageObject.orphaned_at.asc())
                    .limit(limit)
                )
            ).scalars().all()
        )
        deleted = 0
        failed = 0
        for row in rows:
            try:
                await self.provider.delete(row.staging_key or row.object_key)
            except Exception:  # noqa: BLE001 - preserve orphan for later retry
                failed += 1
                continue
            row.status = "deleted"
            row.deleted_at = utcnow()
            deleted += 1
        await self.session.flush()
        return {"scanned": len(rows), "deleted": deleted, "failed": failed}


__all__ = ["ArtifactCleanup"]
