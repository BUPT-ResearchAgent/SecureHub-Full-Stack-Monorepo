# Status: real

"""API smoke tests for critical endpoints."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.llm.provider import HealthStatus
from app.main import app

USER_ID = "00000000-0000-0000-0000-000000000001"
COURSE_ID = "00000000-0000-0000-0000-000000000101"
KP_ID = "00000000-0000-0000-0000-000000000201"


def test_health():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_agents_manifest():
    client = TestClient(app)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 9
    names = {a["name"] for a in body}
    assert names == {
        "policy_interpreter",
        "hot_analyst",
        "job_analyst",
        "competition_advisor",
        "career_planner",
        "topic_explorer",
        "doc_archivist",
        "task_orchestrator",
        "outcome_evaluator",
    }


def test_rag_search_returns_explicit_fixture_mode():
    client = TestClient(app)
    payload = {"domain": "course_websec", "query": "SQL injection", "top_k": 3, "mode": "fixture"}
    response = client.post(
        "/api/v1/rag/search",
        json=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert "hits" in body
    assert len(body["hits"]) >= 3
    assert body["mode"] == "fixture"

    repeated = client.post("/api/v1/rag/search", json=payload)
    assert repeated.status_code == 200
    assert repeated.json() == body


def test_real_rag_search_fails_closed_without_evidence(monkeypatch):
    import importlib

    rag_service = importlib.import_module("app.rag.search")

    async def empty_retrieve(*_args, **_kwargs):
        return []

    monkeypatch.setattr(rag_service, "retrieve", empty_retrieve)
    response = TestClient(app).post(
        "/api/v1/rag/search",
        json={"domain": "course_websec", "query": "SQL injection", "top_k": 3, "mode": "real"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RAG_UNAVAILABLE"


def test_real_rag_search_sanitises_embedding_dependency_failure(monkeypatch):
    import importlib

    from app.llm.embeddings.errors import EmbeddingConfigurationError

    rag_service = importlib.import_module("app.rag.search")

    async def unavailable_retrieve(*_args, **_kwargs):
        raise EmbeddingConfigurationError("DASHSCOPE_API_KEY is not set")

    monkeypatch.setattr(rag_service, "retrieve", unavailable_retrieve)
    response = TestClient(app).post(
        "/api/v1/rag/search",
        json={"domain": "course_websec", "query": "SQL injection", "top_k": 3, "mode": "real"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "RAG_UNAVAILABLE",
        "message": "real RAG embedding dependency is unavailable",
    }


def test_courses_list():
    client = TestClient(app)
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    body = response.json()
    assert any(c["code"] == "WEB-SEC-101" for c in body)


def test_llm_health_endpoint_uses_health_service(monkeypatch):
    from app.api.v1.endpoints import llm as llm_endpoint

    async def available_health() -> HealthStatus:
        return HealthStatus(
            provider="deepseek",
            model="deepseek-v4-pro",
            mode="real",
            live_enabled=True,
            status="available",
            rate_limit_state={"used": 2, "limit": 10},
        )

    monkeypatch.setattr(llm_endpoint, "get_llm_health", available_health)
    monkeypatch.setattr(
        llm_endpoint,
        "get_settings",
        lambda: SimpleNamespace(
            AGENT_RUN_REAL_ENABLED=True,
            LLM_PROVIDER="deepseek",
            DEEPSEEK_MODEL="deepseek-v4-pro",
            XFYUN_MODEL="spark-v4",
        ),
    )

    client = TestClient(app)
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    assert response.json() == {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "mode": "real",
        "live_enabled": True,
        "status": "available",
        "last_error": None,
        "rate_limit_state": {"used": 2, "limit": 10},
    }


def test_llm_health_endpoint_does_not_probe_when_real_execution_is_disabled(monkeypatch):
    from app.api.v1.endpoints import llm as llm_endpoint

    async def unexpected_probe() -> HealthStatus:
        raise AssertionError("disabled health endpoint must not probe a provider")

    monkeypatch.setattr(llm_endpoint, "get_llm_health", unexpected_probe)
    monkeypatch.setattr(
        llm_endpoint,
        "get_settings",
        lambda: SimpleNamespace(
            AGENT_RUN_REAL_ENABLED=False,
            LLM_PROVIDER="xfyun",
            DEEPSEEK_MODEL="deepseek-v4-pro",
            XFYUN_MODEL="spark-v4",
        ),
    )

    response = TestClient(app).get("/api/v1/llm/health")
    assert response.status_code == 200
    assert response.json() == {
        "provider": "xfyun",
        "model": "spark-v4",
        "mode": "real",
        "live_enabled": False,
        "status": "unknown",
        "last_error": "real execution is disabled",
        "rate_limit_state": {"used": 0, "limit": 0},
    }


def test_llm_health_endpoint_sanitizes_provider_error(monkeypatch):
    from app.api.v1.endpoints import llm as llm_endpoint

    async def unavailable_health() -> HealthStatus:
        return HealthStatus(
            provider="deepseek",
            model="deepseek-v4-pro",
            mode="real",
            live_enabled=True,
            status="error",
            last_error="upstream error with implementation details",
        )

    monkeypatch.setattr(llm_endpoint, "get_llm_health", unavailable_health)
    monkeypatch.setattr(
        llm_endpoint,
        "get_settings",
        lambda: SimpleNamespace(
            AGENT_RUN_REAL_ENABLED=True,
            LLM_PROVIDER="deepseek",
            DEEPSEEK_MODEL="deepseek-v4-pro",
            XFYUN_MODEL="spark-v4",
        ),
    )

    response = TestClient(app).get("/api/v1/llm/health")
    assert response.status_code == 200
    assert response.json()["last_error"] == "provider health check failed"
