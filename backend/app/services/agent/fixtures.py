# Status: mock

"""Fixture service functions for the student-side real-first API adapters.

These functions intentionally do not call LLM providers, skills, databases, or
the Harness. They keep the public service signatures stable so frontend and API
integration can validate DTO and SSE wire contracts before Wave 2 real skill
integration replaces the internals.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

FIXTURE_PROVIDER = "fixture"
FIXTURE_MODEL = "fixture-canned"


def _evidence_chunk() -> dict[str, Any]:
    return {
        "chunk_id": "00000000-0000-0000-0000-000000000501",
        "document_id": "00000000-0000-0000-0000-000000000601",
        "chunk_text": (
            "SQL injection occurs when untrusted input is concatenated into a "
            "database query instead of being bound as a parameter."
        ),
        "excerpt": (
            "SQL injection occurs when untrusted input is concatenated into a "
            "database query."
        ),
        "score": 0.91,
        "platform": "owasp",
        "rights_note": "CC BY-SA 4.0",
        "source_url": "https://owasp.org/www-community/attacks/SQL_Injection",
        "title": "OWASP SQL Injection",
        "author": "OWASP",
        "collection_mode": "scrapling",
        "asset_type": "web_article",
        "license": "CC BY-SA 4.0",
        "reliability": 0.92,
    }


def _trace_event(
    *,
    run_id: str,
    workflow_name: str,
    agent_name: str,
    skill_name: str,
    status: str,
    duration_ms: int | None = None,
    quality_score: float | None = None,
) -> dict[str, Any]:
    return {
        "event": "trace",
        "run_id": run_id,
        "parent_run_id": None,
        "workflow_name": workflow_name,
        "agent_name": agent_name,
        "skill_name": skill_name,
        "status": status,
        "duration_ms": duration_ms,
        "quality_score": quality_score,
        "provider": FIXTURE_PROVIDER,
        "model": FIXTURE_MODEL,
        "token_usage": {"input": 0, "output": 0},
    }


async def _yield_control() -> None:
    await asyncio.sleep(0)


async def generate_learning_path(
    *,
    user_id: str,
    course_id: str,
    target_node_id: str | None = None,
    options: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Return a CoursePlanResponse-shaped fixture."""

    first_node = target_node_id or "00000000-0000-0000-0000-000000000201"
    return {
        "course_id": course_id,
        "path": [
            {
                "node_id": str(first_node),
                "title": "SQL injection basics",
                "status": "ready",
                "prerequisites": [],
            },
            {
                "node_id": "00000000-0000-0000-0000-000000000202",
                "title": "Parameterized queries",
                "status": "locked",
                "prerequisites": [str(first_node)],
            },
        ],
    }


async def run_assessment(
    *,
    user_id: str,
    course_id: str,
    answers: list[dict[str, Any]],
    **_: Any,
) -> dict[str, Any]:
    """Return an AssessmentRunResponse-shaped fixture."""

    assessment = {
        "score": 0.78,
        "feedback": (
            "The SQL injection fundamentals are mostly understood. Continue "
            "with parameterized-query practice and evidence-backed labs."
        ),
        "updated_capabilities": [
            {
                "dimension": "web_security",
                "score": 0.42,
                "confidence": 0.65,
                "evidence_count": 1,
            }
        ],
    }
    return {
        **assessment,
        "assessment": assessment,
    }


