# Status: real

"""Focused T3 evidence for durable teacher-production state machines."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.agent.agent_run import AgentRun
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.knowledge.document import Document
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.teaching.teacher_production import (
    AssessmentGradeDecision,
    CourseAssetGovernance,
    CourseSyllabusVersion,
    TeachingRecommendation,
)
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot, WorkflowRun
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import (
    DEMO_COURSE_TEACHER_ID,
    DEMO_TEACHING_CLASS_ID,
    run as seed_education_domain,
)
from app.schemas.syllabus import (
    CreateSyllabusVersionRequest,
    SyllabusExportRequest,
    SyllabusModuleContent,
    SyllabusReviewRequest,
    TypedSyllabusContent,
)
from app.schemas.teacher_production import (
    AssessmentCreateRequest,
    AssessmentVersionCreateRequest,
    AssessmentVersionItemRequest,
    AssignmentCreateRequest,
    AssetLifecycleRequest,
    BindCourseDocumentRequest,
    CreateTeachingRecommendationRequest,
    GradeOverrideRequest,
    QuizReviewRequest,
    RecordSubjectiveSuggestionRequest,
    SubmitAssessmentRequest,
    WeaknessSnapshotRequest,
)
from app.services.learning.quiz_quality_service import QuizQualityService
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


@pytest.mark.anyio
async def test_gap13_teacher_production_is_scoped_durable_and_reversible(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await seed_education_domain(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    student = await sqlite_session.get(User, DEMO_USER_ID)
    assert teacher is not None and student is not None

    bank = QuizQualityService(sqlite_session)
    await bank.validate_course(course_id=COURSE_WEBSEC_ID)
    publishable = await bank.list_publishable_items(course_id=COURSE_WEBSEC_ID)
    objective = next(item for item in publishable.items if item.type == "single_choice")
    subjective = next(item for item in publishable.items if item.type in {"short_answer", "code", "fill"})
    sqlite_session.add(
        QuizAttempt(
            id=uuid4(),
            quiz_item_id=objective.id,
            user_id=student.id,
            submitted_answer={"answer": "错误答案"},
            is_correct=False,
            score=0.0,
            feedback="真实作答记录",
            metadata_={"source": "gap13-focused"},
        )
    )
    await sqlite_session.flush()

    typed = TypedSyllabusContent(
        title="Web 安全基础教学大纲",
        summary="以 HTTP 安全边界和常见攻击防御为主线。",
        learning_outcomes=["能够识别常见 Web 攻击边界"],
        modules=[
            SyllabusModuleContent(
                module_id="m1",
                title="SQL 注入与输入验证",
                knowledge_node_ids=[objective.knowledge_node_id],
                learning_outcome="能够分析输入验证缺陷。",
                activities=["基于证据的案例分析"],
            )
        ],
        assessment_plan="作业与阶段性测验结合。",
        source_note="只使用已冻结 WebSec 知识资产。",
    )
    run = WorkflowRun(
        id=uuid4(),
        workflow_name="teacher-production-focused",
        user_id=teacher.id,
        status="succeeded",
        input_payload={},
        output_ref={},
        budget={},
        error={},
    )
    sqlite_session.add(run)
    await sqlite_session.flush()
    agent_run = AgentRun(
        id=uuid4(),
        workflow_name="teacher-production-focused",
        user_id=teacher.id,
        workflow_run_id=run.id,
        status="succeeded",
        input_summary={},
        output_summary={"suggested_score": 4.0, "typed_syllabus": typed.model_dump(mode="json")},
        # SQLite's JSON compatibility column serializes the runtime list as
        # opaque identifiers; production PostgreSQL retains UUID typing.
        evidence_chunk_ids=[str(objective.evidence[0].chunk_id)],  # type: ignore[list-item]
        token_usage={},
    )
    sqlite_session.add(agent_run)
    await sqlite_session.flush()
    evidence = WorkflowEvidenceSnapshot(
        id=uuid4(),
        workflow_run_id=run.id,
        agent_run_id=agent_run.id,
        chunk_id=str(objective.evidence[0].chunk_id),
        document_id=None,
        chunk_version="v1",
        content_digest="gap13-evidence-digest",
        excerpt="证据快照",
        citation={"chunk_id": str(objective.evidence[0].chunk_id)},
        source={},
        rights={},
    )
    sqlite_session.add(evidence)
    await sqlite_session.flush()

    service = TeacherProductionService(sqlite_session)

    # FG-02: the asset remains in unified documents and soft lifecycle is durable.
    document = (await sqlite_session.execute(select(Document).where(Document.domain == "course_websec"))).scalars().first()
    assert document is not None
    asset = await service.bind_document(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=BindCourseDocumentRequest(document_id=document.id, reason="纳入教师教材库"),
    )
    assert asset.state == "ready"
    withdrawn_asset = await service.withdraw_asset(
        actor=teacher,
        asset_id=asset.id,
        payload=AssetLifecycleRequest(reason="暂时下线"),
    )
    assert withdrawn_asset.state == "withdrawn"
    restored_asset = await service.restore_asset(
        actor=teacher,
        asset_id=asset.id,
        payload=AssetLifecycleRequest(reason="恢复已核验版本"),
    )
    assert restored_asset.state == "ready"

    # F1: a human decision and an evidence-bound recommendation are separate
    # from T2's deterministic validator and never mutate the course itself.
    review = await service.review_quiz(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        quiz_item_id=objective.id,
        payload=QuizReviewRequest(decision="publish", reason="教师确认后发布"),
    )
    assert review.after_status == "curated"
    weakness = await service.compute_weakness_snapshot(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=WeaknessSnapshotRequest(minimum_sample=1),
    )
    assert weakness.sample_size == 1
    weakness_rows = await service.list_weakness_snapshots(actor=teacher, course_id=COURSE_WEBSEC_ID)
    assert [row.id for row in weakness_rows.items] == [weakness.id]
    recommendation = await service.create_teaching_recommendation(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=CreateTeachingRecommendationRequest(
            source_snapshot_id=weakness.id,
            evidence_snapshot_id=evidence.id,
            agent_run_id=agent_run.id,
            title="增加输入验证复盘",
            actions=["在下一次作业前安排证据驱动复盘"],
            rationale="真实作答样本显示此知识点分数偏低。",
        ),
    )
    assert recommendation.status == "pending"
    recommendation_rows = await service.list_teaching_recommendations(
        actor=teacher, course_id=COURSE_WEBSEC_ID
    )
    assert [row.id for row in recommendation_rows.items] == [recommendation.id]

    # FG-05: version snapshot, class target, student submission, deterministic
    # objective score, Runtime-linked suggestion, manual override, publish.
    assessment = await service.create_assessment(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=AssessmentCreateRequest(kind="assignment", logical_key="gap13-assignment-001"),
    )
    version = await service.create_assessment_version(
        actor=teacher,
        assessment_id=assessment.id,
        payload=AssessmentVersionCreateRequest(
            title="输入安全作业",
            items=[
                AssessmentVersionItemRequest(
                    quiz_item_id=objective.id, position=1, points=5, grading_mode="objective"
                ),
                AssessmentVersionItemRequest(
                    quiz_item_id=subjective.id, position=2, points=5, grading_mode="subjective"
                ),
            ],
        ),
    )
    assignment = await service.assign_assessment(
        actor=teacher,
        version_id=version.id,
        payload=AssignmentCreateRequest(
            target_type="class",
            teaching_class_id=DEMO_TEACHING_CLASS_ID,
            due_at=datetime.now(UTC) + timedelta(days=1),
            reason="布置课堂作业",
        ),
    )
    assignment_rows = await service.list_course_assignments(actor=teacher, course_id=COURSE_WEBSEC_ID)
    assert [row.id for row in assignment_rows.items] == [assignment.id]
    submission = await service.submit_assessment(
        actor=student,
        assignment_id=assignment.id,
        payload=SubmitAssessmentRequest(
            answers={str(objective.id): objective.answer, str(subjective.id): "主观作答"}
        ),
    )
    submission_rows = await service.list_assignment_submissions(actor=teacher, assignment_id=assignment.id)
    assert [row.id for row in submission_rows.items] == [submission.id]
    assert submission_rows.items[0].student_display_name == student.display_name
    scored = await service.score_objective_submission(actor=teacher, submission_id=submission.id)
    assert scored.objective_score == 5
    suggested = await service.record_subjective_suggestion(
        actor=teacher,
        submission_id=submission.id,
        payload=RecordSubjectiveSuggestionRequest(agent_run_id=agent_run.id, evidence_snapshot_id=evidence.id),
    )
    assert suggested.ai_suggested_score == 4
    reviewed_grade = await service.override_grade(
        actor=teacher,
        submission_id=submission.id,
        payload=GradeOverrideRequest(final_score=9, reason="教师复核主观回答后调整"),
    )
    assert reviewed_grade.status == "teacher_reviewed"
    published_grade = await service.publish_grade(actor=teacher, submission_id=submission.id)
    assert published_grade.status == "published"
    student_result = await service.get_student_published_result(actor=student, assignment_id=assignment.id)
    assert student_result.final_score == 9
    withdrawn_grade = await service.withdraw_grade(
        actor=teacher, submission_id=submission.id, reason="更正后重新发布"
    )
    assert withdrawn_grade.status == "withdrawn"
    with pytest.raises(TeacherProductionError) as unpublished:
        await service.get_student_published_result(actor=student, assignment_id=assignment.id)
    assert unpublished.value.code == "GRADE_NOT_PUBLISHED"

    # FG-06: a typed state is reviewed/published/exported without changing
    # course fields; no ordinary generated document is accepted as a syllabus.
    syllabus = await service.create_syllabus_version(
        actor=teacher,
        course_id=COURSE_WEBSEC_ID,
        payload=CreateSyllabusVersionRequest(typed_content=typed, reason="教师编辑 typed syllabus"),
    )
    approved = await service.review_syllabus_version(
        actor=teacher,
        version_id=syllabus.id,
        payload=SyllabusReviewRequest(decision="approve", reason="教师审核通过"),
    )
    assert approved.state == "published"
    syllabus_rows = await service.list_syllabus_versions(actor=teacher, course_id=COURSE_WEBSEC_ID)
    assert [row.id for row in syllabus_rows.items] == [approved.id]
    export = await service.export_syllabus_version(
        actor=teacher,
        version_id=approved.id,
        payload=SyllabusExportRequest(format="markdown"),
    )
    assert export.generated_resource_id is not None
    assert "# Web 安全基础教学大纲" in str(export.content)

    rows = (await sqlite_session.execute(select(GovernanceAuditEvent))).scalars().all()
    assert any(row.action == "assessment_grade.override" for row in rows)
    assert any(row.action == "syllabus.review" for row in rows)
    assert await sqlite_session.scalar(select(CourseAssetGovernance.id)) is not None
    assert await sqlite_session.scalar(select(TeachingRecommendation.id)) == recommendation.id
    assert await sqlite_session.scalar(select(AssessmentGradeDecision.id)) == published_grade.id
    assert await sqlite_session.scalar(select(CourseSyllabusVersion.id)) == approved.id
