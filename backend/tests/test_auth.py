# Status: real

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.db.base import Base
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.seeds._constants import DEMO_USER_EMAIL, DEMO_USER_PASSWORD
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.session import get_session
from app.main import app


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(_element, _compiler, **_kw):  # type: ignore[no-redef]
    return "BLOB"


@pytest.fixture()
def auth_client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "auth-test.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[User.__table__, UserProfile.__table__, UserCapability.__table__],
            )
        async with sessionmaker() as session:
            await seed_demo_user(session)
            await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        asyncio.run(engine.dispose())


def _register_payload(email: str = "new-user@example.com") -> dict[str, str]:
    return {
        "email": email,
        "password": "SecureHub@2026",
        "display_name": "新同学",
    }


def test_register_success(auth_client: TestClient) -> None:
    response = auth_client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "new-user@example.com"
    assert body["user"]["display_name"] == "新同学"


def test_register_duplicate_email_returns_409(auth_client: TestClient) -> None:
    payload = _register_payload("duplicate@example.com")
    assert auth_client.post("/api/v1/auth/register", json=payload).status_code == 201

    response = auth_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


def test_login_success_returns_token(auth_client: TestClient) -> None:
    payload = _register_payload("login-user@example.com")
    auth_client.post("/api/v1/auth/register", json=payload)

    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password_returns_401(auth_client: TestClient) -> None:
    payload = _register_payload("wrong-password@example.com")
    auth_client.post("/api/v1/auth/register", json=payload)

    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword@2026"},
    )

    assert response.status_code == 401


def test_auth_me_with_token_success(auth_client: TestClient) -> None:
    payload = _register_payload("me-user@example.com")
    token = auth_client.post("/api/v1/auth/register", json=payload).json()["access_token"]

    response = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == payload["email"]


def test_auth_me_without_token_returns_401(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_demo_account_can_login(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == DEMO_USER_EMAIL
    assert body["user"]["display_name"] == "陈同学"
    assert body["access_token"]
