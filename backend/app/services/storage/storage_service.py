# Status: planned

"""Per task brief §6 — StorageService is the provider abstraction layer over
``storage_objects.provider`` (local / minio / s3 / oss / cos / r2). Callers
only deal in ``object_key`` and bytes; the service decides where to put them.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class StorageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        provider: str = "local",
        bucket: str | None = None,
        mime_type: str | None = None,
    ) -> None:
        raise NotImplementedError("planned: P0 — local FS in P0, MinIO in P1")

    async def get_bytes(self, object_key: str) -> bytes | None:
        raise NotImplementedError("planned: P0")

    async def presigned_url(
        self, object_key: str, *, expires_in: int = 3600
    ) -> str | None:
        raise NotImplementedError("planned: P1 — MinIO / S3 only")
