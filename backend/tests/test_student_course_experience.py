# Status: real

"""Focused contract tests for the current-student WEBSEC-101 projection."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints.courses import get_student_course_experience
from app.db.models.identity.user import User
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID
from app.db.seeds.seed_showcase_course import (
    SHOWCASE_DEMO_STUDENT_DISPLAY_NAME,
    _student_id,
    run,
)


@pytest.mark.anyio
async def test_student_experience_uses_current_student_records_and_quality_resources(sqlite_session) -> None:
    await run(sqlite_session)
    demo_student = await sqlite_session.get(User, DEMO_USER_ID)
    accelerated_student = await sqlite_session.get(User, _student_id("qinglan"))
    recovery_student = await sqlite_session.get(User, _student_id("hanyue"))
    assert demo_student is not None and accelerated_student is not None and recovery_student is not None

    demo = await get_student_course_experience(
        course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=demo_student
    )
    accelerated = await get_student_course_experience(
        course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=accelerated_student
    )
    recovery = await get_student_course_experience(
        course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=recovery_student
    )

    assert accelerated.profile.display_name != recovery.profile.display_name
    assert accelerated.profile.learning_story != recovery.profile.learning_story
    assert accelerated.progress_percent != recovery.progress_percent
    assert accelerated.data_status == "ready"
    assert demo.data_status == "ready"
    assert demo.missing_dependencies == []
    assert demo.profile.display_name == SHOWCASE_DEMO_STUDENT_DISPLAY_NAME
    assert demo.profile.learning_story == "input_validation"
    assert demo.tasks
    assert demo.tutor_exchanges
    assert demo.assessment.scored_attempt_count > 0
    assert demo.assignments
    assert set(resource.resource_type for resource in demo.resources) == {
        "doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"
    }
    assert {item.dimension: item.score for item in accelerated.capabilities} != {
        item.dimension: item.score for item in recovery.capabilities
    }

    resource_by_type = {item.resource_type: item for item in accelerated.resources}
    assert set(resource_by_type) == {"doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"}
    assert len(str(resource_by_type["doc"].content["body"])) >= 900
    assert 10 <= len(resource_by_type["ppt"].content["slides"]) <= 14
    assert resource_by_type["mindmap"].content["depth"] == 3
    assert len(resource_by_type["mindmap"].content["nodes"]) >= 20
    assert resource_by_type["readings"].source_kind == "external-preview"
    assert resource_by_type["video"].content["artifact_kind"] == "讲解脚本/分镜"
    assert resource_by_type["video"].content["is_playable_video"] is False
    assert all(item.source_boundary for item in accelerated.resources)

    assert len(accelerated.tutor_exchanges) == 5
    insufficient = [item for item in accelerated.tutor_exchanges if item.evidence_status == "insufficient"]
    assert len(insufficient) == 1
    assert insufficient[0].evidence == []
    assert all(item.source_kind == "curated-demo" for item in accelerated.tutor_exchanges)

    assert accelerated.assignments
    assert all(
        assignment.published_score is None
        for assignment in accelerated.assignments
        if assignment.learner_status != "published"
    )
    assert all("答案" not in assignment.next_action for assignment in accelerated.assignments)

    own_attempt_count = await sqlite_session.scalar(
        select(func.count(QuizAttempt.id)).where(
            QuizAttempt.user_id == accelerated_student.id,
            QuizAttempt.score.is_not(None),
        )
    )
    assert accelerated.assessment.scored_attempt_count == own_attempt_count
    assert accelerated.assessment.metrics


@pytest.mark.anyio
async def test_student_experience_rejects_teacher_and_unenrolled_student(sqlite_session) -> None:
    await run(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    with pytest.raises(HTTPException) as teacher_denied:
        await get_student_course_experience(
            course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=teacher
        )
    assert teacher_denied.value.status_code == 403
    assert teacher_denied.value.detail["code"] == "STUDENT_ROLE_REQUIRED"

    outsider = User(
        id=uuid4(),
        email="student-without-websec-enrollment@securehub.local",
        display_name="未选课测试花名",
        hashed_password=None,
        is_active=True,
        role="student",
    )
    sqlite_session.add(outsider)
    await sqlite_session.flush()

    with pytest.raises(HTTPException) as enrollment_denied:
        await get_student_course_experience(
            course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=outsider
        )
    assert enrollment_denied.value.status_code == 403
    assert enrollment_denied.value.detail["code"] == "COURSE_ENROLLMENT_REQUIRED"
