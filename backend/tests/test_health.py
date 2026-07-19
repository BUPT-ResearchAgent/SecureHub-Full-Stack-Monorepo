from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Avoid the unrelated production audit session in a health contract test."""

    async def isolated_get_session() -> AsyncIterator[None]:
        yield None

    had_previous_override = get_session in app.dependency_overrides
    previous_override = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = isolated_get_session
    test_client: TestClient | None = None
    try:
        test_client = TestClient(app)
        yield test_client
    finally:
        if test_client is not None:
            test_client.close()
        if had_previous_override:
            app.dependency_overrides[get_session] = previous_override
        else:
            app.dependency_overrides.pop(get_session, None)


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "securehub-backend"