async def build_learning_persona(
    *,
    user_id: str,
    message: str,
    dialogue_turns: list[dict[str, str]] | None = None,
    history: list[dict[str, str]] | None = None,
    **_: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Yield profile-building SSE events."""

    run_id = str(uuid4())
    yield {
        "event": "progress",
        "node_name": "validate",
        "agent_id": "career_planner",
        "skill_id": "BuildLearningPersona",
        "percentage": 10,
        "status": "running",
    }
    yield _trace_event(
        run_id=run_id,
        workflow_name="profile_build",
        agent_name="career_planner",
        skill_name="BuildLearningPersona",
        status="running",
    )
    await _yield_control()

    chunks = [
        "I have identified your current learning goal as ",
        "Web security fundamentals, ",
        "with SQL injection as the first practice topic.",
    ]
    for index, content in enumerate(chunks, start=1):
        yield {"event": "token", "content": content, "index": index}
        await _yield_control()

    yield _trace_event(
        run_id=run_id,
        workflow_name="profile_build",
        agent_name="career_planner",
        skill_name="BuildLearningPersona",
        status="success",
        duration_ms=1200,
        quality_score=0.85,
    )
    yield {
        "event": "done",
        "run_id": run_id,
        "final_output_ref": f"user_profiles/{user_id}",
        "quality_score": 0.85,
    }


async def ask_tutor(
    *,
    user_id: str,
    course_id: str,
    question: str,
    context: dict[str, Any] | None = None,
    **_: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Yield tutor-answer SSE events."""

    run_id = str(uuid4())
    yield {
        "event": "progress",
        "node_name": "retrieve",
        "agent_id": "career_planner",
        "skill_id": "RouteTutorQuestion",
        "percentage": 30,
        "status": "running",
    }
    yield {"event": "evidence", **_evidence_chunk()}
    yield _trace_event(
        run_id=run_id,
        workflow_name="tutor_routing",
        agent_name="career_planner",
        skill_name="RouteTutorQuestion",
        status="running",
    )
    await _yield_control()

    chunks = [
        "Use parameterized queries because the SQL structure stays fixed. ",
        "User input is passed as values, ",
        "so it cannot become executable SQL syntax.",
    ]
    for index, content in enumerate(chunks, start=1):
        yield {"event": "token", "content": content, "index": index}
        await _yield_control()

    yield _trace_event(
        run_id=run_id,
        workflow_name="tutor_routing",
        agent_name="career_planner",
        skill_name="RouteTutorQuestion",
        status="success",
        duration_ms=800,
        quality_score=0.82,
    )
    yield {
        "event": "done",
        "run_id": run_id,
        "final_output_ref": "agent_messages/fixture-tutor",
        "quality_score": 0.82,
    }


async def generate_resource(
    *,
    course_id: str,
    user_id: str,
    kp_id: str,
    type: str | None = None,
    resource_type: str | None = None,
    options: dict[str, Any] | None = None,
    **_: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Yield resource-generation SSE events."""

    run_id = str(uuid4())
    resource_id = str(uuid4())
    resolved_type = resource_type or type or "doc"

    yield {
        "event": "progress",
        "node_name": "retrieve",
        "agent_id": "doc_archivist",
        "skill_id": f"Generate{resolved_type.title()}",
        "percentage": 20,
        "status": "running",
    }
    yield _trace_event(
        run_id=run_id,
        workflow_name=f"course_{course_id}_resource_{resolved_type}",
        agent_name="doc_archivist",
        skill_name=f"Generate{resolved_type.title()}",
        status="running",
    )
    yield {"event": "evidence", **_evidence_chunk()}
    await _yield_control()

    chunks = [
        f"# SQL injection {resolved_type} fixture\n\n",
        "This generated resource explains the risk model, ",
        "shows a vulnerable query, ",
        "and closes with a parameterized-query remediation checklist.",
    ]
    for index, content in enumerate(chunks, start=1):
        yield {"event": "token", "content": content, "index": index}
        await _yield_control()

    yield {
        "event": "artifact",
        "resource_id": resource_id,
        "resource_type": resolved_type,
        "object_key": f"local/{resolved_type}/{resource_id}.md",
        "title": f"SQL injection {resolved_type} fixture",
    }
    yield _trace_event(
        run_id=run_id,
        workflow_name=f"course_{course_id}_resource_{resolved_type}",
        agent_name="doc_archivist",
        skill_name=f"Generate{resolved_type.title()}",
        status="success",
        duration_ms=1500,
        quality_score=0.86,
    )
    yield {
        "event": "done",
        "run_id": run_id,
        "final_output_ref": f"generated_resources/{resource_id}",
        "quality_score": 0.86,
    }
