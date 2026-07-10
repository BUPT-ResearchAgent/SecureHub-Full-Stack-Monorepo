# Status: partial-real

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app


USER_ID = "00000000-0000-0000-0000-000000000001"


def _start_fixture_run(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflow-runs",
        json={
            "workflow": "course_learning_minimal",
            "user_id": USER_ID,
            "course_id": "course-websec",
            "topic": "SQL 注入",
            "goal": "为初学者生成 SQL 注入学习路径和入门资源",
            "mode": "fixture",
            "provider": "fixture",
            "stream": True,
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def _wait_for_terminal(client: TestClient, run_id: str, timeout_seconds: float = 2.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/workflow-runs/{run_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in {"succeeded", "failed", "blocked", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError(f"workflow run {run_id} did not reach a terminal state")


def test_manifest_exposes_exactly_nine_fixed_agents():
    with TestClient(app) as client:
        response = client.get("/api/v1/agents/manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 9
    assert {agent["name"] for agent in body["agents"]} == {
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


def test_fixture_workflow_status_and_sse_trace_are_observable():
    with TestClient(app) as client:
        started = _start_fixture_run(client)
        run_id = str(started["run_id"])
        terminal = _wait_for_terminal(client, run_id)
        events = client.get(f"/api/v1/workflow-runs/{run_id}/events")

    assert started["mode"] == "fixture"
    assert started["provider"] == "fixture"
    assert terminal["status"] == "succeeded"
    assert terminal["child_run_count"] == 5
    assert len({item["agent_name"] for item in terminal["child_runs"]}) >= 4
    assert all(item["status"] == "succeeded" for item in terminal["child_runs"])
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: progress" in events.text
    assert "event: trace" in events.text
    assert "event: done" in events.text
    assert '"mode": "fixture"' in events.text
    assert '"provider": "fixture"' in events.text
    assert '"mode": "real"' not in events.text


def test_cancel_marks_active_fixture_run_cancelled(monkeypatch):
    from app.runtime.workflows import course_learning_minimal

    monkeypatch.setattr(course_learning_minimal, "FIXTURE_STEP_DELAY_SECONDS", 0.2)
    with TestClient(app) as client:
        started = _start_fixture_run(client)
        run_id = str(started["run_id"])
        cancelled = client.post(f"/api/v1/workflow-runs/{run_id}/cancel")
        terminal = _wait_for_terminal(client, run_id)
        events = client.get(f"/api/v1/workflow-runs/{run_id}/events")

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] in {"cancelling", "cancelled"}
    assert terminal["status"] == "cancelled"
    assert any(item["status"] in {"cancelled", "skipped"} for item in terminal["child_runs"])
    assert "event: done" in events.text
    assert '"status": "cancelled"' in events.text
    assert "event: token" not in events.text
    assert "event: artifact" not in events.text


def test_real_request_is_rejected_without_silent_fixture_fallback():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflow-runs",
            json={
                "workflow": "course_learning_minimal",
                "user_id": USER_ID,
                "course_id": "course-websec",
                "mode": "real",
                "provider": "deepseek",
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
