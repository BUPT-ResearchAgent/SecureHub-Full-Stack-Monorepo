# Status: real

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path


class LocalStorageProvider:
    provider_name = "local"
    bucket: str | None = None

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _resolve_path(self, object_key: str) -> Path:
        if not object_key.strip():
            raise ValueError("object_key must be non-empty")
        target = (self.root / object_key).resolve()
        root = self.root.resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"object_key escapes local storage root: {object_key}")
        return target

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        path = self._resolve_path(object_key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        await asyncio.to_thread(_write)

    async def get_bytes(self, object_key: str) -> bytes | None:
        path = self._resolve_path(object_key)

        def _read() -> bytes | None:
            if not path.exists() or not path.is_file():
                return None
            return path.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, object_key: str) -> None:
        path = self._resolve_path(object_key)

        def _delete() -> None:
            if path.exists() and path.is_file():
                path.unlink()

        await asyncio.to_thread(_delete)

    async def exists(self, object_key: str) -> bool:
        path = self._resolve_path(object_key)
        return await asyncio.to_thread(path.is_file)

    async def presigned_url(
        self,
        object_key: str,
        *,
        method: str = "GET",
        expires_in: int = 600,
    ) -> str | None:
        path = self._resolve_path(object_key)
        if not await asyncio.to_thread(path.exists):
            return None
        return path.as_uri()
