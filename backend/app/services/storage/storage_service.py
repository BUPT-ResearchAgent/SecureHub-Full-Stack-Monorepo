# Status: real

"""Per task brief §6 — StorageService is the provider abstraction layer over
``storage_objects.provider`` (local / minio / s3 / oss / cos / r2). Callers
only deal in ``object_key`` and bytes; the service decides where to put them.
"""

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.storage_objects import StorageObjectRepository


class StorageService:
    def __init__(self, session: AsyncSession, *, local_root: Path | None = None) -> None:
        self.session = session
        self.local_root = local_root or Path(__file__).resolve().parents[4] / "data" / "storage"

    def _resolve_local_path(self, object_key: str) -> Path:
        target = (self.local_root / object_key).resolve()
        root = self.local_root.resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"object_key escapes local storage root: {object_key}")
        return target

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        provider: str = "local",
        bucket: str | None = None,
        mime_type: str | None = None,
        original_filename: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if provider != "local":
            raise NotImplementedError("P0 StorageService only supports provider='local'")

        path = self._resolve_local_path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

        content_hash = sha256(content).hexdigest()
        repo = StorageObjectRepository(self.session)
        existing = await repo.get_by_key(object_key)
        if existing is None:
            await repo.create(
                storage_id=uuid4(),
                object_key=object_key,
                provider=provider,
                bucket=bucket,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=len(content),
                content_hash=content_hash,
                status="ready",
                metadata=metadata,
            )
            return

        existing.provider = provider
        existing.bucket = bucket
        existing.original_filename = original_filename
        existing.mime_type = mime_type
        existing.size_bytes = len(content)
        existing.content_hash = content_hash
        existing.status = "ready"
        if metadata is not None:
            existing.metadata_ = dict(metadata)
        await self.session.flush()

    async def get_bytes(self, object_key: str) -> bytes | None:
        path = self._resolve_local_path(object_key)
        if not path.exists() or not path.is_file():
            return None
        return path.read_bytes()

    async def presigned_url(
        self, object_key: str, *, expires_in: int = 3600
    ) -> str | None:
        path = self._resolve_local_path(object_key)
        if not path.exists():
            return None
        return path.as_uri()
