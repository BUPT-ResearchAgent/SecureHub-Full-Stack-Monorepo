# Status: real

"""API smoke test：验证关键 endpoint 注册成功且 200 OK。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


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


def test_rag_search_returns_fixture():
    client = TestClient(app)
    response = client.post(
        "/api/v1/rag/search",
        json={"domain": "course_websec", "query": "SQL 注入", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert "hits" in body
    assert len(body["hits"]) >= 3
    assert body["fallback"] is True  # no DB in test


def test_courses_list():
    client = TestClient(app)
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    body = response.json()
    assert any(c["code"] == "WEB-SEC-101" for c in body)


def test_course_plan_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/v1/courses/course-websec/plan",
        json={"user_id": "demo", "selected_kp_ids": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert "path" in body
    assert body["status"] == "ok"


def test_profile_chat_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/v1/profile/chat",
        json={"user_id": "demo", "message": "我想从零学 Web 安全"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "persona" in body
    # fixture 默认会落 6+ dimensions
    assert isinstance(body["persona"].get("dimensions"), dict)
