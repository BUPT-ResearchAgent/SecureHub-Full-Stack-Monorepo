# Status: real

"""Focused coverage for the durable teacher quiz-candidate to assembly handoff."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints.teaching import prepare_course_quiz_candidates
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.quiz_item import QuizItem
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID
from app.db.seeds.seed_showcase_course import run as seed_showcase_course
from app.schemas.teacher_production import (
    QuizCandidateFilterRequest,
    QuizCandidatePrepareRequest,
)
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
    assert all(item.difficulty == 3 for item in preview.items)
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


@pytest.mark.anyio
async def test_quiz_candidate_preflight_reports_real_zero_and_explicit_alternatives(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    http_node = await sqlite_session.scalar(
        select(KnowledgeNode).where(
            KnowledgeNode.course_id == COURSE_WEBSEC_ID,
            KnowledgeNode.name == "HTTP / HTTPS 协议基础",
        )
    )
    assert teacher is not None and http_node is not None

    service = TeacherProductionService(sqlite_session)
    exact_filter = QuizCandidateFilterRequest(
        knowledge_node_ids=[http_node.id],
        question_types=["short_answer"],
        quantity=8,
        target_difficulty=3,
    )
    audit_before = await sqlite_session.scalar(
        select(func.count()).select_from(GovernanceAuditEvent)
    )
    availability = await service.preflight_quiz_candidates(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=exact_filter,
    )

    assert availability.available_count == 0
    assert availability.can_fulfill_requested_quantity is False
    assert availability.alternatives
    assert any(
        alternative.target_difficulty == 3
        and not alternative.knowledge_node_ids
        and not alternative.question_types
        and alternative.available_count >= 8
        and alternative.can_fulfill_requested_quantity
        for alternative in availability.alternatives
    )
    assert await sqlite_session.scalar(select(func.count()).select_from(GovernanceAuditEvent)) == audit_before

    with pytest.raises(TeacherProductionError) as unavailable:
        await service.prepare_quiz_candidates(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=QuizCandidatePrepareRequest(
                **exact_filter.model_dump(),
                teaching_intent="Keep the exact zero-result filter visible instead of substituting any question.",
            ),
        )
    assert unavailable.value.code == "QUIZ_CANDIDATES_UNAVAILABLE"
    assert unavailable.value.status_code == 409
    assert unavailable.value.detail is not None
    error_availability = unavailable.value.detail["availability"]
    assert isinstance(error_availability, dict)
    assert error_availability["available_count"] == 0

    # The HTTP adapter must preserve the server-derived preflight data instead
    # of collapsing a real no-result business state into a generic failure.
    await sqlite_session.commit()
    with pytest.raises(HTTPException) as http_error:
        await prepare_course_quiz_candidates(
            course_id=COURSE_WEBSEC_ID,
            payload=QuizCandidatePrepareRequest(
                **exact_filter.model_dump(),
                teaching_intent="Keep the exact zero-result filter visible instead of substituting any question.",
            ),
            session=sqlite_session,
            user=teacher,
        )
    assert http_error.value.status_code == 409
    assert isinstance(http_error.value.detail, dict)
    assert http_error.value.detail["code"] == "QUIZ_CANDIDATES_UNAVAILABLE"
    assert http_error.value.detail["availability"]["available_count"] == 0

    student_after_rollback = await sqlite_session.scalar(
        select(User).where(User.role == "student").order_by(User.email)
    )
    assert student_after_rollback is not None
    with pytest.raises(TeacherProductionError) as denied:
        await service.preflight_quiz_candidates(
            actor=student_after_rollback,
            course_id=COURSE_WEBSEC_ID,
            payload=exact_filter,
        )
    assert denied.value.code == "TEACHER_ROLE_REQUIRED"
