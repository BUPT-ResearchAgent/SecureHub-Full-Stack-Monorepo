from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.models.resource.generated_resource import GeneratedResource
from app.runtime.actions import WorkflowActionService
from app.runtime.contracts import ExecutionMode, ProviderSelection
from app.runtime.harness.context import ExecutionContext
from app.services.workflow_application_service import WorkflowApplicationError, WorkflowApplicationService


def _context(user_id):
    return ExecutionContext(
        workflow_run_id=uuid4(),
        step_attempt_id=uuid4(),
        agent_run_id=uuid4(),
        user_id=user_id,
        mode=ExecutionMode.FIXTURE,
        provider_selection=ProviderSelection(requested_provider="fixture", requested_model="fixture-v1"),
    )


async def _seed_capability(sqlite_session):
    user_id = uuid4()
    sqlite_session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Assessment User"))
    sqlite_session.add(UserProfile(user_id=user_id, dimensions={"weak_points": ["http-basics"]}))
    sqlite_session.add(
        UserCapability(
            user_id=user_id,
            dimension="web_security",
            score=0.6,
            confidence=0.8,
            evidence_count=2,
            metadata_={},
        )
    )
    await sqlite_session.commit()
    return user_id


def _state(*, persona_dimensions):
    return {
        "run_assessment": {
            "output": {
                "score": 0.75,
                "feedback": "继续巩固参数化查询。",
                "capability_delta": {"web_security": 0.15},
                "weak_kp_ids": ["kp-sqli"],
                "next_recommendation": "复习参数化查询后继续 SQL 注入防护。",
            },
            "evidence_snapshot_ids": [str(uuid4()), str(uuid4()), str(uuid4())],
        },
        "update_capability": {"output": {"capability_delta": {"web_security": 0.15}}},
        "update_persona": {"output": {"dimensions": persona_dimensions}},
        "quality_check": {"output": {"accept": True}},
    }


@pytest.mark.anyio
async def test_atomic_assessment_feedback_persists_before_after_audit(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    actions = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())

    result = await actions.persist_assessment_feedback(
        {
            "user_id": str(user_id),
            "answers": [{"quiz_item_id": "q1", "question": "Which query is safe?", "answer": "B"}],
            "quiz_artifact_id": "resource-quiz-1",
            "context": {"kp_id": "kp-sqli"},
        },
        _state(persona_dimensions={"weak_points": ["kp-sqli"]}),
        _context(user_id),
    )
    await sqlite_session.commit()

    capability = await sqlite_session.scalar(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.dimension == "web_security",
        )
    )
    profile = await sqlite_session.get(UserProfile, user_id)
    audit = result["assessment_audit"]
    assert capability is not None and capability.score == pytest.approx(0.75)
    assert capability.evidence_count == 5
    assert profile is not None and profile.dimensions["weak_points"] == ["kp-sqli"]
    assert audit["quiz"]["artifact_id"] == "resource-quiz-1"
    assert audit["quiz"]["submitted_answers"] == [
        {"quiz_item_id": "q1", "prompt": "Which query is safe?", "answer": "B"}
    ]
    change = audit["capability_changes"][0]
    assert change["dimension"] == "web_security"
    assert change["before_score"] == pytest.approx(0.6)
    assert change["after_score"] == pytest.approx(0.75)
    assert change["delta"] == pytest.approx(0.15)
    assert change["confidence"] == pytest.approx(0.8)
    assert change["evidence_count"] == 5
    assert audit["persona"]["before_dimensions"] == {"weak_points": ["http-basics"]}
    assert audit["persona"]["after_dimensions"] == {"weak_points": ["kp-sqli"]}


@pytest.mark.anyio
async def test_atomic_assessment_feedback_rolls_back_capability_when_profile_write_fails(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    actions = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())

    with pytest.raises(Exception):
        await actions.persist_assessment_feedback(
            {"user_id": str(user_id), "answers": [], "context": {}},
            _state(persona_dimensions={"not_json": object()}),
            _context(user_id),
        )

    capability = await sqlite_session.scalar(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.dimension == "web_security",
        )
    )
    profile = await sqlite_session.get(UserProfile, user_id)
    assert capability is not None and capability.score == pytest.approx(0.6)
    assert capability.evidence_count == 2
    assert profile is not None and profile.dimensions == {"weak_points": ["http-basics"]}


