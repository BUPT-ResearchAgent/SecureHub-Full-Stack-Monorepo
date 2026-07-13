# Status: real

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.db.models.identity.user import User
from app.repositories.identity.provider_credentials import ProviderCredentialRepository
from app.runtime.persistence.run_store import RunStore
from app.runtime.workflow_definition import NodeDefinition, WorkflowDefinition
from app.runtime.workflow_registry import WorkflowRegistry
from app.schemas.agent_control import WorkflowRunStartRequest
from app.services.provider_credential_resolver import ProviderCredentialResolver
from app.services.provider_credentials import ProviderCredentialError, ProviderCredentialService
from app.services.workflow_application_service import WorkflowApplicationService


def _settings() -> Settings:
    return Settings(PROVIDER_CREDENTIAL_MASTER_KEY=base64.urlsafe_b64encode(b"p" * 32).decode("ascii"))


async def _user(session, suffix: str) -> User:
    row = User(
        id=uuid4(),
        email=f"credential-{suffix}@example.test",
        display_name=f"Credential {suffix}",
        hashed_password=None,
        is_active=True,
    )
    session.add(row)
    await session.commit()
    return row


@pytest.mark.anyio
async def test_credentials_are_user_scoped_encrypted_and_switch_active(sqlite_session) -> None:
    first_user = await _user(sqlite_session, "first")
    second_user = await _user(sqlite_session, "second")
    service = ProviderCredentialService(sqlite_session, _settings())
    first_key = uuid4().hex
    second_key = uuid4().hex
    other_key = uuid4().hex

    first = await service.create(
        user_id=first_user.id,
        provider="deepseek",
        name="main",
        api_key=first_key,
        activate=True,
    )
    second = await service.create(
        user_id=first_user.id,
        provider="deepseek",
        name="backup",
        api_key=second_key,
        activate=False,
    )
    other = await service.create(
        user_id=second_user.id,
        provider="deepseek",
        name="main",
        api_key=other_key,
        activate=True,
    )

    assert first.encrypted_key != first_key
    assert first_key not in first.encrypted_key
    assert first.key_fingerprint.startswith("sha256:")
    assert first.verification_status == "unverified"

    await service.activate(user_id=first_user.id, credential_id=second.id)
    first_rows = await service.list(first_user.id)
    assert {row.id for row in first_rows} == {first.id, second.id}
    assert [row.id for row in first_rows if row.is_active] == [second.id]
    assert (await service.list(second_user.id))[0].id == other.id

    with pytest.raises(ProviderCredentialError) as exc_info:
        await service.activate(user_id=second_user.id, credential_id=second.id)
    assert exc_info.value.code == "CREDENTIAL_NOT_FOUND"


@pytest.mark.anyio
async def test_resolver_uses_only_the_root_frozen_owned_credential(sqlite_session, monkeypatch) -> None:
    user = await _user(sqlite_session, "resolver")
    other = await _user(sqlite_session, "resolver-other")
    settings = _settings()
    service = ProviderCredentialService(sqlite_session, settings)
    key = uuid4().hex
    credential = await service.create(
        user_id=user.id,
        provider="deepseek",
        name="frozen",
        api_key=key,
        activate=True,
    )

    captured: dict[str, str] = {}

    def fake_provider(provider: str, *, api_key: str | None = None):
        captured["provider"] = provider
        captured["api_key"] = api_key or ""
        return object()

    monkeypatch.setattr("app.services.provider_credential_resolver.get_llm_provider", fake_provider)
    monkeypatch.setattr("app.services.provider_credential_resolver.get_settings", lambda: settings)
    resolver = ProviderCredentialResolver(lambda: _SessionContext(sqlite_session))
    # The resolver only relies on the async context-manager protocol, letting
    # this test share its isolated SQLite transaction without a global DB.
    result = await resolver.resolve(
        provider="deepseek",
        user_id=user.id,
        credential_id=credential.id,
    )
    assert result is not None
    assert captured == {"provider": "deepseek", "api_key": key}

    with pytest.raises(ProviderCredentialError):
        await resolver.resolve(
            provider="deepseek",
            user_id=other.id,
            credential_id=credential.id,
        )


class _SessionContext:
    """Tiny adapter to reuse the fixture's session in resolver unit coverage."""

    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class _RootInput(BaseModel):
    value: str


class _RootOutput(BaseModel):
    value: str


@pytest.mark.anyio
async def test_real_root_persists_the_active_credential_id(sqlite_session, monkeypatch) -> None:
    """A worker must receive the ID chosen at root creation, not look it up later."""
    user = await _user(sqlite_session, "root")
    settings = _settings().model_copy(update={"AGENT_RUN_REAL_ENABLED": True})
    credential = await ProviderCredentialService(sqlite_session, settings).create(
        user_id=user.id,
        provider="deepseek",
        name="selected",
        api_key=uuid4().hex,
        activate=True,
    )
    definition = WorkflowDefinition(
        name="credential_root_test_v1",
        version=1,
        input_model=_RootInput,
        output_model=_RootOutput,
        nodes=(NodeDefinition(node_id="noop", kind="action", action_name="Noop"),),
    )
    registry = WorkflowRegistry()
    registry.register(definition)
    monkeypatch.setattr("app.services.workflow_application_service.get_settings", lambda: settings)
    service = WorkflowApplicationService(
        lambda: _SessionContext(sqlite_session),
        workflow_registry=registry,
    )

    started = await service.start(
        WorkflowRunStartRequest(
            workflow=definition.name,
            user_id=str(user.id),
            input={"value": "persist credential"},
            mode="real",
            provider="deepseek",
            model="deepseek-chat",
        ),
        idempotency_key="credential-root",
        actor_user_id=user.id,
    )

    run = await RunStore(sqlite_session).get_run(started.run_id)
    assert run is not None
    assert run.credential_id == credential.id

    await ProviderCredentialService(sqlite_session, settings).delete(
        user_id=user.id,
        credential_id=credential.id,
    )
    await sqlite_session.refresh(run)
    # Deletion must not change the root into an environment-key fallback.
    assert run.credential_id == credential.id
