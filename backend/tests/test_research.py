from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Keep research HTTP contract tests on the middleware's isolated path."""

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


def test_list_research_funds(client: TestClient) -> None:
    response = client.get("/api/v1/research/funds?direction=AI%20安全")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert data[0]["evidence_sources"][0]["updated_at"]
    assert "CN2025XXXXXX" not in str(data)


def test_toggle_compare_and_read_compare_items(client: TestClient) -> None:
    payload = {"item_type": "fund", "item_id": "fund-edu-industry"}
    toggle_response = client.post("/api/v1/research/compare/toggle", json=payload)

    assert toggle_response.status_code == 200
    assert toggle_response.json()["compared"] is True

    compare_response = client.get("/api/v1/research/compare")
    assert compare_response.status_code == 200
    assert any(item["item_id"] == "fund-edu-industry" for item in compare_response.json())


def test_get_research_detail(client: TestClient) -> None:
    response = client.get("/api/v1/research/items/paper/paper-jailbreak-chain")

    assert response.status_code == 200
    data = response.json()
    assert data["item_type"] == "paper"
    assert data["item"]["doi_url"]
