# Status: partial-real

from __future__ import annotations

import time
import re
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


USER_ID = "00000000-0000-0000-0000-000000000001"


def _event_ids(sse_text: str) -> list[int]:
    return [int(value) for value in re.findall(r"^id: (\d+)$", sse_text, re.MULTILINE)]


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


def test_completed_sse_history_replays_after_last_event_id():
    with TestClient(app) as client:
        started = _start_fixture_run(client)
        run_id = str(started["run_id"])
        _wait_for_terminal(client, run_id)
        initial = client.get(f"/api/v1/workflow-runs/{run_id}/events")
        initial_ids = _event_ids(initial.text)
        replay = client.get(
            f"/api/v1/workflow-runs/{run_id}/events",
            headers={"Last-Event-ID": str(initial_ids[0])},
        )

    replay_ids = _event_ids(replay.text)
    assert initial.status_code == 200
    assert initial_ids
    assert replay.status_code == 200
    assert replay_ids
    assert all(event_id > initial_ids[0] for event_id in replay_ids)
    assert "event: trace" in replay.text


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


def test_real_request_is_rejected_when_server_side_gate_is_disabled():
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
    assert response.json()["detail"]["code"] == "REAL_MODE_DISABLED"


def test_real_request_rejects_any_provider_except_deepseek():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflow-runs",
            json={
                "workflow": "course_learning_minimal",
                "user_id": USER_ID,
                "course_id": "course-websec",
                "mode": "real",
                "provider": "xfyun",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_PROVIDER"


def test_real_request_rejects_invalid_user_id_before_real_gate():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflow-runs",
            json={
                "workflow": "course_learning_minimal",
                "user_id": "not-a-uuid",
                "course_id": "course-websec",
                "mode": "real",
                "provider": "deepseek",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_USER_ID"


def test_real_endpoint_returns_202_with_enabled_gate_and_fake_provider(monkeypatch):
    from app.api.v1.endpoints import agent_control
    from app.runtime.run_registry import RunRegistry
    from app.services import agent_control_service
    from app.services.agent_control_service import AgentControlService

    fake_provider = SimpleNamespace(provider_name="deepseek", model_name="fake-deepseek-v4")

    async def fake_workflow(run_id, registry):
        record = await registry.get(run_id)
        if not await registry.mark_running(run_id):
            return
        await registry.mark_succeeded(run_id, {})
        await registry.publish(
            run_id,
            {
                "event": "done",
                "workflow_run_id": str(run_id),
                "status": "succeeded",
                "final_output_ref": None,
                "child_run_count": len(record.nodes),
                "quality_score": None,
                "mode": record.mode,
                "provider": record.provider,
                "model": record.model,
            },
        )

    async def fake_preflight(_user_id):
        return None

    monkeypatch.setattr(
        agent_control_service,
        "get_settings",
        lambda: SimpleNamespace(
            AGENT_RUN_REAL_ENABLED=True,
            AGENT_RUN_REAL_MAX_CONCURRENCY=1,
        ),
    )
    monkeypatch.setattr(
        agent_control_service,
        "get_strict_deepseek_provider",
        lambda: fake_provider,
    )
    monkeypatch.setattr(agent_control_service, "run_course_learning_minimal", fake_workflow)
    service = AgentControlService(RunRegistry())
    monkeypatch.setattr(service, "_validate_real_prerequisites", fake_preflight)
    monkeypatch.setattr(agent_control, "_service", service)

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

    assert response.status_code == 202
    assert response.json()["mode"] == "real"
    assert response.json()["provider"] == "deepseek"
    assert response.json()["model"] == "fake-deepseek-v4"
