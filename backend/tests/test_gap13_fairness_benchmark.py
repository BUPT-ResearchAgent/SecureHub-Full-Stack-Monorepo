# Status: real

"""Focused T6 evidence: consent, aggregate fairness, appeals, benchmarks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.fairness.fairness import FairnessGroupAssignment, FairnessMetricRun
from app.db.models.governance.governance import RoleDefinition, UserRoleGrant
from app.db.models.identity.user import User
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentSubmission,
    AssessmentVersion,
)
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID, run as seed_education_domain
from app.repositories.governance.governance import GovernanceRepository
from app.schemas.benchmark import BenchmarkRunRequest
from app.schemas.fairness import (
    FairnessAppealCreateRequest,
    FairnessAppealResolveRequest,
    FairnessConsentRequest,
    FairnessGroupAssignmentRequest,
    FairnessMetricRunRequest,
    FairnessPolicyCreateRequest,
    FairnessReviewRequest,
)
from app.services.benchmark.benchmark_service import BenchmarkService
from app.services.fairness.fairness_service import FairnessDomainError, FairnessService
from app.services.governance.governance_service import GovernanceService


@pytest.mark.anyio
async def test_gap13_fairness_and_benchmarks_are_consent_gated_reproducible_and_nonpunitive(
    sqlite_session,
) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await seed_education_domain(sqlite_session)
    now = datetime.now(UTC)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    # The existing T4 RBAC authority, not a browser role, unlocks governance.
    await GovernanceService(sqlite_session).ensure_default_definitions()
    role = await GovernanceRepository(sqlite_session).get_active_role_by_code("administrator")
    assert role is not None
    sqlite_session.add(
        UserRoleGrant(
            id=uuid4(),
            user_id=teacher.id,
            role_id=role.id,
            granted_by=teacher.id,
            granted_at=now,
            status="active",
            reason="T6 focused administrator evidence",
        )
    )

    students = [
        User(
            id=uuid4(),
            email=f"fairness-student-{index}@example.test",
            display_name=f"公平测试学生{index}",
            hashed_password=None,
            role="student",
            is_active=True,
        )
        for index in range(1, 5)
    ]
    sqlite_session.add_all(students)
    await sqlite_session.flush()

    # Published final grades are the only score source.  No grade is mutated
    # by any later fairness or appeal operation.
    assessment = Assessment(
        id=uuid4(),
        course_id=COURSE_WEBSEC_ID,
        owner_teacher_id=teacher.id,
        kind="assignment",
        logical_key="gap13-fairness-focused",
        status="published",
    )
    sqlite_session.add(assessment)
    await sqlite_session.flush()
    version = AssessmentVersion(
        id=uuid4(),
        assessment_id=assessment.id,
        version_no=1,
        title="公平监控测试作业",
        instructions="只用于测试已发布成绩的聚合读取。",
        state="published",
        created_by=teacher.id,
        frozen_at=now,
    )
    sqlite_session.add(version)
    await sqlite_session.flush()
    scores = [82.0, 80.0, 42.0, 40.0]
    grade_ids = []
    for student, score in zip(students, scores, strict=True):
        assignment = AssessmentAssignment(
            id=uuid4(),
            assessment_version_id=version.id,
            target_type="student",
            teaching_class_id=None,
            group_id=None,
            student_id=student.id,
            due_at=now + timedelta(days=1),
            allow_late=False,
            status="active",
            assigned_by=teacher.id,
            idempotency_key=None,
        )
        sqlite_session.add(assignment)
        await sqlite_session.flush()
        submission = AssessmentSubmission(
            id=uuid4(),
            assignment_id=assignment.id,
            student_id=student.id,
            answers={},
            submitted_at=now,
            status="submitted",
        )
        sqlite_session.add(submission)
        await sqlite_session.flush()
        grade = AssessmentGradeDecision(
            id=uuid4(),
            submission_id=submission.id,
            objective_score=None,
            ai_suggested_score=None,
            ai_agent_run_id=None,
            ai_evidence_snapshot_id=None,
            ai_suggestion_status="not_requested",
            final_score=score,
            status="published",
            graded_by=teacher.id,
            override_reason="教师已发布最终成绩",
            published_at=now,
            withdrawn_at=None,
        )
        sqlite_session.add(grade)
        grade_ids.append(grade.id)
    await sqlite_session.flush()

    fairness = FairnessService(sqlite_session)
    with pytest.raises(FairnessDomainError) as sensitive_policy:
        await fairness.create_policy(
            actor=teacher,
            payload=FairnessPolicyCreateRequest(
                code="forbidden-sensitive-key",
                version_no=1,
                purpose="应拒绝任何未获 RFC 许可的敏感字段。",
                allowed_group_keys=["gender"],
                minimum_sample=2,
                pass_score=60,
                retention_days=30,
            ),
        )
    assert sensitive_policy.value.code == "FAIRNESS_ATTRIBUTE_NOT_ALLOWED"

    policy = await fairness.create_policy(
        actor=teacher,
        payload=FairnessPolicyCreateRequest(
            code="fairness-focused",
            version_no=1,
            purpose="只对明确同意的非敏感 cohort 聚合评估公平性。",
            allowed_group_keys=["cohort"],
            minimum_sample=2,
            pass_score=60,
            retention_days=30,
            thresholds={"max_mean_score_gap": 5.0, "max_pass_rate_gap": 0.1},
        ),
    )

    # A malicious/incomplete persistence state cannot bypass consent: it is
    # rejected and retains only an aggregate audit run without cells.
    for index, student in enumerate(students):
        sqlite_session.add(
            FairnessGroupAssignment(
                id=uuid4(),
                user_id=student.id,
                policy_id=policy.id,
                group_key="cohort",
                minimal_group_value="A" if index < 2 else "B",
                expires_at=now + timedelta(days=14),
                assigned_by=teacher.id,
            )
        )
    await sqlite_session.flush()
    with pytest.raises(FairnessDomainError) as missing_consent:
        await fairness.run_metrics(
            actor=teacher,
            policy_id=policy.id,
            payload=FairnessMetricRunRequest(assessment_ids=[assessment.id]),
        )
    assert missing_consent.value.code == "FAIRNESS_CONSENT_REQUIRED"
    rejected_run = await sqlite_session.scalar(
        select(FairnessMetricRun).where(FairnessMetricRun.rejection_code == "FAIRNESS_CONSENT_REQUIRED")
    )
    assert rejected_run is not None and rejected_run.status == "rejected"

    # Consent and group assignment are each durable and audited.  The group
    # values are simple non-sensitive cohort codes, never protected traits.
    for index, student in enumerate(students):
        await fairness.grant_consent(
            actor=student,
            payload=FairnessConsentRequest(
                policy_id=policy.id,
                expires_at=now + timedelta(days=14),
            ),
        )
        await fairness.assign_group(
            actor=teacher,
            policy_id=policy.id,
            payload=FairnessGroupAssignmentRequest(
                user_id=student.id,
                group_key="cohort",
                minimal_group_value="A" if index < 2 else "B",
                expires_at=now + timedelta(days=14),
                reason="仅保留最小 cohort 码用于聚合评估。",
            ),
        )

    # Insufficient sample returns the explicit state and never creates cells.
    insufficient_policy = await fairness.create_policy(
        actor=teacher,
        payload=FairnessPolicyCreateRequest(
            code="fairness-insufficient",
            version_no=1,
            purpose="验证样本不足时不展示公平结论。",
            allowed_group_keys=["cohort"],
            minimum_sample=3,
            pass_score=60,
            retention_days=30,
        ),
    )
    for index, student in enumerate(students):
        await fairness.grant_consent(
            actor=student,
            payload=FairnessConsentRequest(
                policy_id=insufficient_policy.id,
                expires_at=now + timedelta(days=14),
            ),
        )
        await fairness.assign_group(
            actor=teacher,
            policy_id=insufficient_policy.id,
            payload=FairnessGroupAssignmentRequest(
                user_id=student.id,
                group_key="cohort",
                minimal_group_value="A" if index < 2 else "B",
                expires_at=now + timedelta(days=14),
                reason="样本门槛拒绝验证。",
            ),
        )
    insufficient = await fairness.run_metrics(
        actor=teacher,
        policy_id=insufficient_policy.id,
        payload=FairnessMetricRunRequest(assessment_ids=[assessment.id]),
    )
    assert insufficient.status == "insufficient_sample"
    assert insufficient.rejection_code == "INSUFFICIENT_SAMPLE"
    assert insufficient.cells == []

    # Same frozen grades, consent, policy and formula yield the same metric
    # fingerprint and same aggregate cells on repeated execution.
    first = await fairness.run_metrics(
        actor=teacher,
        policy_id=policy.id,
        payload=FairnessMetricRunRequest(assessment_ids=[assessment.id]),
    )
    second = await fairness.run_metrics(
        actor=teacher,
        policy_id=policy.id,
        payload=FairnessMetricRunRequest(assessment_ids=[assessment.id]),
    )
    assert first.status == second.status == "completed"
    assert first.dataset_fingerprint == second.dataset_fingerprint
    assert [(cell.group_value, cell.sample_size, cell.mean_score, cell.pass_rate) for cell in first.cells] == [
        (cell.group_value, cell.sample_size, cell.mean_score, cell.pass_rate) for cell in second.cells
    ]
    assert all(cell.sample_size == 2 for cell in first.cells)
    assert first.alerts and all(alert.status == "open" for alert in first.alerts)
    review = await fairness.review_alert(
        actor=teacher,
        alert_id=first.alerts[0].id,
        payload=FairnessReviewRequest(status="under_review", reason="需要人工检查评分规则及样本限制。"),
    )
    assert review.status == "under_review"

    # An appeal is ownership-checked and ends in a human explanation.  It
    # cannot rewrite the published grade by itself.
    appeal = await fairness.create_appeal(
        actor=students[0],
        payload=FairnessAppealCreateRequest(
            grade_decision_id=grade_ids[0], reason="请人工说明该成绩的评分依据。"
        ),
    )
    resolved = await fairness.resolve_appeal(
        actor=teacher,
        appeal_id=appeal.id,
        payload=FairnessAppealResolveRequest(status="resolved", response_note="已完成评分依据说明。"),
    )
    assert resolved.status == "resolved"
    unchanged_grade = await sqlite_session.get(AssessmentGradeDecision, grade_ids[0])
    assert unchanged_grade is not None and unchanged_grade.status == "published" and unchanged_grade.final_score == 82

    # VG-01: all three frozen manifests run deterministically; the fixtures
    # label themselves as non-user evaluation assets rather than outcomes.
    benchmarks = BenchmarkService(sqlite_session)
    await benchmarks.bootstrap_default_datasets()
    datasets = await benchmarks.list_datasets(actor=teacher)
    assert {item.kind for item in datasets.items} == {"content_relevance", "api_misuse", "fairness"}
    benchmark_outputs = [
        await benchmarks.run_dataset(actor=teacher, dataset_id=dataset.id, payload=BenchmarkRunRequest())
        for dataset in datasets.items
    ]
    assert {run.dataset_kind for run in benchmark_outputs} == {"content_relevance", "api_misuse", "fairness"}
    assert all(run.status == "completed" and run.summary["group_counts"] for run in benchmark_outputs)
    first_dataset = datasets.items[0]
    benchmark_one = benchmark_outputs[0]
    benchmark_two = await benchmarks.run_dataset(
        actor=teacher, dataset_id=first_dataset.id, payload=BenchmarkRunRequest()
    )
    assert benchmark_one.summary["confusion_matrix"] == benchmark_two.summary["confusion_matrix"]
    assert benchmark_one.config_fingerprint == benchmark_two.config_fingerprint
    assert benchmark_one.summary["user_effect_metric"] is False
    assert benchmark_one.summary["failure_samples"]

    audit_actions = {row.action for row in (await sqlite_session.execute(select(GovernanceAuditEvent))).scalars()}
    assert {"fairness_consent.grant", "fairness_metric.run", "fairness_alert.review", "fairness_appeal.review", "benchmark.run"} <= audit_actions