@pytest.mark.anyio
async def test_atomic_assessment_feedback_ignores_untrusted_persona_patch(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    actions = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())

    result = await actions.persist_assessment_feedback(
        {
            "user_id": str(user_id),
            "answers": [{"quiz_item_id": "q1", "answer": "B"}],
            "capability_dimensions": ["web_security"],
            "persona_dimension_keys": ["weak_points"],
        },
        _state(persona_dimensions={"career_goal": "unsupported replacement"}),
        _context(user_id),
    )
    await sqlite_session.commit()

    capability = await sqlite_session.scalar(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.dimension == "web_security",
        )
    )
    profile = await sqlite_session.get(UserProfile, user_id)
    assert capability is not None and capability.score == pytest.approx(0.75)
    assert capability.evidence_count == 5
    assert profile is not None and profile.dimensions["weak_points"][-1].startswith("评估待复盘：")
    assert "career_goal" not in profile.dimensions
    assert result["assessment_audit"]["persona"]["projection"] == "assessment_feedback"


@pytest.mark.anyio
async def test_atomic_assessment_feedback_normalises_course_subconcepts_and_projects_a_gap(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    actions = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())
    state = _state(persona_dimensions={})
    state["update_capability"] = {
        "output": {"capability_delta": {"sql_injection_defense": -0.1, "stored_procedures": -0.1}}
    }

    result = await actions.persist_assessment_feedback(
        {
            "user_id": str(user_id),
            "answers": [{"quiz_item_id": "q1", "answer": "A"}],
            "domain": "course_websec",
            "capability_dimensions": ["web_security"],
            "persona_dimension_keys": ["weak_points"],
        },
        state,
        _context(user_id),
    )
    await sqlite_session.commit()

    capability = await sqlite_session.scalar(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.dimension == "web_security",
        )
    )
    profile = await sqlite_session.get(UserProfile, user_id)
    change = result["assessment_audit"]["capability_changes"][0]
    assert capability is not None and capability.score == pytest.approx(0.4)
    assert change["dimension"] == "web_security"
    assert change["source_dimensions"] == ["sql_injection_defense", "stored_procedures"]
    assert profile is not None and profile.dimensions["weak_points"][-1].startswith("评估待复盘：")
    assert result["assessment_audit"]["persona"]["projection"] == "assessment_feedback"


@pytest.mark.anyio
async def test_course_assessment_does_not_mutate_another_existing_capability(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    from app.db.models.identity.user_capability import UserCapability

    sqlite_session.add(
        UserCapability(
            user_id=user_id,
            dimension="engineering_practice",
            score=0.9,
            confidence=0.8,
            evidence_count=4,
        )
    )
    await sqlite_session.flush()
    actions = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())
    state = _state(persona_dimensions={"weak_points": []})
    state["update_capability"] = {
        "output": {"capability_delta": {"engineering_practice": -0.1}}
    }

    result = await actions.persist_assessment_feedback(
        {
            "user_id": str(user_id),
            "answers": [{"quiz_item_id": "q1", "answer": "A"}],
            "domain": "course_websec",
            "capability_dimensions": ["web_security"],
            "persona_dimension_keys": ["weak_points"],
        },
        state,
        _context(user_id),
    )
    await sqlite_session.commit()

    engineering = await sqlite_session.scalar(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.dimension == "engineering_practice",
        )
    )
    assert engineering is not None and engineering.score == pytest.approx(0.9)
    change = result["assessment_audit"]["capability_changes"][0]
    assert change["dimension"] == "web_security"
    assert change["source_dimensions"] == ["engineering_practice"]


@pytest.mark.anyio
async def test_real_assessment_requires_an_active_owned_evidenced_quiz_artifact(sqlite_session) -> None:
    user_id = await _seed_capability(sqlite_session)
    course_id = uuid4()
    artifact_id = uuid4()
    sqlite_session.add(
        GeneratedResource(
            id=artifact_id,
            user_id=user_id,
            course_id=course_id,
            resource_type="quiz",
            title="SQL injection quiz",
            content={},
            evidence_chunk_ids=[str(uuid4()), str(uuid4()), str(uuid4())],
            status="active",
            metadata_={},
        )
    )
    await sqlite_session.commit()

    await WorkflowApplicationService._validate_assessment_quiz_artifact(
        sqlite_session,
        user_id=str(user_id),
        course_id=str(course_id),
        quiz_artifact_id=str(artifact_id),
        mode=ExecutionMode.REAL,
    )

    with pytest.raises(WorkflowApplicationError, match="unavailable") as error:
        await WorkflowApplicationService._validate_assessment_quiz_artifact(
            sqlite_session,
            user_id=str(user_id),
            course_id=str(uuid4()),
            quiz_artifact_id=str(artifact_id),
            mode=ExecutionMode.REAL,
        )
    assert error.value.code == "INVALID_ASSESSMENT_ARTIFACT"
