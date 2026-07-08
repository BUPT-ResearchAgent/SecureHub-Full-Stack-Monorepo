# Status: real

"""API smoke tests for critical endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.agent import AgentTraceDTO
from app.schemas.assessment import AssessmentRunResponse
from app.schemas.course import CoursePlanResponse
from app.schemas.evidence import EvidenceChunkDTO
from app.services.agent import (
    build_learning_persona,
    generate_learning_path,
    generate_resource,
    run_assessment,
)

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


def test_rag_search_returns_fixture(monkeypatch):
    from app.core.config import get_settings
    from app.llm.embedding import reset_embedding_service

    monkeypatch.setenv("EMBEDDING_PROVIDER", "fixture")
    get_settings.cache_clear()
    reset_embedding_service()
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


def test_llm_health_endpoint_fixture_mode():
    client = TestClient(app)
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    assert response.json() == {
        "provider": "fixture",
        "model": "fixture-canned",
        "mode": "fixture",
        "live_enabled": False,
        "status": "available",
        "last_error": None,
        "rate_limit_state": {"used": 0, "limit": 0},
    }


def test_agent_fixture_services_match_frozen_dtos():
    async def collect() -> tuple[dict, dict, list[dict], list[dict]]:
        plan = await generate_learning_path(
            user_id=USER_ID,
            course_id=COURSE_ID,
            target_node_id=KP_ID,
        )
        assessment = await run_assessment(
            user_id=USER_ID,
            course_id=COURSE_ID,
            answers=[],
        )
        persona_events = [
            event
            async for event in build_learning_persona(
                user_id=USER_ID,
                message="I want to learn SQL injection.",
                dialogue_turns=[],
            )
        ]
        resource_events = [
            event
            async for event in generate_resource(
                user_id=USER_ID,
                course_id=COURSE_ID,
                kp_id=KP_ID,
                type="doc",
            )
        ]
        return plan, assessment, persona_events, resource_events

    plan, assessment, persona_events, resource_events = asyncio.run(collect())

    CoursePlanResponse(**plan)
    AssessmentRunResponse(**assessment)

    evidence = next(event for event in resource_events if event["event"] == "evidence")
    EvidenceChunkDTO(**{key: value for key, value in evidence.items() if key != "event"})

    trace = next(event for event in persona_events if event["event"] == "trace")
    AgentTraceDTO(**{key: value for key, value in trace.items() if key != "event"})
    assert trace["provider"] == "fixture"
    assert trace["model"] == "fixture-canned"

    assert {event["event"] for event in resource_events} >= {
        "progress",
        "evidence",
        "token",
        "artifact",
        "trace",
        "done",
    }


def test_resource_generate_sse_contains_contract_payloads():
    client = TestClient(app)
    response = client.post(
        "/api/v1/courses/course-websec/resources/generate?type=doc",
        json={"type": "doc", "user_id": USER_ID, "kp_id": KP_ID},
    )
    assert response.status_code == 200
    assert "event: evidence" in response.text
    assert "event: artifact" in response.text
    assert "event: trace" in response.text

    payloads = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert any(payload.get("platform") == "owasp" for payload in payloads)
    assert any(payload.get("provider") == "fixture" for payload in payloads)
