# Status: real

"""Focused coverage for the durable teacher quiz-candidate to assembly handoff."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.learning.quiz_item import QuizItem
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID
from app.db.seeds.seed_showcase_course import run as seed_showcase_course
from app.schemas.teacher_production import QuizCandidatePrepareRequest
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


@pytest.mark.anyio
async def test_quiz_candidates_are_scoped_audited_and_do_not_create_questions(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    before = await sqlite_session.scalar(select(func.count()).select_from(QuizItem))
    preview = await TeacherProductionService(sqlite_session).prepare_quiz_candidates(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=QuizCandidatePrepareRequest(
            quantity=8,
            target_difficulty=3,
            teaching_intent=(
                "Prepare a mixed-difficulty, evidence-backed input validation review "
                "before the next class assignment."
            ),
        ),
    )

    assert preview.source == "persisted_quality_passed_bank"
    assert preview.live_generation_started is False
    assert preview.requested_quantity == 8
    assert len(preview.items) == 8
    assert preview.available_count >= len(preview.items)
    assert all(item.quality_state == "passed" and item.evidence_count >= 1 for item in preview.items)
    assert await sqlite_session.scalar(select(func.count()).select_from(QuizItem)) == before

    audit = await sqlite_session.scalar(
        select(GovernanceAuditEvent)
        .where(GovernanceAuditEvent.action == "quiz_candidate.prepare")
        .order_by(GovernanceAuditEvent.created_at.desc())
    )
    assert audit is not None
    assert audit.object_id == COURSE_WEBSEC_ID
    assert audit.metadata_["live_generation_started"] is False
    assert audit.metadata_["selected_quiz_item_ids"] == [str(item.id) for item in preview.items]

    with pytest.raises(TeacherProductionError) as denied:
        await TeacherProductionService(sqlite_session).prepare_quiz_candidates(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=QuizCandidatePrepareRequest(
                knowledge_node_ids=[uuid4()],
                quantity=1,
                target_difficulty=3,
                teaching_intent="Reject a forged knowledge-node identifier before any question selection.",
            ),
        )
    assert denied.value.code == "QUIZ_CANDIDATE_SCOPE_DENIED"
