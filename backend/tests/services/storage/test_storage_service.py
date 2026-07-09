# Status: real

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.models.storage.storage_object import StorageObject
from app.services.storage.storage_service import StorageService


class _FakeProvider:
    provider_name = "cos"
    bucket = "securehub-test-bucket"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, Mapping[str, str] | None] = {}

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        self.objects[object_key] = content
        self.metadata[object_key] = metadata

    async def get_bytes(self, object_key: str) -> bytes | None:
        return self.objects.get(object_key)

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    async def exists(self, object_key: str) -> bool:
        return object_key in self.objects

    async def presigned_url(
        self,
        object_key: str,
        *,
        method: str = "GET",
        expires_in: int = 600,
    ) -> str | None:
        return f"https://cos.example.invalid/{object_key}?expires={expires_in}"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        STORAGE_PROVIDER="cos",
        STORAGE_LOCAL_ROOT=tmp_path / "storage",
        COS_SECRET_ID="unit-test-id",
        COS_SECRET_KEY="unit-test-key",
        COS_REGION="ap-beijing",
        COS_BUCKET="securehub-test-bucket",
    )


def test_settings_fail_fast_when_cos_required_values_are_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="COS_SECRET_ID"):
        Settings(
            _env_file=None,
            STORAGE_PROVIDER="cos",
            STORAGE_LOCAL_ROOT=tmp_path / "storage",
            COS_SECRET_ID="",
            COS_SECRET_KEY="",
            COS_REGION="",
            COS_BUCKET="",
        )


@pytest.mark.anyio
async def test_storage_service_local_root_forces_local_provider_when_env_is_cos(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "cos")
    monkeypatch.setenv("COS_SECRET_ID", "unit-test-id")
    monkeypatch.setenv("COS_SECRET_KEY", "unit-test-key")
    monkeypatch.setenv("COS_REGION", "ap-beijing")
    monkeypatch.setenv("COS_BUCKET", "unit-test-bucket")
    get_settings.cache_clear()

    try:
        local_root = tmp_path / "forced-local"
        service = StorageService(sqlite_session, local_root=local_root)
        assert service.provider.provider_name == "local"

        await service.put_bytes(
            object_key="news/test/mindspider_reference/topic.json",
            content=b'{"topic_id":"demo"}',
            mime_type="application/json",
        )
        await sqlite_session.commit()

        assert (local_root / "news/test/mindspider_reference/topic.json").read_bytes() == (
            b'{"topic_id":"demo"}'
        )
        row = (
            await sqlite_session.execute(
                select(StorageObject).where(
                    StorageObject.object_key == "news/test/mindspider_reference/topic.json"
                )
            )
        ).scalar_one()
        assert row.provider == "local"
        assert row.bucket is None
    finally:
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_storage_service_writes_storage_object_fields(
    sqlite_session,
    tmp_path: Path,
) -> None:
    provider = _FakeProvider()
    service = StorageService(
        sqlite_session,
        settings=_settings(tmp_path),
        storage_provider=provider,
    )
    content = b"storage object payload"

    await service.put_bytes(
        object_key="runtime/course/demo.txt",
        content=content,
        mime_type="text/plain",
        original_filename="demo.txt",
        metadata={"domain": "course_websec", "asset_type": "markdown_full"},
    )
    await sqlite_session.commit()

    row = (
        await sqlite_session.execute(
            select(StorageObject).where(StorageObject.object_key == "runtime/course/demo.txt")
        )
    ).scalar_one()

    assert row.provider == "cos"
    assert row.bucket == "securehub-test-bucket"
    assert row.object_key == "runtime/course/demo.txt"
    assert row.mime_type == "text/plain"
    assert row.size_bytes == len(content)
    assert row.content_hash == sha256(content).hexdigest()
    assert row.status == "ready"
    assert row.metadata_ == {"domain": "course_websec", "asset_type": "markdown_full"}
    assert provider.objects["runtime/course/demo.txt"] == content
    assert provider.metadata["runtime/course/demo.txt"] == {
        "domain": "course_websec",
        "asset_type": "markdown_full",
    }


@pytest.mark.anyio
async def test_storage_service_updates_existing_object(
    sqlite_session,
    tmp_path: Path,
) -> None:
    provider = _FakeProvider()
    service = StorageService(
        sqlite_session,
        settings=_settings(tmp_path),
        storage_provider=provider,
    )

    await service.put_bytes(object_key="runtime/course/demo.txt", content=b"old")
    await service.put_bytes(
        object_key="runtime/course/demo.txt",
        content=b"new",
        mime_type="text/plain",
        metadata={"updated": True},
    )
    await sqlite_session.commit()

    rows = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    assert len(rows) == 1
    assert rows[0].size_bytes == 3
    assert rows[0].content_hash == sha256(b"new").hexdigest()
    assert rows[0].metadata_ == {"updated": True}
