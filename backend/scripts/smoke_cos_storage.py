# Status: real

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.services.storage.provider_factory import create_storage_provider


async def main() -> None:
    settings = get_settings()
    if settings.STORAGE_PROVIDER != "cos":
        raise SystemExit("Set STORAGE_PROVIDER=cos before running COS smoke storage.")

    provider = create_storage_provider(settings)
    object_key = f"tmp/smoke/{uuid4().hex}.txt"
    content = f"securehub cos smoke {uuid4().hex}\n".encode("utf-8")
    uploaded = False

    try:
        await provider.put_bytes(
            object_key=object_key,
            content=content,
            mime_type="text/plain; charset=utf-8",
            metadata={"purpose": "smoke"},
        )
        uploaded = True
        print("COS_UPLOAD_OK")

        if not await provider.exists(object_key):
            raise RuntimeError("COS smoke HEAD did not find uploaded object")
        print("COS_HEAD_OK")

        downloaded = await provider.get_bytes(object_key)
        if downloaded != content:
            raise RuntimeError("COS smoke downloaded content mismatch")
        print("COS_DOWNLOAD_OK")

        signed_url = await provider.presigned_url(
            object_key,
            method="GET",
            expires_in=settings.COS_PRESIGNED_EXPIRES_SECONDS,
        )
        if not signed_url:
            raise RuntimeError("COS smoke failed to generate signed URL")
        print("COS_SIGNED_URL_OK")
    finally:
        if uploaded:
            await provider.delete(object_key)
            if await provider.exists(object_key):
                raise RuntimeError("COS smoke object still exists after delete")
            print("COS_DELETE_OK")


if __name__ == "__main__":
    asyncio.run(main())
