# Status: real

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.storage.storage_object import StorageObject
from app.repositories.base import UUIDPKRepository


class StorageObjectRepository(UUIDPKRepository[StorageObject]):
    """P0 methods per task brief §5.2. Provider-agnostic — local / minio /
    s3 / oss / cos / r2.
    """

    model = StorageObject

    async def get_by_key(self, object_key: str) -> StorageObject | None:
        result = await self.session.execute(
            select(StorageObject).where(StorageObject.object_key == object_key)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        storage_id: UUID,
        object_key: str,
        provider: str = "local",
        bucket: str | None = None,
        original_filename: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        content_hash: str | None = None,
        status: str = "ready",
        metadata: dict[str, Any] | None = None,
    ) -> StorageObject:
        row = StorageObject(
            id=storage_id,
            provider=provider,
            bucket=bucket,
            object_key=object_key,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status=status,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
