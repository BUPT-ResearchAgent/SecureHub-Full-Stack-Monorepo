"""HTTP regression coverage for profile identity routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import profile
from app.db.seeds._constants import DEMO_USER_ID
from app.db.session import get_session
from app.deps import current_user_id


class _EmptyResult:
    def scalar_one_or_none(self) -> None:
        return None


class _EmptySession:
    async def execute(self, _statement: object) -> _EmptyResult:
        return _EmptyResult()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(profile.router, prefix="/api/v1")

    async def session_override():
        yield _EmptySession()

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[current_user_id] = lambda: DEMO_USER_ID
    return TestClient(app)


def test_profile_me_resolves_current_user_without_querying_with_literal_me() -> None:
    with _client() as client:
        response = client.get("/api/v1/profile/me")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "user_id": str(DEMO_USER_ID),
        "dimensions": {},
        "updated_at": None,
    }


def test_profile_dynamic_path_rejects_non_uuid_before_database_access() -> None:
    with _client() as client:
        response = client.get("/api/v1/profile/not-a-uuid")

    assert response.status_code == 422


def test_profile_dynamic_path_accepts_uuid() -> None:
    user_id = UUID("00000000-0000-0000-0000-000000000010")
    with _client() as client:
        response = client.get(f"/api/v1/profile/{user_id}")

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == str(user_id)
