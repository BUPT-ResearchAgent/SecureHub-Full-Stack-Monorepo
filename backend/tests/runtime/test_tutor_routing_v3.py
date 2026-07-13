from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.db.models.identity.user import User
from app.db.models.identity.user_profile import UserProfile
from app.runtime.workflows.tutor_routing_v3 import TUTOR_ROUTING_V3, _base_input
from app.services.workflow_application_service import WorkflowApplicationService


@pytest.mark.anyio
async def test_tutor_persona_projection_keeps_current_durable_dimensions(sqlite_session) -> None:
    user_id = uuid4()
    sqlite_session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Tutor User"))
    sqlite_session.add(
        UserProfile(
            user_id=user_id,
            dimensions={
                "knowledge_basis": "web development foundations",
                "cognitive_style": "case driven",
                "easy_mistakes": ["URL encoding"],
                "learning_pace": "4 hours weekly",
                "interest_anchors": ["Web security"],
                "career_goal": "security engineer",
                "untrusted_extra": "must not be projected",
            },
        )
    )
    await sqlite_session.commit()

    summary = await WorkflowApplicationService._tutor_persona_summary(sqlite_session, str(user_id))

    assert json.loads(summary) == {
        "career_goal": "security engineer",
        "cognitive_style": "case driven",
        "easy_mistakes": ["URL encoding"],
        "interest_anchors": ["Web security"],
        "knowledge_basis": "web development foundations",
        "learning_pace": "4 hours weekly",
    }


def test_tutor_v3_maps_only_bounded_course_context() -> None:
    mapped = _base_input(
        {
            "user_id": "user-1",
            "course_id": "course-1",
            "question": "Why are parameterized queries safer?",
            "context": {"kp_id": "kp-sqli", "current_path_node_ids": ["node-1"], "raw_answer": "ignored"},
        },
        {},
    )

    assert mapped["course_id"] == "course-1"
    assert mapped["current_kp_id"] == "kp-sqli"
    assert mapped["learning_context"] == {"current_path_node_ids": ["node-1"]}
    assert "raw_answer" not in mapped["learning_context"]


def test_tutor_v3_retains_server_owned_persona_summary_for_engine_replay() -> None:
    saved_root_input = {
        "user_id": "user-1",
        "course_id": "course-1",
        "question": "How should I mitigate SQL injection?",
        "persona_summary": '{"career_goal":"security engineer"}',
    }

    replay_input = TUTOR_ROUTING_V3.input_model.model_validate(saved_root_input).model_dump(mode="json")

    assert replay_input["persona_summary"] == saved_root_input["persona_summary"]
