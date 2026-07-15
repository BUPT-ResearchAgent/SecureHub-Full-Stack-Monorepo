# Status: real

"""Idempotent minimal teaching-class seed for the ready Web security course.

Run after ``seed_demo_user`` and ``seed_course_websec``:
``python -m app.db.seeds.seed_education_domain``.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import (
    CourseEnrollment,
    CourseTeacherAssignment,
    GovernanceAuditEvent,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
    TeachingClassTeacher,
)
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID, stable_id
from app.db.session import get_sessionmaker

DEMO_COURSE_TEACHER_ID = stable_id("user:demo-course-teacher")
DEMO_TEACHING_CLASS_ID = stable_id("education:teaching-class:websec:2026-a")
DEMO_STUDENT_GROUP_ID = stable_id("education:student-group:websec:2026-a:lab-a")
DEMO_COURSE_TEACHER_ASSIGNMENT_ID = stable_id(
    "education:course-teacher-assignment:websec:demo-course-teacher"
)
DEMO_CLASS_TEACHER_ASSIGNMENT_ID = stable_id(
    "education:teaching-class-teacher:websec:2026-a:demo-course-teacher"
)
DEMO_ENROLLMENT_ID = stable_id("education:course-enrollment:websec:demo-student")
DEMO_GROUP_MEMBER_ID = stable_id("education:student-group-member:websec:lab-a:demo-student")
_SEED_AT = datetime(2026, 7, 15, tzinfo=UTC)


async def _ensure(
    session: AsyncSession, model: type[object], row_id: UUID, **values: object
) -> tuple[object, bool]:
    row = await session.get(model, row_id)
    if row is not None:
        return row, False
    row = model(id=row_id, **values)  # type: ignore[call-arg]
    session.add(row)
    await session.flush()
    return row, True


async def _seed(session: AsyncSession) -> dict[str, int]:
    counts = {
        "course_teacher_assignments": 0,
        "teaching_classes": 0,
        "teaching_class_teachers": 0,
        "course_enrollments": 0,
        "student_groups": 0,
        "student_group_members": 0,
        "governance_audit_events": 0,
    }
    _, created = await _ensure(
        session,
        CourseTeacherAssignment,
        DEMO_COURSE_TEACHER_ASSIGNMENT_ID,
        course_id=COURSE_WEBSEC_ID,
        teacher_id=DEMO_COURSE_TEACHER_ID,
        assignment_role="owner",
        status="active",
        assigned_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["course_teacher_assignments"] += int(created)
    _, created = await _ensure(
        session,
        TeachingClass,
        DEMO_TEACHING_CLASS_ID,
        course_id=COURSE_WEBSEC_ID,
        code="WEBSEC-2026-A",
        name="Web 安全基础 · 2026 春 A 班",
        status="active",
        created_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["teaching_classes"] += int(created)
    _, created = await _ensure(
        session,
        TeachingClassTeacher,
        DEMO_CLASS_TEACHER_ASSIGNMENT_ID,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        teacher_id=DEMO_COURSE_TEACHER_ID,
        role="owner",
        status="active",
        assigned_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["teaching_class_teachers"] += int(created)
    _, created = await _ensure(
        session,
        CourseEnrollment,
        DEMO_ENROLLMENT_ID,
        course_id=COURSE_WEBSEC_ID,
        student_id=DEMO_USER_ID,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        status="enrolled",
        enrolled_by=DEMO_COURSE_TEACHER_ID,
        enrolled_at=_SEED_AT,
    )
    counts["course_enrollments"] += int(created)
    _, created = await _ensure(
        session,
        StudentGroup,
        DEMO_STUDENT_GROUP_ID,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        name="实验 A 组",
        status="active",
        created_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["student_groups"] += int(created)
    _, created = await _ensure(
        session,
        StudentGroupMember,
        DEMO_GROUP_MEMBER_ID,
        group_id=DEMO_STUDENT_GROUP_ID,
        student_id=DEMO_USER_ID,
        status="active",
        changed_by=DEMO_COURSE_TEACHER_ID,
        changed_at=_SEED_AT,
    )
    counts["student_group_members"] += int(created)

    audit_rows = (
        (
            "education:audit:course-teacher-assignment:websec",
            "course_teacher_assignment.seed",
            "course_teacher_assignment",
            DEMO_COURSE_TEACHER_ASSIGNMENT_ID,
        ),
        (
            "education:audit:course-enrollment:websec-demo-student",
            "course_enrollment.seed",
            "course_enrollment",
            DEMO_ENROLLMENT_ID,
        ),
        (
            "education:audit:student-group-member:websec-lab-a-demo-student",
            "student_group.member_seed",
            "student_group_member",
            DEMO_GROUP_MEMBER_ID,
        ),
    )
    for stable_name, action, object_type, object_id in audit_rows:
        _, created = await _ensure(
            session,
            GovernanceAuditEvent,
            stable_id(stable_name),
            actor_user_id=DEMO_COURSE_TEACHER_ID,
            action=action,
            object_type=object_type,
            object_id=object_id,
            reason="idempotent demo education seed",
            result_status="seeded",
            request_id=None,
            metadata_={"seed": "seed_education_domain", "course_id": str(COURSE_WEBSEC_ID)},
            created_at=_SEED_AT,
        )
        counts["governance_audit_events"] += int(created)
    return counts


async def run(session: AsyncSession | None = None) -> dict[str, int]:
    if session is not None:
        return await _seed(session)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as own_session:
        stats = await _seed(own_session)
        await own_session.commit()
    return stats


if __name__ == "__main__":  # pragma: no cover
    print(asyncio.run(run()))
