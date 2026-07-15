# Status: real

"""Focused T2 evidence for durable WEBSEC-101 quiz quality and consumption."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models.identity.user import User
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizQualityReport
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID, run as seed_education_domain
from app.services.learning.quiz_quality_service import QuizQualityError, QuizQualityService


@pytest.mark.anyio
async def test_gap13_websec_quiz_quality_is_reproducible_scoped_and_publishable(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    first_seed = await seed_course_websec(sqlite_session)
    await sqlite_session.commit()
    second_seed = await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    assert first_seed["quiz_items"] == 21
    assert second_seed["quiz_items"] == 0

    service = QuizQualityService(sqlite_session)
    first_run = await service.validate_course(course_id=COURSE_WEBSEC_ID)
    await sqlite_session.flush()
    report_count_after_first = await sqlite_session.scalar(select(func.count(QuizQualityReport.id)))
    second_run = await service.validate_course(course_id=COURSE_WEBSEC_ID)
    await sqlite_session.flush()
    report_count_after_second = await sqlite_session.scalar(select(func.count(QuizQualityReport.id)))

    assert first_run.result == second_run.result == "passed"
    assert first_run.input_fingerprint == second_run.input_fingerprint
    assert first_run.coverage["required_knowledge_point_count"] == 17
    assert first_run.coverage["covered_knowledge_point_count"] == 17
    assert first_run.coverage["missing_knowledge_node_ids"] == []
    assert len(first_run.type_distribution) >= 3
    assert report_count_after_first == report_count_after_second == 21

    published = await service.list_publishable_items(course_id=COURSE_WEBSEC_ID)
    assert len(published.items) == 21
    assert {item.knowledge_node_id for item in published.items}
    assert len({item.knowledge_node_id for item in published.items}) == 17
    assert all(item.review_status == "curated" for item in published.items)
    assert all(item.quality and item.quality.result == "passed" for item in published.items)
    assert all(item.evidence for item in published.items)
    assert {item.review_status for item in published.items} == {"curated"}
    reports = (await sqlite_session.execute(select(QuizQualityReport))).scalars().all()
    assert all(report.reviewed_by is None for report in reports)

    await seed_education_domain(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None
    teacher_bank = await service.list_teacher_bank(actor=teacher)
    assert teacher_bank.coverage["all_knowledge_points_covered"] is True
    assert len(teacher_bank.items) == 21

    invalid = QuizItem(
        id=uuid4(),
        kp_id=published.items[0].knowledge_node_id,
        canonical_key="websec:v1:invalid:no-evidence",
        content_version=1,
        type="single_choice",
        question="缺少证据的测试题目是什么？",
        options=["选项 A", "选项 B"],
        answer="选项 A",
        explanation="这是用于验证确定性拒绝的受控失败样本。",
        difficulty=1,
        review_status="curated",
        source_status="seeded",
    )
    sqlite_session.add(invalid)
    await sqlite_session.flush()
    failed_run = await service.validate_course(course_id=COURSE_WEBSEC_ID)
    assert failed_run.result == "failed"
    assert any(
        sample.canonical_key == invalid.canonical_key
        and "QUESTION_EVIDENCE_MISSING" in sample.failure_codes
        for sample in failed_run.failure_samples
    )
    with pytest.raises(QuizQualityError) as rejected:
        await service.list_publishable_items(
            course_id=COURSE_WEBSEC_ID,
            canonical_key=invalid.canonical_key,
        )
    assert rejected.value.code == "QUESTION_STATUS_NOT_PUBLISHABLE"
