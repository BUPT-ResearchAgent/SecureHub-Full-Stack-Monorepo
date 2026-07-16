# Status: real

import asyncio
import base64
import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.provider_credential import ProviderCredential
from app.db.models.identity.provider_model_selection import ProviderModelSelection
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.models.security.account_security import AccountPasswordCompliance, PasswordPolicy
from app.db.session import get_session
from app.main import app


@pytest.fixture()
def credential_client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'credentials.sqlite'}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        PROVIDER_CREDENTIAL_MASTER_KEY=base64.urlsafe_b64encode(b"q" * 32).decode("ascii"),
        XFYUN_MODEL="spark-x",
    )

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[
                    User.__table__,
                    UserProfile.__table__,
                    UserCapability.__table__,
                    ProviderCredential.__table__,
                    ProviderModelSelection.__table__,
                    PasswordPolicy.__table__,
                    AccountPasswordCompliance.__table__,
                    GovernanceAuditEvent.__table__,
                ],
            )

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        asyncio.run(engine.dispose())


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecureHub@2026", "display_name": "Credential User"},
    )
    assert response.status_code == 201
    return str(response.json()["access_token"])


def test_provider_credential_endpoints_require_authenticated_user(credential_client: TestClient) -> None:
    response = credential_client.get("/api/v1/provider-credentials")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_provider_credential_api_masks_key_and_isolates_users(credential_client: TestClient) -> None:
    first_token = _token(credential_client, "credential-api-first@example.test")
    second_token = _token(credential_client, "credential-api-second@example.test")
    headers = {"Authorization": f"Bearer {first_token}"}
    key_one, key_two = uuid4().hex, uuid4().hex

    first = credential_client.post(
        "/api/v1/provider-credentials",
        headers=headers,
        json={"provider": "deepseek", "name": "main", "api_key": key_one, "activate": True},
    )
    assert first.status_code == 201
    first_payload = first.json()
    assert first_payload["fingerprint"].startswith("sha256:")
    assert key_one not in json.dumps(first_payload)
    assert "encrypted_key" not in first_payload

    second = credential_client.post(
        "/api/v1/provider-credentials",
        headers=headers,
        json={"provider": "deepseek", "name": "backup", "api_key": key_two, "activate": False},
    )
    assert second.status_code == 201
    activated = credential_client.post(
        f"/api/v1/provider-credentials/{second.json()['id']}/activate",
        headers=headers,
    )
    assert activated.status_code == 200

    first_list = credential_client.get("/api/v1/provider-credentials", headers=headers)
    assert first_list.status_code == 200
    assert len(first_list.json()["items"]) == 2
    assert [item["name"] for item in first_list.json()["items"] if item["is_active"]] == ["backup"]

    other_list = credential_client.get(
        "/api/v1/provider-credentials",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert other_list.status_code == 200
    other_payload = other_list.json()
    assert other_payload["items"] == []
    assert {source["provider"] for source in other_payload["sources"]} == {"deepseek", "xfyun"}
    assert other_payload["selection"] is not None


def test_provider_model_selection_is_server_owned_and_source_verification_is_safe(
    credential_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token(credential_client, "credential-source@example.test")
    headers = {"Authorization": f"Bearer {token}"}

    selected = credential_client.post(
        "/api/v1/provider-credentials/selection",
        headers=headers,
        json={"provider": "xfyun", "model": "spark-x"},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["provider"] == "xfyun"
    assert selected.json()["model"] == "spark-x"
    assert selected.json()["model_label"] == "Spark X2 Flash"

    unsupported = credential_client.post(
        "/api/v1/provider-credentials/selection",
        headers=headers,
        json={"provider": "xfyun", "model": "browser-supplied-model"},
    )
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["code"] == "MODEL_SOURCE_UNSUPPORTED"

    class _AvailableProvider:
        async def health_check(self):
            from app.llm.provider import HealthStatus

            return HealthStatus(
                provider="xfyun",
                model="spark-x",
                mode="real",
                live_enabled=True,
                status="available",
            )

    monkeypatch.setattr(
        "app.services.provider_credentials.get_llm_provider",
        lambda _provider, **_kwargs: _AvailableProvider(),
    )
    verified = credential_client.post(
        "/api/v1/provider-credentials/source-verification",
        headers=headers,
        json={"provider": "xfyun", "model": "spark-x"},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json() == {
        "provider": "xfyun",
        "model": "spark-x",
        "label": "讯飞星火",
        "model_label": "Spark X2 Flash",
        "status": "available",
    }
