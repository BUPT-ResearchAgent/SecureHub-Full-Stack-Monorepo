# Status: real

"""Focused T1 evidence for durable education relationships and authorization."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.education.education_domain import (
    CourseEnrollment,
    GovernanceAuditEvent,
)
from app.db.models.identity.user import User
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import (
    DEMO_COURSE_TEACHER_ID,
    DEMO_STUDENT_GROUP_ID,
    DEMO_TEACHING_CLASS_ID,
    run as seed_education_domain,
)
from app.schemas.education import ChangeStudentGroupMemberRequest
from app.services.education.education_service import EducationDomainError, EducationService


@pytest.mark.anyio
async def test_gap13_education_domain_is_idempotent_scoped_and_audited(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    first_seed = await seed_education_domain(sqlite_session)
    await sqlite_session.commit()
    second_seed = await seed_education_domain(sqlite_session)
    await sqlite_session.commit()

    assert first_seed["teaching_classes"] == 1
    assert first_seed["course_enrollments"] == 1
    assert first_seed["student_group_members"] == 1
    assert all(count == 0 for count in second_seed.values())

    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    student = await sqlite_session.get(User, DEMO_USER_ID)
    assert teacher is not None and student is not None
    service = EducationService(sqlite_session)

    classes = await service.list_classes(actor=teacher)
    assert [(row.id, row.course_id, row.student_count) for row in classes.items] == [
        (DEMO_TEACHING_CLASS_ID, COURSE_WEBSEC_ID, 1)
    ]
    roster = await service.get_roster(actor=teacher, class_id=DEMO_TEACHING_CLASS_ID)
    assert [(row.id, row.display_name) for row in roster.students] == [(DEMO_USER_ID, "陈同学")]
    groups = await service.get_groups(actor=teacher, class_id=DEMO_TEACHING_CLASS_ID)
    assert [(row.id, row.name, [member.student_id for member in row.members]) for row in groups.items] == [
        (DEMO_STUDENT_GROUP_ID, "实验 A 组", [DEMO_USER_ID])
    ]

    with pytest.raises(EducationDomainError) as student_denied:
        await service.get_roster(actor=student, class_id=DEMO_TEACHING_CLASS_ID)
    assert student_denied.value.code == "TEACHER_ROLE_REQUIRED"

    outsider = User(
        id=uuid4(),
        email="outside-course-teacher@example.test",
        display_name="越权教师",
        hashed_password=None,
        is_active=True,
        role="course_teacher",
    )
    sqlite_session.add(outsider)
    await sqlite_session.flush()
    with pytest.raises(EducationDomainError) as scope_denied:
        await service.get_roster(actor=outsider, class_id=DEMO_TEACHING_CLASS_ID)
    assert scope_denied.value.code == "COURSE_ACCESS_DENIED"

    new_student = User(
        id=uuid4(),
        email="enrolled-student@example.test",
        display_name="李同学",
        hashed_password=None,
        is_active=True,
        role="student",
    )
    sqlite_session.add(new_student)
    sqlite_session.add(
        CourseEnrollment(
            id=uuid4(),
            course_id=COURSE_WEBSEC_ID,
            student_id=new_student.id,
            teaching_class_id=DEMO_TEACHING_CLASS_ID,
            status="enrolled",
            enrolled_by=teacher.id,
        )
    )
    await sqlite_session.flush()
    payload = ChangeStudentGroupMemberRequest(student_id=new_student.id, action="add", reason="课堂分组")
    changed = await service.change_group_member(
        actor=teacher,
        class_id=DEMO_TEACHING_CLASS_ID,
        group_id=DEMO_STUDENT_GROUP_ID,
        payload=payload,
        idempotency_key="gap13-member-add-001",
    )
    replay = await service.change_group_member(
        actor=teacher,
        class_id=DEMO_TEACHING_CLASS_ID,
        group_id=DEMO_STUDENT_GROUP_ID,
        payload=payload,
        idempotency_key="gap13-member-add-001",
    )
    assert changed.student_id == replay.student_id == new_student.id
    assert changed.status == replay.status == "active"

    with pytest.raises(EducationDomainError) as idempotency_conflict:
        await service.change_group_member(
            actor=teacher,
            class_id=DEMO_TEACHING_CLASS_ID,
            group_id=DEMO_STUDENT_GROUP_ID,
            payload=ChangeStudentGroupMemberRequest(student_id=new_student.id, action="remove"),
            idempotency_key="gap13-member-add-001",
        )
    assert idempotency_conflict.value.code == "IDEMPOTENCY_CONFLICT"

    events = (
        await sqlite_session.execute(
            select(GovernanceAuditEvent).where(
                GovernanceAuditEvent.request_id == "gap13-member-add-001"
            )
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].actor_user_id == teacher.id
    assert events[0].object_type == "student_group_member"
    assert events[0].result_status == "succeeded"
