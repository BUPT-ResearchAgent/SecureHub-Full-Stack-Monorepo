# Status: real

"""Recovery scanner for interrupted Artifact Saga activations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.storage.storage_object import StorageObject
from app.runtime.artifacts.saga import ArtifactSaga, ArtifactStorageProvider


class ArtifactRecovery:
    def __init__(self, session: AsyncSession, storage: ArtifactStorageProvider) -> None:
        self.session = session
        self.saga = ArtifactSaga(session, storage)

    async def recover_staging(self, *, limit: int = 100) -> dict[str, int]:
        rows = list(
            (
                await self.session.execute(
                    select(StorageObject)
                    .where(StorageObject.status == "staging")
                    .order_by(StorageObject.created_at.asc())
                    .limit(limit)
                )
            ).scalars().all()
        )
        activated = 0
        orphaned = 0
        for row in rows:
            try:
                await self.saga.activate(row.id)
                activated += 1
            except Exception:  # noqa: BLE001 - saga records the durable failure
                orphaned += 1
        await self.session.flush()
        return {"scanned": len(rows), "activated": activated, "orphaned": orphaned}


__all__ = ["ArtifactRecovery"]
