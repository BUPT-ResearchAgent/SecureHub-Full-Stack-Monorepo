# Status: real

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings
from app.services.storage.providers.base import StorageProvider
from app.services.storage.providers.cos import CosStorageProvider
from app.services.storage.providers.local import LocalStorageProvider


def create_storage_provider(
    settings: Settings | None = None,
    *,
    local_root: Path | None = None,
) -> StorageProvider:
    settings = settings or get_settings()
    provider = settings.STORAGE_PROVIDER.strip().lower()
    if provider == "local":
        return LocalStorageProvider(local_root or settings.STORAGE_LOCAL_ROOT)
    if provider == "cos":
        return CosStorageProvider(settings)
    raise NotImplementedError(f"unsupported storage provider: {provider}")
