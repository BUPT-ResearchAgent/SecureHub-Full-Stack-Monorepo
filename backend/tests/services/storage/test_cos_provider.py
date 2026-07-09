# Status: real

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from qcloud_cos.cos_exception import CosClientError, CosServiceError

from app.core.config import Settings
from app.services.storage.providers.base import StorageProviderError
from app.services.storage.providers.cos import CosStorageProvider


class _Body:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def get_raw_stream(self) -> BytesIO:
        return BytesIO(self.content)


class _FakeCosClient:
    def __init__(self) -> None:
        self.put_kwargs: dict[str, Any] | None = None
        self.deleted: list[dict[str, str]] = []

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        self.put_kwargs = kwargs
        return {"ETag": "etag"}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"Body": _Body(b"downloaded")}

    def head_object(self, **kwargs: Any) -> dict[str, str]:
        return {"Content-Length": "10"}

    def delete_object(self, **kwargs: Any) -> dict[str, str]:
        self.deleted.append(kwargs)
        return {}

    def get_presigned_url(self, **kwargs: Any) -> str:
        return "https://cos.example.invalid/object"


class _MissingCosClient(_FakeCosClient):
    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        raise CosServiceError("GET", "missing", 404)

    def head_object(self, **kwargs: Any) -> dict[str, str]:
        raise CosServiceError("HEAD", "missing", 404)

    def delete_object(self, **kwargs: Any) -> dict[str, str]:
        raise CosServiceError("DELETE", "missing", 404)


class _FailingCosClient(_FakeCosClient):
    def put_object(self, **kwargs: Any) -> dict[str, str]:
        raise CosServiceError("PUT", "access denied", 403)

    def head_object(self, **kwargs: Any) -> dict[str, str]:
        raise CosClientError("network unavailable")


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        STORAGE_PROVIDER="cos",
        STORAGE_LOCAL_ROOT=tmp_path / "storage",
        COS_SECRET_ID="unit-test-id",
        COS_SECRET_KEY="unit-test-key",
        COS_REGION="ap-beijing",
        COS_BUCKET="securehub-test-bucket",
        COS_SCHEME="https",
        COS_UPLOAD_MAX_BYTES=64,
    )


@pytest.mark.anyio
async def test_cos_provider_calls_sdk_without_real_network(tmp_path: Path) -> None:
    client = _FakeCosClient()
    provider = CosStorageProvider(_settings(tmp_path), client=client)

    await provider.put_bytes(
        object_key="tmp/test.txt",
        content=b"hello",
        mime_type="text/plain",
        metadata={"domain": "course_websec"},
    )

    assert client.put_kwargs == {
        "Bucket": "securehub-test-bucket",
        "Key": "tmp/test.txt",
        "Body": b"hello",
        "ContentType": "text/plain",
        "Metadata": {"domain": "course_websec"},
    }
    assert await provider.exists("tmp/test.txt")
    assert await provider.get_bytes("tmp/test.txt") == b"downloaded"
    assert await provider.presigned_url("tmp/test.txt", expires_in=600) == (
        "https://cos.example.invalid/object"
    )
    await provider.delete("tmp/test.txt")
    assert client.deleted == [{"Bucket": "securehub-test-bucket", "Key": "tmp/test.txt"}]


@pytest.mark.anyio
async def test_cos_provider_maps_not_found_to_none_false_and_idempotent_delete(
    tmp_path: Path,
) -> None:
    provider = CosStorageProvider(_settings(tmp_path), client=_MissingCosClient())

    assert await provider.get_bytes("tmp/missing.txt") is None
    assert not await provider.exists("tmp/missing.txt")
    await provider.delete("tmp/missing.txt")


@pytest.mark.anyio
async def test_cos_provider_maps_sdk_errors_without_secrets(tmp_path: Path) -> None:
    provider = CosStorageProvider(_settings(tmp_path), client=_FailingCosClient())

    with pytest.raises(StorageProviderError) as exc_info:
        await provider.put_bytes(object_key="tmp/forbidden.txt", content=b"hello")

    message = str(exc_info.value)
    assert "status=403" in message
    assert "unit-test-id" not in message
    assert "unit-test-key" not in message
    assert "sign=" not in message

    with pytest.raises(StorageProviderError, match="CosClientError"):
        await provider.exists("tmp/network.txt")


@pytest.mark.anyio
async def test_cos_provider_enforces_upload_max_bytes(tmp_path: Path) -> None:
    provider = CosStorageProvider(_settings(tmp_path), client=_FakeCosClient())

    with pytest.raises(StorageProviderError, match="COS_UPLOAD_MAX_BYTES"):
        await provider.put_bytes(object_key="tmp/large.bin", content=b"x" * 65)
