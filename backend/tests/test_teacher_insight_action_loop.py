# Status: real

"""Focused Phase 3 coverage for explainable teaching insights and actions."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.agent.agent_run import AgentRun
from app.db.models.education.education_domain import CourseEnrollment, GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import (
    DEMO_COURSE_TEACHER_ID,
    DEMO_TEACHING_CLASS_ID,
    run as seed_education_domain,
)
from app.db.seeds.seed_showcase_course import run as seed_showcase_course
from app.schemas.teacher_production import (
    CreateTeachingRecommendationRequest,
    TeachingRecommendationDecisionRequest,
    WeaknessSnapshotRequest,
)
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


def _recommendation_payload(*, snapshot_id, agent_run_id, evidence_snapshot_id):
    return CreateTeachingRecommendationRequest(
        source_snapshot_id=snapshot_id,
        agent_run_id=agent_run_id,
        evidence_snapshot_id=evidence_snapshot_id,
        title="围绕输入边界与安全输出安排分层防御复盘",
        actions=[
            "为目标教学班补充输入校验、参数化查询和输出编码的防御性对照学习单，并明确每项控制的适用边界。",
            "使用同范围质量通过题目进行短测，比较有效覆盖率、错误率和平均分后再决定是否创建后续课程候选。",
        ],
        rationale=(
            "建议以当前班级快照中的真实可评分作答为依据，并引用当前课程范围内成功 AgentRun 关联的 Evidence。"
            "教师将先解释概念边界与错误模式，再安排不含可滥用攻击载荷的防御性检查活动；建议本身不会"
            "自动发布课程更新、作业、大纲或学生通知。"
        ),
        expected_impact="预计下一次同范围短测将提高相关知识点的有效覆盖率和平均分，并降低重复错误率；实际效果必须由新的真实快照复核。",
    )


@pytest.mark.anyio
async def test_weakness_snapshot_rejects_scope_without_scored_attempts(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await seed_education_domain(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    with pytest.raises(TeacherProductionError) as rejected:
        await TeacherProductionService(sqlite_session).compute_weakness_snapshot(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=WeaknessSnapshotRequest(
                teaching_class_id=DEMO_TEACHING_CLASS_ID,
                minimum_sample=10,
                knowledge_point_minimum_sample=5,
            ),
        )
    assert rejected.value.code == "INSUFFICIENT_ASSESSMENT_SAMPLE"
    assert "没有可评分的真实作答" in rejected.value.message


@pytest.mark.anyio
async def test_weakness_uses_scored_students_and_marks_small_knowledge_samples(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None
    service = TeacherProductionService(sqlite_session)

    before = await service.preflight_course_work(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        minimum_scored_students=10,
        knowledge_point_minimum_sample=5,
    )
    unscored_student_id = uuid4()
    sqlite_session.add(
        User(
            id=unscored_student_id,
            email=f"insight-unscored-{unscored_student_id}@securehub.local",
            display_name="待评分学习者",
            hashed_password=None,
            is_active=True,
            role="student",
        )
    )
    sqlite_session.add(
        CourseEnrollment(
            id=uuid4(),
            course_id=COURSE_WEBSEC_ID,
            student_id=unscored_student_id,
            teaching_class_id=DEMO_TEACHING_CLASS_ID,
            status="enrolled",
            enrolled_by=teacher.id,
        )
    )
    await sqlite_session.flush()

    threshold = before.scored_student_count + 1
    with pytest.raises(TeacherProductionError) as rejected:
        await service.compute_weakness_snapshot(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=WeaknessSnapshotRequest(
                teaching_class_id=DEMO_TEACHING_CLASS_ID,
                minimum_sample=threshold,
                knowledge_point_minimum_sample=5,
            ),
        )
    assert rejected.value.code == "INSUFFICIENT_ASSESSMENT_SAMPLE"
    assert str(before.scored_student_count) in rejected.value.message

    snapshot = await service.compute_weakness_snapshot(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=WeaknessSnapshotRequest(
            teaching_class_id=DEMO_TEACHING_CLASS_ID,
            minimum_sample=10,
            knowledge_point_minimum_sample=100,
        ),
    )
    assert snapshot.scored_student_count == before.scored_student_count
    assert snapshot.enrolled_student_count == before.enrolled_student_count + 1
    assert snapshot.knowledge_point_metrics
    assert all(point.attention_status == "insufficient_sample" for point in snapshot.knowledge_point_metrics)
    assert snapshot.weak_knowledge_points == []


@pytest.mark.anyio
async def test_recommendation_rejects_cross_course_evidence_pair(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None
    service = TeacherProductionService(sqlite_session)
    context = await service.get_form_context(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        purpose="teaching_recommendation",
    )
    assert context.weakness_snapshots and context.agent_evidence_pairs
    pair = context.agent_evidence_pairs[0]
    run = await sqlite_session.get(AgentRun, pair.agent_run_id)
    evidence = await sqlite_session.get(WorkflowEvidenceSnapshot, pair.evidence_snapshot_id)
    assert run is not None and evidence is not None

    foreign_course_id = str(uuid4())
    run.input_summary = {"course_id": foreign_course_id}
    run.output_summary = {"course_id": foreign_course_id}
    evidence.citation = {"course_id": foreign_course_id}
    evidence.source = {"course_id": foreign_course_id}
    await sqlite_session.flush()

    with pytest.raises(TeacherProductionError) as rejected:
        await service.create_teaching_recommendation(
            actor=teacher,
            course_id=COURSE_WEBSEC_ID,
            payload=_recommendation_payload(
                snapshot_id=context.weakness_snapshots[0].id,
                agent_run_id=pair.agent_run_id,
                evidence_snapshot_id=pair.evidence_snapshot_id,
            ),
        )
    assert rejected.value.code == "COURSE_ACCESS_DENIED"


@pytest.mark.anyio
async def test_adoption_creates_pending_action_without_publishing_course_content(sqlite_session) -> None:
    await seed_showcase_course(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    course = await sqlite_session.get(Course, COURSE_WEBSEC_ID)
    assert teacher is not None and course is not None
    original_title = course.title
    service = TeacherProductionService(sqlite_session)
    context = await service.get_form_context(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        purpose="teaching_recommendation",
    )
    assert context.weakness_snapshots and context.agent_evidence_pairs
    pair = context.agent_evidence_pairs[0]
    recommendation = await service.create_teaching_recommendation(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=_recommendation_payload(
            snapshot_id=context.weakness_snapshots[0].id,
            agent_run_id=pair.agent_run_id,
            evidence_snapshot_id=pair.evidence_snapshot_id,
        ),
    )

    adopted = await service.decide_teaching_recommendation(
        actor=teacher,
        recommendation_id=recommendation.id,
        payload=TeachingRecommendationDecisionRequest(
            decision="adopt",
            reason="教师确认先进入待审核复盘作业草稿，不自动发布任何课程内容。",
            action_type="review_assignment",
            action_title="待审核：输入边界与安全输出复盘作业",
            action_draft=(
                "面向目标教学班整理输入校验、参数化查询与输出编码的防御性复盘任务。"
                "教师将在审核后选择质量通过题目、设置教学班和截止时间；在审核完成前不得生成"
                "学生可见的作业、课程更新或成绩变化。"
            ),
        ),
    )
    assert adopted.status == "adopted"
    assert adopted.pending_teaching_action is not None
    assert adopted.pending_teaching_action.status == "pending_review"
    assert adopted.pending_teaching_action.action_type == "review_assignment"
    assert course.title == original_title

    audits = list(
        (
            await sqlite_session.execute(
                select(GovernanceAuditEvent).where(
                    GovernanceAuditEvent.object_id == adopted.pending_teaching_action.id
                )
            )
        ).scalars()
    )
    assert any(event.action == "teaching_action.create" for event in audits)
    assert all(event.metadata_["course_row_mutated"] is False for event in audits)
