"""HTTP contract tests for the durable Workflow Run control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import agent_control
from app.db.seeds._constants import DEMO_USER_ID
from app.main import app
from app.runtime.contracts import EventEnvelope, EventType
from app.schemas.agent_control import (
    WorkflowRunCancelResponse,
    WorkflowRunControlResponse,
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)


class RecordingWorkflowService:
    """Durable-service double; no Skill, queue, or in-memory executor."""

    def __init__(self) -> None:
        self.requests: list[tuple[WorkflowRunStartRequest, str | None, UUID | str | None]] = []
        self.replay_cursors: list[int] = []
        self.actions: list[tuple[str, UUID, UUID | str | None]] = []
        self._starts: dict[tuple[str, str | None], WorkflowRunStartResponse] = {}
        self._runs: dict[UUID, WorkflowRunResponse] = {}
        self._events: dict[UUID, list[EventEnvelope]] = {}

    async def start(
        self,
        request: WorkflowRunStartRequest,
        *,
        idempotency_key: str | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> WorkflowRunStartResponse:
        self.requests.append((request, idempotency_key, actor_user_id))
        key = (request.workflow, idempotency_key)
        if idempotency_key and key in self._starts:
            return self._starts[key]
        run_id = uuid4()
        start = WorkflowRunStartResponse(
            run_id=run_id,
            workflow=request.workflow,
            status="queued",
            events_url=f"/api/v1/workflow-runs/{run_id}/events",
            cancel_url=f"/api/v1/workflow-runs/{run_id}/cancel",
            mode=request.mode,
            requested_provider=request.provider,
            requested_model=request.model,
            provider=request.provider,
            model=request.model,
        )
        self._starts[key] = start
        self._runs[run_id] = WorkflowRunResponse(
            run_id=run_id,
            workflow=request.workflow,
            workflow_version="1",
            status="succeeded",
            mode=request.mode,
            requested_provider=request.provider,
            requested_model=request.model,
            provider=request.provider,
            model=request.model,
            created_at=datetime.now(timezone.utc),
            final_output={"output": {}},
        )
        self._events[run_id] = [
            EventEnvelope(
                workflow_run_id=run_id,
                sequence=1,
                event_type=EventType.PROGRESS,
                payload={"root_status": "queued", "status": "queued", "mode": request.mode},
            ),
            EventEnvelope(
                workflow_run_id=run_id,
                sequence=2,
                event_type=EventType.DONE,
                payload={"status": "succeeded", "final_output_ref": None},
            ),
        ]
        return start

    async def get(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunResponse:
        return self._runs[UUID(str(run_id))]

    async def replay(
        self,
        run_id: UUID | str,
        *,
        after_sequence: int = 0,
        until_sequence: int | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> list[EventEnvelope]:
        self.replay_cursors.append(after_sequence)
        return [
            event
            for event in self._events[UUID(str(run_id))]
            if event.sequence > after_sequence
            and (until_sequence is None or event.sequence <= until_sequence)
        ]

    async def cancel(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunCancelResponse:
        parsed = UUID(str(run_id))
        self.actions.append(("cancel", parsed, actor_user_id))
        return WorkflowRunCancelResponse(run_id=parsed, status="cancelling", cancel_requested=True)

    async def pause(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunControlResponse:
        return self._action("pause", run_id, actor_user_id)

    async def resume(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunControlResponse:
        return self._action("resume", run_id, actor_user_id)

    async def retry(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunControlResponse:
        return self._action("retry", run_id, actor_user_id)

    def _action(
        self, name: str, run_id: UUID | str, actor_user_id: UUID | str | None
    ) -> WorkflowRunControlResponse:
        parsed = UUID(str(run_id))
        self.actions.append((name, parsed, actor_user_id))
        return WorkflowRunControlResponse(run_id=parsed, status="queued", compatibility="compatible")


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> RecordingWorkflowService:
    fake = RecordingWorkflowService()
    monkeypatch.setattr(agent_control, "_service", lambda _request=None: fake)
    return fake


@pytest.fixture
def client() -> TestClient:
    # Lifespan is intentionally not entered: this suite exercises the HTTP
    # contract around the application service, not a Worker process.
    return TestClient(app)


def _start_fixture_run(client: TestClient, *, idempotency_key: str | None = None) -> dict[str, object]:
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    response = client.post(
        "/api/v1/workflow-runs",
        json={
            "workflow": "resource_generate_v1",
            "user_id": "00000000-0000-0000-0000-000000000999",
            "course_id": "5f63a7c3-1c76-513c-88a5-f335d6190816",
            "input": {"resource_type": "doc", "query": "SQL injection"},
            "mode": "fixture",
            "provider": "fixture",
            "stream": True,
        },
        headers=headers,
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_manifest_exposes_exactly_nine_agents_and_frozen_catalog() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/agents/manifest")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 9
    assert body["catalog_version"] == "production-catalog-v1"
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
    assert sum(len(agent["skills"]) for agent in body["agents"]) == 28
    assert all(agent["stable_id"] for agent in body["agents"])


def test_start_creates_one_owned_durable_root(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    started = _start_fixture_run(client, idempotency_key="same-root")

    assert started["mode"] == "fixture"
    assert started["provider"] == "fixture"
    assert started["events_url"] == f"/api/v1/workflow-runs/{started['run_id']}/events"
    request, key, actor = service.requests[-1]
    assert request.workflow == "resource_generate_v1"
    assert request.user_id == str(DEMO_USER_ID)
    assert actor == DEMO_USER_ID
    assert key == "same-root"


def test_idempotency_returns_the_same_root_without_a_second_execution(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    first = _start_fixture_run(client, idempotency_key="same-root")
    second = _start_fixture_run(client, idempotency_key="same-root")

    assert first["run_id"] == second["run_id"]
    assert len(service._runs) == 1
    assert len(service.requests) == 2


def test_sse_replay_honours_last_event_id_and_keeps_fixed_event_vocabulary(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    started = _start_fixture_run(client)
    run_id = str(started["run_id"])

    initial = client.get(f"/api/v1/workflow-runs/{run_id}/events")
    replay = client.get(
        f"/api/v1/workflow-runs/{run_id}/events",
        headers={"Last-Event-ID": "1"},
    )

    assert initial.status_code == replay.status_code == 200
    assert initial.headers["content-type"].startswith("text/event-stream")
    assert "id: 1" in initial.text and "event: progress" in initial.text
    assert "id: 2" in initial.text and "event: done" in initial.text
    assert "id: 1" not in replay.text and "id: 2" in replay.text
    assert "event: done" in replay.text
    assert service.replay_cursors[-1] == 1
    assert "event: fixture" not in initial.text


def test_cursor_validation_rejects_negative_and_conflicting_values(client: TestClient) -> None:
    negative = client.get(
        "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000001/events",
        headers={"Last-Event-ID": "-1"},
    )
    conflict = client.get(
        "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000001/events?after_sequence=1",
        headers={"Last-Event-ID": "2"},
    )

    assert negative.status_code == conflict.status_code == 422
    assert negative.json()["detail"]["code"] == "INVALID_EVENT_CURSOR"
    assert conflict.json()["detail"]["code"] == "INVALID_EVENT_CURSOR"


@pytest.mark.parametrize("action", ["cancel", "pause", "resume", "retry"])
def test_control_actions_forward_only_the_durable_root(
    client: TestClient, service: RecordingWorkflowService, action: str
) -> None:
    started = _start_fixture_run(client)
    run_id = str(started["run_id"])
    response = client.post(f"/api/v1/workflow-runs/{run_id}/{action}")

    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == run_id
    assert service.actions[-1] == (action, UUID(run_id), DEMO_USER_ID)


def test_real_mode_cannot_select_fixture_provider(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflow-runs",
        json={
            "workflow": "resource_generate_v1",
            "user_id": "00000000-0000-0000-0000-000000000999",
            "input": {"resource_type": "doc", "query": "SQL injection"},
            "mode": "real",
            "provider": "fixture",
        },
    )

    assert response.status_code == 422
