"""Contract tests for the five product-to-durable-workflow adapters."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import assessment, courses, profile, tutor
from app.db.seeds._constants import COURSE_CRYPTO_ID, COURSE_WEBSEC_ID, DEMO_USER_ID, node_id
from app.main import app
from app.runtime.contracts import EventEnvelope, EventType
from app.schemas.agent_control import (
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)


COURSE_ID = str(COURSE_WEBSEC_ID)
KP_ID = str(node_id("sql-injection"))
UNTRUSTED_USER_ID = "00000000-0000-0000-0000-000000000999"


class RecordingWorkflowService:
    """Minimal durable-service double with no Skill or queue implementation."""

    def __init__(self) -> None:
        self.requests: list[tuple[WorkflowRunStartRequest, str | None, UUID | str | None]] = []
        self._starts_by_key: dict[tuple[str, str | None], WorkflowRunStartResponse] = {}
        self._status_by_run: dict[UUID, WorkflowRunResponse] = {}
        self._events_by_run: dict[UUID, list[EventEnvelope]] = {}

    async def start(
        self,
        request: WorkflowRunStartRequest,
        *,
        idempotency_key: str | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> WorkflowRunStartResponse:
        self.requests.append((request, idempotency_key, actor_user_id))
        key = (request.workflow, idempotency_key)
        existing = self._starts_by_key.get(key) if idempotency_key else None
        if existing is not None:
            return existing
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
        self._starts_by_key[key] = start
        self._status_by_run[run_id] = self._run_status(start)
        self._events_by_run[run_id] = [
            EventEnvelope(
                workflow_run_id=run_id,
                sequence=1,
                event_type=EventType.PROGRESS,
                payload={"root_status": "queued", "status": "queued"},
            ),
            EventEnvelope(
                workflow_run_id=run_id,
                sequence=2,
                event_type=EventType.DONE,
                payload={"status": "succeeded", "final_output_ref": None},
            ),
        ]
        return start

    async def get(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> WorkflowRunResponse:
        return self._status_by_run[UUID(str(run_id))]

    async def replay(
        self,
        run_id: UUID | str,
        *,
        after_sequence: int = 0,
        until_sequence: int | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> list[EventEnvelope]:
        return [
            event
            for event in self._events_by_run[UUID(str(run_id))]
            if event.sequence > after_sequence and (until_sequence is None or event.sequence <= until_sequence)
        ]

    def mark_succeeded(self, run_id: UUID, output: dict[str, object]) -> None:
        current = self._status_by_run[run_id]
        self._status_by_run[run_id] = current.model_copy(
            update={"status": "succeeded", "final_output": {"output": output}}
        )

    @staticmethod
    def _run_status(start: WorkflowRunStartResponse) -> WorkflowRunResponse:
        return WorkflowRunResponse(
            run_id=start.run_id,
            workflow=start.workflow,
            workflow_version="1",
            status="queued",
            mode=start.mode,
            requested_provider=start.requested_provider,
            requested_model=start.requested_model,
            provider=start.provider,
            model=start.model,
            created_at=datetime.now(timezone.utc),
        )


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> RecordingWorkflowService:
    fake = RecordingWorkflowService()
    monkeypatch.setattr(profile, "_service", lambda _request: fake)
    monkeypatch.setattr(courses, "_service", lambda _request: fake)
    monkeypatch.setattr(tutor, "_service", lambda _request: fake)
    monkeypatch.setattr(assessment, "_service", lambda _request: fake)
    return fake


@pytest.fixture
def client() -> TestClient:
    # Avoid lifespan startup: this suite exercises HTTP adapters, not Worker
    # execution. The service double is the only product-path collaborator.
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "body", "expected_workflow"),
    [
        (
            "/api/v1/profile/chat",
            {"user_id": "demo", "message": "I want to learn SQL injection."},
            "profile_build_v1",
        ),
        (
            "/api/v1/tutor/ask",
            {
                "user_id": UNTRUSTED_USER_ID,
                "course_id": COURSE_ID,
                "question": "Why use parameterized queries?",
            },
                "tutor_routing_v3",
        ),
        (
            "/api/v1/courses/course-websec/resources/generate?type=doc",
            {"user_id": UNTRUSTED_USER_ID, "kp_id": KP_ID, "type": "doc"},
            "resource_generate_v1",
        ),
        (
            "/api/v1/courses/course-websec/resources/generate-bundle",
            {"kp_id": KP_ID},
            "course_learning_full_v2",
        ),
    ],
)
def test_streaming_product_paths_create_one_durable_root(
    client: TestClient,
    service: RecordingWorkflowService,
    path: str,
    body: dict[str, object],
    expected_workflow: str,
) -> None:
    response = client.post(path, json=body, headers={"Idempotency-Key": "stream-root"})

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["X-Workflow-Run-ID"]
    assert response.headers["Location"] == f"/api/v1/workflow-runs/{response.headers['X-Workflow-Run-ID']}"
    assert f'"workflow_run_id": "{response.headers["X-Workflow-Run-ID"]}"' in response.text
    assert "event: progress" in response.text
    assert "event: done" in response.text

    started, key, actor = service.requests[-1]
    assert started.workflow == expected_workflow
    assert started.user_id == str(DEMO_USER_ID)
    assert actor == DEMO_USER_ID
    assert key == "stream-root"
    assert started.mode == "real"


def test_profile_idempotency_reuses_the_same_durable_root(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    body = {"user_id": "someone-else", "message": "Build my profile."}
    first = client.post("/api/v1/profile/chat", json=body, headers={"Idempotency-Key": "same-root"})
    second = client.post("/api/v1/profile/chat", json=body, headers={"Idempotency-Key": "same-root"})

    assert first.status_code == second.status_code == 200
    assert first.headers["X-Workflow-Run-ID"] == second.headers["X-Workflow-Run-ID"]
    assert len(service._starts_by_key) == 1
    assert len(service.requests) == 2


def test_product_adapter_does_not_fallback_when_root_persistence_is_unavailable(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    async def unavailable_start(*_args: object, **_kwargs: object) -> WorkflowRunStartResponse:
        raise ConnectionError("database host is unavailable")

    service.start = unavailable_start  # type: ignore[method-assign]
    response = client.post(
        "/api/v1/profile/chat",
        json={"user_id": "demo", "message": "Build my profile."},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "INTERNAL",
        "message": "workflow runtime is temporarily unavailable",
    }


def test_preview_course_adapters_refuse_before_creating_a_root(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    preview_id = str(COURSE_CRYPTO_ID)
    requests_before = len(service.requests)
    plan = client.post(
        "/api/v1/courses/crypto-foundation/plan",
        json={"user_id": UNTRUSTED_USER_ID, "target_node_id": KP_ID, "options": {"depth": 3}},
    )
    tutor_response = client.post(
        "/api/v1/tutor/ask",
        json={"user_id": UNTRUSTED_USER_ID, "course_id": preview_id, "question": "为什么不能生成？"},
        headers={"Idempotency-Key": "preview-tutor"},
    )
    assessment_response = client.post(
        "/api/v1/assessment/run",
        json={"user_id": UNTRUSTED_USER_ID, "course_id": preview_id, "answers": []},
        headers={"Idempotency-Key": "preview-assessment"},
    )

    for response in (plan, tutor_response, assessment_response):
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "COURSE_CONTENT_NOT_READY"
    assert len(service.requests) == requests_before


def test_course_plan_returns_accepted_root_when_not_terminal(
    client: TestClient,
    service: RecordingWorkflowService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_terminal(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(courses, "wait_for_terminal", no_terminal)
    response = client.post(
        "/api/v1/courses/course-websec/plan",
        json={"user_id": UNTRUSTED_USER_ID, "target_node_id": KP_ID, "options": {"depth": 3}},
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["workflow"] == "course_plan_v1"
    assert body["run_id"] == response.headers["X-Workflow-Run-ID"]
    assert response.headers["Location"] == f"/api/v1/workflow-runs/{body['run_id']}"
    assert service.requests[-1][0].user_id == str(DEMO_USER_ID)
    assert service.requests[-1][0].course_id == COURSE_ID


def test_course_plan_completed_response_retains_durable_root(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    original_start = service.start

    async def completed_start(*args: object, **kwargs: object) -> WorkflowRunStartResponse:
        start = await original_start(*args, **kwargs)
        service.mark_succeeded(
            start.run_id,
            {
                "path": [
                    {
                        "node_id": KP_ID,
                        "title": "SQL injection fundamentals",
                        "status": "ready",
                        "prerequisites": [],
                    }
                ]
            },
        )
        return start

    service.start = completed_start  # type: ignore[method-assign]
    response = client.post(
        "/api/v1/courses/course-websec/plan",
        json={"user_id": UNTRUSTED_USER_ID, "target_node_id": KP_ID},
    )

    assert response.status_code == 200, response.text
    run_id = response.headers["X-Workflow-Run-ID"]
    assert response.headers["Location"] == f"/api/v1/workflow-runs/{run_id}"
    assert response.headers["X-Workflow-Events-URL"] == f"/api/v1/workflow-runs/{run_id}/events"
    assert response.json()["path"][0]["node_id"] == KP_ID


def test_assessment_maps_a_completed_durable_output_without_executing_a_skill(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    original_start = service.start

    async def completed_start(*args: object, **kwargs: object) -> WorkflowRunStartResponse:
        start = await original_start(*args, **kwargs)
        service.mark_succeeded(
            start.run_id,
            {
                "score": 0.86,
                "feedback": "Focus next on parameterized queries.",
                "updated_capabilities": [
                    {"dimension": "web_security", "score": 0.58, "confidence": 0.8, "evidence_count": 2}
                ],
            },
        )
        return start

    service.start = completed_start  # type: ignore[method-assign]
    response = client.post(
        "/api/v1/assessment/run",
        json={"user_id": UNTRUSTED_USER_ID, "course_id": COURSE_ID, "answers": []},
    )

    assert response.status_code == 200, response.text
    run_id = response.headers["X-Workflow-Run-ID"]
    assert response.headers["Location"] == f"/api/v1/workflow-runs/{run_id}"
    assert response.headers["X-Workflow-Events-URL"] == f"/api/v1/workflow-runs/{run_id}/events"
    assert response.json()["score"] == 0.86
    assert response.json()["updated_capabilities"][0]["dimension"] == "web_security"
    assert service.requests[-1][0].workflow == "assessment_update_v2"
    assert service.requests[-1][0].user_id == str(DEMO_USER_ID)


def test_assessment_maps_the_nested_terminal_payload_written_by_profile_persistence(
    client: TestClient, service: RecordingWorkflowService
) -> None:
    original_start = service.start

    async def completed_start(*args: object, **kwargs: object) -> WorkflowRunStartResponse:
        start = await original_start(*args, **kwargs)
        service.mark_succeeded(
            start.run_id,
            {
                "assessment": {
                    "score": 0.73,
                    "feedback": "复习参数化查询后再完成下一次测验。",
                },
                "updated_capabilities": [
                    {"dimension": "web_security", "score": 0.61, "confidence": 0.7, "evidence_count": 1}
                ],
            },
        )
        return start

    service.start = completed_start  # type: ignore[method-assign]
    response = client.post(
        "/api/v1/assessment/run",
        json={"user_id": UNTRUSTED_USER_ID, "course_id": COURSE_ID, "answers": []},
    )

    assert response.status_code == 200, response.text
    assert response.json()["score"] == 0.73
    assert response.json()["feedback"] == "复习参数化查询后再完成下一次测验。"


def test_product_routes_do_not_retain_direct_skill_or_fixture_execution() -> None:
    root = Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "endpoints"
    forbidden = ("skill.run", "HarnessContext", "asyncio.Queue", "services.agent", "make_event_source_response")
    for name in ("profile.py", "courses.py", "tutor.py", "assessment.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), name
