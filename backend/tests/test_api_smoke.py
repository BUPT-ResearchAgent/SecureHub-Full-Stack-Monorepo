# Status: real

"""API smoke tests for critical endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

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


def test_rag_search_returns_fixture():
    client = TestClient(app)
    response = client.post(
        "/api/v1/rag/search",
        json={"domain": "course_websec", "query": "SQL injection", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert "hits" in body
    assert len(body["hits"]) >= 3
    assert body["fallback"] is True


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
        json={"user_id": USER_ID, "target_node_id": KP_ID, "options": {"depth": 3}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["course_id"] == COURSE_ID
    assert "path" in body


def test_profile_chat_endpoint_sse():
    client = TestClient(app)
    response = client.post(
        "/api/v1/profile/chat",
        json={"user_id": "demo", "message": "I want to learn web security."},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: " in response.text


def test_tutor_ask_endpoint_sse():
    client = TestClient(app)
    response = client.post(
        "/api/v1/tutor/ask",
        json={"user_id": USER_ID, "course_id": COURSE_ID, "question": "Why use parameterized queries?"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: " in response.text


def test_resource_generate_endpoint_sse():
    client = TestClient(app)
    response = client.post(
        "/api/v1/courses/course-websec/resources/generate?type=readings",
        json={"type": "readings", "user_id": USER_ID, "kp_id": KP_ID},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: " in response.text


def test_assessment_run_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/v1/assessment/run",
        json={"user_id": USER_ID, "course_id": COURSE_ID, "answers": [{"quiz_item_id": "q1", "answer": "A"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert "feedback" in body
    assert "updated_capabilities" in body
