# Status: [planned]

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_xfyun() -> None:
    return None


@pytest.fixture
def seeded_kg() -> None:
    return None
