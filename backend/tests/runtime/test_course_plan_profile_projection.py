"""Regression coverage for server-owned profile-aware course planning."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.task_orchestrator.skills.generate_learning_path import (
    GenerateLearningPathInput,
    GenerateLearningPathOutput,
    PROMPT_TEMPLATE,
)
from app.db.models.identity.user import User
from app.db.models.identity.user_profile import UserProfile
from app.db.models.workflow_runtime import WorkflowRun
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.runtime.context_builder import ContextBuilder
from app.runtime.harness.fixtures import fixture_llm_output
from app.runtime.workflows.product_workflows import CoursePlanInput, _path_input
from app.schemas.agent_control import WorkflowRunStartRequest
from app.schemas.course_plan_profile import CoursePlanProfileSnapshot
from app.services.workflow_application_service import WorkflowApplicationService


def _fixture_plan(snapshot: CoursePlanProfileSnapshot) -> GenerateLearningPathOutput:
    root = CoursePlanInput(
        user_id="fixture-user",
        course_id=str(COURSE_WEBSEC_ID),
        query="Generate a personalised WEBSEC-101 path",
        profile_snapshot=snapshot,
        profile_reason_codes=snapshot.rationale_codes(),
        persona_summary=snapshot.prompt_summary(),
    ).model_dump(mode="json")
    task_input = GenerateLearningPathInput.model_validate(_path_input(root, {}))
    prompt = ContextBuilder().build(
        prompt_template=PROMPT_TEMPLATE,
        input_value=task_input,
        evidence=[],
        persona_summary=snapshot.prompt_summary(),
        output_model=GenerateLearningPathOutput,
    )
    return GenerateLearningPathOutput.model_validate(
        fixture_llm_output("GenerateLearningPath", prompt=prompt)
    )


def test_course_plan_fixture_uses_related_server_profile_dimensions_and_ignores_layout() -> None:
    baseline_dimensions = {
        "base_knowledge": "synthetic-baseline",
        "target_direction": "synthetic-web-defense",
        "preferred_modality": ["doc"],
        "weak_points": ["synthetic-baseline-kp"],
        "untrusted_note": "must not enter a path root",
    }
    baseline = CoursePlanProfileSnapshot.from_dimensions(baseline_dimensions)
    baseline_plan = _fixture_plan(baseline).model_dump(mode="json")

    related_treatments = (
        {**baseline_dimensions, "base_knowledge": "synthetic-advanced"},
        {**baseline_dimensions, "target_direction": "synthetic-application-security"},
        {**baseline_dimensions, "preferred_modality": ["video"]},
        {**baseline_dimensions, "weak_points": ["synthetic-assessment-weak-kp"]},
    )
    for treatment in related_treatments:
        assert _fixture_plan(CoursePlanProfileSnapshot.from_dimensions(treatment)).model_dump(mode="json") != baseline_plan

    unrelated = CoursePlanProfileSnapshot.from_dimensions(
        {**baseline_dimensions, "unrelated_layout_preference": "synthetic-compact"}
    )
    assert unrelated == baseline
    assert _fixture_plan(unrelated).model_dump(mode="json") == baseline_plan
    assert "untrusted_note" not in baseline.compact_payload()


@pytest.mark.anyio
async def test_course_plan_root_rehydrates_profile_from_authenticated_durable_state(sqlite_session) -> None:
    user_id = uuid4()
    durable_dimensions = {
        "base_knowledge": "synthetic-advanced",
        "target_direction": "synthetic-application-security",
        "preferred_modality": ["video", "unbounded-value"],
        "weak_points": ["synthetic-assessment-weak-kp"],
        "untrusted_note": "never persist this",
    }
    sqlite_session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Course Plan Learner"))
    sqlite_session.add(UserProfile(user_id=user_id, dimensions=durable_dimensions))
    await sqlite_session.commit()

    bind = sqlite_session.bind
    assert bind is not None
    sessions = async_sessionmaker(bind, expire_on_commit=False)
    service = WorkflowApplicationService(sessions)
    response = await service.start(
        WorkflowRunStartRequest(
            workflow="course_plan_v1",
            user_id=str(user_id),
            course_id=str(COURSE_WEBSEC_ID),
            mode="fixture",
            provider="fixture",
            input={
                "query": "Generate a personalised WEBSEC-101 path",
                "user_id": str(uuid4()),
                "profile_snapshot": {"base_knowledge": "forged"},
                "profile_reason_codes": ["foundation_reinforcement"],
                "profile_dimensions": {"forged": "browser"},
                "persona_summary": "forged browser profile",
            },
        ),
        idempotency_key="course-plan-profile-projection",
        actor_user_id=user_id,
    )

    expected = CoursePlanProfileSnapshot.from_dimensions(durable_dimensions)
    async with sessions() as session:
        root = await session.get(WorkflowRun, response.run_id)
        assert root is not None
        saved = dict(root.input_payload or {})

    assert saved["profile_snapshot"] == expected.compact_payload()
    assert saved["profile_reason_codes"] == list(expected.rationale_codes())
    assert json.loads(saved["persona_summary"]) == expected.compact_payload()
    assert saved["user_id"] == str(user_id)
    assert "profile_dimensions" not in saved
    assert "forged" not in json.dumps(saved, ensure_ascii=False, sort_keys=True)
