# Status: real

from pathlib import Path

import pytest

from app.services.storage.providers.local import LocalStorageProvider


@pytest.mark.anyio
async def test_local_provider_put_get_exists_presign_delete(tmp_path: Path) -> None:
    provider = LocalStorageProvider(tmp_path)
    object_key = "course/demo.txt"
    content = b"securehub local storage"

    assert not await provider.exists(object_key)

    await provider.put_bytes(
        object_key=object_key,
        content=content,
        mime_type="text/plain",
        metadata={"domain": "course_websec"},
    )

    assert (tmp_path / object_key).read_bytes() == content
    assert await provider.exists(object_key)
    assert await provider.get_bytes(object_key) == content
    signed = await provider.presigned_url(object_key)
    assert signed is not None
    assert signed.startswith("file:")

    await provider.delete(object_key)
    assert not await provider.exists(object_key)
    assert await provider.get_bytes(object_key) is None
    assert await provider.presigned_url(object_key) is None


@pytest.mark.anyio
async def test_local_provider_rejects_directory_traversal(tmp_path: Path) -> None:
    provider = LocalStorageProvider(tmp_path)

    with pytest.raises(ValueError, match="escapes local storage root"):
        await provider.put_bytes(object_key="../escape.txt", content=b"nope")

    assert not (tmp_path.parent / "escape.txt").exists()
