# Status: real

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


class StorageProviderError(RuntimeError):
    """Provider-level failure with sanitized, non-secret diagnostics."""


class StorageObjectNotFound(StorageProviderError):
    """Raised when a provider operation requires an object that does not exist."""


@runtime_checkable
class StorageProvider(Protocol):
    provider_name: str
    bucket: str | None

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None: ...

    async def get_bytes(self, object_key: str) -> bytes | None: ...

    async def delete(self, object_key: str) -> None: ...

    async def exists(self, object_key: str) -> bool: ...

    async def presigned_url(
        self,
        object_key: str,
        *,
        method: str = "GET",
        expires_in: int = 600,
    ) -> str | None: ...
