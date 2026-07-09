# Status: real

"""Storage object metadata service over provider-backed binary I/O."""

from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.repositories.storage.storage_objects import StorageObjectRepository
from app.services.storage.provider_factory import create_storage_provider
from app.services.storage.providers.base import StorageProvider
from app.services.storage.providers.local import LocalStorageProvider


class StorageService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        local_root: Path | None = None,
        settings: Settings | None = None,
        storage_provider: StorageProvider | None = None,
    ) -> None:
        self.session = session
        explicit_local_root = local_root is not None
        if explicit_local_root and settings is None and storage_provider is None:
            self.settings = Settings(
                _env_file=None,
                STORAGE_PROVIDER="local",
                STORAGE_LOCAL_ROOT=local_root,
            )
        else:
            self.settings = settings or get_settings()
        self.local_root = local_root or self.settings.STORAGE_LOCAL_ROOT
        if storage_provider is not None:
            self.provider = storage_provider
        elif explicit_local_root and settings is None:
            self.provider = LocalStorageProvider(self.local_root)
        else:
            self.provider = create_storage_provider(
                self.settings,
                local_root=self.local_root,
            )

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        provider: str | None = None,
        bucket: str | None = None,
        mime_type: str | None = None,
        original_filename: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        provider_name = (provider or self.provider.provider_name).strip().lower()
        if provider_name != self.provider.provider_name:
            raise NotImplementedError(
                "StorageService per-call provider override must match the configured "
                f"provider ({self.provider.provider_name!r}); got {provider_name!r}"
            )

        content_hash = sha256(content).hexdigest()
        effective_bucket = bucket if bucket is not None else self.provider.bucket
        await self.provider.put_bytes(
            object_key=object_key,
            content=content,
            mime_type=mime_type,
            metadata=_provider_metadata(metadata),
        )

        repo = StorageObjectRepository(self.session)
        existing = await repo.get_by_key(object_key)
        if existing is None:
            await repo.create(
                storage_id=uuid4(),
                object_key=object_key,
                provider=provider_name,
                bucket=effective_bucket,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=len(content),
                content_hash=content_hash,
                status="ready",
                metadata=metadata,
            )
            return

        existing.provider = provider_name
        existing.bucket = effective_bucket
        existing.original_filename = original_filename
        existing.mime_type = mime_type
        existing.size_bytes = len(content)
        existing.content_hash = content_hash
        existing.status = "ready"
        if metadata is not None:
            existing.metadata_ = dict(metadata)
        await self.session.flush()

    async def get_bytes(self, object_key: str) -> bytes | None:
        return await self.provider.get_bytes(object_key)

    async def exists(self, object_key: str) -> bool:
        return await self.provider.exists(object_key)

    async def delete(self, object_key: str) -> None:
        await self.provider.delete(object_key)

    async def presigned_url(
        self,
        object_key: str,
        *,
        method: str = "GET",
        expires_in: int | None = None,
    ) -> str | None:
        method = method.upper()
        if method in {"GET", "HEAD"} and not await self.provider.exists(object_key):
            return None
        return await self.provider.presigned_url(
            object_key,
            method=method,
            expires_in=expires_in or self.settings.COS_PRESIGNED_EXPIRES_SECONDS,
        )


def _provider_metadata(metadata: Mapping[str, object] | None) -> dict[str, str] | None:
    if not metadata:
        return None
    provider_metadata = {
        str(key): str(value)
        for key, value in metadata.items()
        if value is not None and isinstance(value, str | int | float | bool)
    }
    return provider_metadata or None
