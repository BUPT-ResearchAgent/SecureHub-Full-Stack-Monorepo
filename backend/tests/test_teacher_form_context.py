# Status: real

"""Focused contract tests for teacher FormAssist candidates and audit boundaries."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.api.v1.endpoints.teaching import record_teacher_form_prefill, teacher_form_context
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.teaching.teacher_production import Assessment
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID
from app.db.seeds.seed_showcase_course import run as seed_showcase_course
from app.schemas.teacher_production import (
    AssessmentCreateRequest,
    AssessmentVersionCreateRequest,
    AssessmentVersionItemRequest,
    CreateTeachingRecommendationRequest,
    QuizCandidateFilterRequest,
)
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


@pytest.mark.anyio
async def test_teacher_form_context_is_scoped_editable_and_audited(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    student = await sqlite_session.scalar(
        select(User).where(User.role == "student").order_by(User.email)
    )
    assert teacher is not None and student is not None

    assessment_count_before = await sqlite_session.scalar(select(func.count()).select_from(Assessment))
    context = await teacher_form_context(
        course_id=COURSE_WEBSEC_ID,
        purpose="assignment",
        session=sqlite_session,
        user=teacher,
    )

    assert context.course_id == COURSE_WEBSEC_ID
    assert context.dependency is not None and context.dependency.ready is True
    assert len(context.teaching_classes) == 2
    assert len(context.publishable_quiz_items) == 36
    assert all(item.state == "curated / passed" for item in context.publishable_quiz_items)
    draft_items = context.draft["items"]
    assert isinstance(draft_items, list) and len(draft_items) == 8
    assert {item["quiz_item_id"] for item in draft_items} <= {
        str(item.id) for item in context.publishable_quiz_items
    }
    assert await sqlite_session.scalar(select(func.count()).select_from(Assessment)) == assessment_count_before

    with pytest.raises(TeacherProductionError) as denied:
        await TeacherProductionService(sqlite_session).get_form_context(
            actor=student,
            course_id=COURSE_WEBSEC_ID,
            purpose="assignment",
        )
    assert denied.value.code == "TEACHER_ROLE_REQUIRED"

    audit = await record_teacher_form_prefill(
        course_id=COURSE_WEBSEC_ID,
        purpose="assignment",
        session=sqlite_session,
        user=teacher,
    )
    assert audit.course_id == COURSE_WEBSEC_ID
    events = list(
        (
            await sqlite_session.execute(
                select(GovernanceAuditEvent).where(
                    GovernanceAuditEvent.action == "teacher_form.context_prefill"
                )
            )
        ).scalars()
    )
    assert len(events) == 1
    assert events[0].metadata_["purpose"] == "assignment"
    assert events[0].metadata_["does_not_submit"] is True

    service = TeacherProductionService(sqlite_session)
    assessment = await service.create_assessment(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=AssessmentCreateRequest(kind="assignment", logical_key="formassist-tamper-check"),
    )
    with pytest.raises(TeacherProductionError) as rejected_question:
        await service.create_assessment_version(
            actor=teacher,
            assessment_id=assessment.id,
            payload=AssessmentVersionCreateRequest(
                title="不应接受伪造题目",
                items=[
                    AssessmentVersionItemRequest(
                        quiz_item_id=uuid4(), position=1, points=10, grading_mode="objective"
                    )
                ],
            ),
        )
    assert rejected_question.value.code == "ASSESSMENT_SCOPE_DENIED"

    with pytest.raises(TeacherProductionError) as rejected_evidence:
        await service.create_teaching_recommendation(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=CreateTeachingRecommendationRequest(
                source_snapshot_id=context.weakness_snapshots[0].id,
                evidence_snapshot_id=context.agent_evidence_pairs[0].evidence_snapshot_id,
                agent_run_id=uuid4(),
                title="不应接受伪造运行",
                actions=[
                    "保留现有教学节奏并在下一次课前核验运行与证据的课程归属。",
                    "仅在服务端确认关联后再让教师创建可编辑教学建议草稿。",
                ],
                rationale=(
                    "该请求只用于证明服务端仍执行运行与 Evidence 关联校验。即使前端能够提交一组"
                    "看似完整的字段，只要 AgentRun 不是成功且可验证地关联当前课程 Evidence 的结果，"
                    "服务端仍必须拒绝写入教学建议，也不能产生任何课程动作。教师只能从受控选择器选择"
                    "当前课程已完成运行及其证据，并在提交前说明快照范围、样本依据与后续审核计划。"
                ),
                expected_impact="预期结果是伪造运行被拒绝，避免不可信内容进入教师建议、课程更新或任何待审核教学动作。",
            ),
        )
    assert rejected_evidence.value.code == "INSUFFICIENT_EVIDENCE"


@pytest.mark.anyio
async def test_quiz_generation_formassist_prefill_uses_a_real_satisfiable_scope(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    service = TeacherProductionService(sqlite_session)
    context = await service.get_form_context(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        purpose="quiz_generation",
    )

    assert context.draft["knowledge_node_id"] is None
    assert context.draft["question_type"] is None
    assert context.draft["quantity"] == 8
    assert context.draft["difficulty"] == 3
    availability = await service.preflight_quiz_candidates(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=QuizCandidateFilterRequest(
            knowledge_node_ids=[],
            question_types=[],
            quantity=context.draft["quantity"],
            target_difficulty=context.draft["difficulty"],
        ),
    )
    assert availability.available_count >= 8
    assert availability.can_fulfill_requested_quantity is True
