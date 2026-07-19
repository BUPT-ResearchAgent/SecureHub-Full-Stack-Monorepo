# Status: real

from collections.abc import AsyncIterator, Iterator
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.services.storage.upload_gate import UploadGateService


def _settings(*, secret: str = "correct-test-key", max_bytes: int = 1024) -> Settings:
    return Settings(
        _env_file=None,
        STORAGE_PROVIDER="cos",
        STORAGE_LOCAL_ROOT="./data/storage",
        COS_SECRET_ID="unit-test-id",
        COS_SECRET_KEY="unit-test-key",
        COS_REGION="ap-beijing",
        COS_BUCKET="unit-test-bucket",
        UPLOAD_GATE_ENABLED=True,
        UPLOAD_GATE_SECRET_HASH=sha256(secret.encode("utf-8")).hexdigest(),
        UPLOAD_GATE_MAX_BYTES=max_bytes,
        UPLOAD_GATE_ALLOWED_MIME_PREFIXES=["image/", "application/pdf", "text/markdown"],
        UPLOAD_GATE_ALLOWED_PREFIXES=["uploads/", "tmp/uploads/"],
        UPLOAD_GATE_PRESIGNED_EXPIRES_SECONDS=600,
    )


@pytest.fixture()
def upload_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    async def fake_signed_url(self: UploadGateService, object_key: str) -> str:
        return f"https://upload.example.invalid/{object_key}"

    async def isolated_get_session() -> AsyncIterator[None]:
        yield None

    monkeypatch.setattr(UploadGateService, "_create_presigned_put_url", fake_signed_url)
    had_previous_session_override = get_session in app.dependency_overrides
    previous_session_override = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = isolated_get_session
    app.dependency_overrides[get_settings] = lambda: _settings()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        if had_previous_session_override:
            app.dependency_overrides[get_session] = previous_session_override
        else:
            app.dependency_overrides.pop(get_session, None)


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "filename": "demo.png",
        "mime_type": "image/png",
        "size_bytes": 123,
        "target_prefix": "uploads/demo",
    }
    payload.update(overrides)
    return payload


def test_upload_init_missing_key_returns_401(upload_client: TestClient) -> None:
    response = upload_client.post("/api/v1/uploads/init", json=_payload())

    assert response.status_code == 401


def test_upload_init_wrong_key_returns_401(upload_client: TestClient) -> None:
    response = upload_client.post(
        "/api/v1/uploads/init",
        json=_payload(),
        headers={"X-SecureHub-Upload-Key": "wrong"},
    )

    assert response.status_code == 401


def test_upload_init_correct_key_returns_presigned_put(upload_client: TestClient) -> None:
    response = upload_client.post(
        "/api/v1/uploads/init",
        json=_payload(filename="../demo.png"),
        headers={"X-SecureHub-Upload-Key": "correct-test-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "PUT"
    assert body["object_key"].startswith("tmp/uploads/")
    assert body["object_key"].endswith("/demo.png")
    assert body["presigned_url"].startswith("https://upload.example.invalid/")
    assert body["expires_in"] == 600
    assert body["max_bytes"] == 1024


def test_upload_init_oversize_returns_413(upload_client: TestClient) -> None:
    response = upload_client.post(
        "/api/v1/uploads/init",
        json=_payload(size_bytes=2048),
        headers={"X-SecureHub-Upload-Key": "correct-test-key"},
    )

    assert response.status_code == 413


def test_upload_init_forbidden_mime_returns_400(upload_client: TestClient) -> None:
    response = upload_client.post(
        "/api/v1/uploads/init",
        json=_payload(mime_type="application/x-msdownload"),
        headers={"X-SecureHub-Upload-Key": "correct-test-key"},
    )

    assert response.status_code == 400


def test_upload_init_forbidden_prefix_returns_400(upload_client: TestClient) -> None:
    response = upload_client.post(
        "/api/v1/uploads/init",
        json=_payload(target_prefix="private/team-sync/data"),
        headers={"X-SecureHub-Upload-Key": "correct-test-key"},
    )

    assert response.status_code == 400
