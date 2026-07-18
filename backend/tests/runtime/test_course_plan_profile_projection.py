"""Regression coverage for server-owned profile-aware course planning."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agents.task_orchestrator.skills.generate_learning_path import (
    GenerateLearningPathInput,
    GenerateLearningPathOutput,
    PROMPT_TEMPLATE,
)
from app.db.models.identity.user import User
from app.db.models.identity.user_profile import UserProfile
from app.db.models.knowledge.course import Course
from app.db.models.learning.learning_task import LearningTask
from app.db.models.workflow_runtime import WorkflowRun
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.runtime.context_builder import ContextBuilder
from app.runtime.actions import WorkflowActionService
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
    assert len(baseline_plan["nodes"]) == 3

    related_treatments = (
        {**baseline_dimensions, "base_knowledge": "synthetic-advanced"},
        {**baseline_dimensions, "target_direction": "synthetic-application-security"},
        {**baseline_dimensions, "preferred_modality": ["video"]},
        {**baseline_dimensions, "weak_points": ["synthetic-assessment-weak-kp"]},
    )
    for treatment in related_treatments:
        treatment_plan = _fixture_plan(CoursePlanProfileSnapshot.from_dimensions(treatment)).model_dump(mode="json")
        assert len(treatment_plan["nodes"]) == 3
        assert treatment_plan != baseline_plan

    weak_point_plan = _fixture_plan(
        CoursePlanProfileSnapshot.from_dimensions(
            {**baseline_dimensions, "weak_points": ["synthetic-sql-injection-gap"]}
        )
    ).model_dump(mode="json")
    assert len(weak_point_plan["nodes"]) == 3
    assert weak_point_plan["nodes"][0]["metadata"]["fixture_weak_point_focus"] == "sql_injection"
    assert "parameterized-query boundary checks" in weak_point_plan["nodes"][0]["description"]
    assert "known_weak_point_reinforcement" in weak_point_plan["personalization_rationale"]
    assert all(
        node.get("id") not in {
            "fixture-assessment-gap-review",
            "fixture-known-gap-review",
            "fixture-general-gap-review",
        }
        for node in weak_point_plan["nodes"]
    )

    unrelated = CoursePlanProfileSnapshot.from_dimensions(
        {**baseline_dimensions, "unrelated_layout_preference": "synthetic-compact"}
    )
    assert unrelated == baseline
    assert _fixture_plan(unrelated).model_dump(mode="json") == baseline_plan
    assert "untrusted_note" not in baseline.compact_payload()


def test_course_plan_snapshot_normalises_fixture_persona_target_direction() -> None:
    snapshot = CoursePlanProfileSnapshot.from_dimensions(
        {"target_direction": "web_security_engineer"}
    )

    assert snapshot.target_direction == "web_defense"
    assert snapshot.rationale_codes() == ("web_defense_goal",)


@pytest.mark.anyio
async def test_fixture_weak_point_pairs_change_durable_task_title_without_leaking_profile_text(sqlite_session) -> None:
    """P05-04 regression: weak-point treatment must survive task materialisation."""
    user = User(id=uuid4(), email="paired-profile@example.test", display_name="Paired Profile Learner")
    course = Course(id=uuid4(), code="PAIRED-PROFILE-101", title="Paired profile test course")
    sqlite_session.add_all([user, course])
    await sqlite_session.commit()

    common_dimensions = {
        "base_knowledge": "synthetic-foundation",
        "target_direction": "synthetic-web-defense",
        "preferred_modality": ["doc"],
        "untrusted_note": "must never become durable task content",
    }
    control = CoursePlanProfileSnapshot.from_dimensions(
        {**common_dimensions, "weak_points": ["synthetic-general-gap"]}
    )
    treatment = CoursePlanProfileSnapshot.from_dimensions(
        {**common_dimensions, "weak_points": ["synthetic-assessment-weak-kp"]}
    )
    unrelated_layout = CoursePlanProfileSnapshot.from_dimensions(
        {
            **common_dimensions,
            "weak_points": ["synthetic-general-gap"],
            "unrelated_layout_preference": "synthetic-compact",
        }
    )
    assert unrelated_layout == control

    action_service = WorkflowActionService(sqlite_session, storage_service=SimpleNamespace())

    async def persist(snapshot: CoursePlanProfileSnapshot) -> tuple[dict[str, object], list[LearningTask]]:
        plan = _fixture_plan(snapshot).model_dump(mode="json")
        result = await action_service.persist_learning_path(
            {
                "user_id": str(user.id),
                "course_id": str(course.id),
                "query": "Generate a bounded paired-profile path",
                "profile_snapshot": snapshot.compact_payload(),
            },
            {"generate_path": {"output": plan}},
            SimpleNamespace(),
        )
        await sqlite_session.commit()
        tasks = list(
            (
                await sqlite_session.execute(
                    select(LearningTask)
                    .where(LearningTask.path_id == UUID(str(result["learning_path_id"])))
                    .order_by(LearningTask.order_index)
                )
            ).scalars()
        )
        return result, tasks

    control_result, control_tasks = await persist(control)
    treatment_result, treatment_tasks = await persist(treatment)

    assert control_result["task_count"] == len(control_tasks) == 3
    assert treatment_result["task_count"] == len(treatment_tasks) == 3
    assert control_tasks[0].title == "Reinforce request-to-query boundaries: general secure-development review"
    assert treatment_tasks[0].title == "Reinforce request-to-query boundaries: assessment-feedback review"
    assert control_tasks[0].title != treatment_tasks[0].title
    assert [
        (task.order_index, task.task_type, task.kp_id, task.status) for task in control_tasks
    ] == [
        (task.order_index, task.task_type, task.kp_id, task.status) for task in treatment_tasks
    ]
    persisted = json.dumps(
        {
            "control": [task.title for task in control_tasks] + [task.metadata_ for task in control_tasks],
            "treatment": [task.title for task in treatment_tasks] + [task.metadata_ for task in treatment_tasks],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    assert "synthetic-general-gap" not in persisted
    assert "synthetic-assessment-weak-kp" not in persisted
    assert "must never become durable task content" not in persisted
    assert _fixture_plan(unrelated_layout).model_dump(mode="json") == _fixture_plan(control).model_dump(mode="json")


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
