# Status: real

"""SQL-only persistence adapter for the education relationship domain."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select

from app.db.models.education.education_domain import (
    CourseEnrollment,
    CourseTeacherAssignment,
    GovernanceAuditEvent,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
    TeachingClassTeacher,
)
from app.db.models.identity.user import User
from app.repositories.base import BaseRepository


class EducationRepository(BaseRepository):
    async def get_course_teacher_assignment(
        self, *, course_id: UUID, teacher_id: UUID
    ) -> CourseTeacherAssignment | None:
        result = await self.session.execute(
            select(CourseTeacherAssignment).where(
                CourseTeacherAssignment.course_id == course_id,
                CourseTeacherAssignment.teacher_id == teacher_id,
                CourseTeacherAssignment.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def list_classes_for_teacher(
        self, *, teacher_id: UUID, course_id: UUID | None = None
    ) -> Sequence[TeachingClass]:
        statement = (
            select(TeachingClass)
            .join(
                TeachingClassTeacher,
                TeachingClassTeacher.teaching_class_id == TeachingClass.id,
            )
            .join(
                CourseTeacherAssignment,
                and_(
                    CourseTeacherAssignment.course_id == TeachingClass.course_id,
                    CourseTeacherAssignment.teacher_id == TeachingClassTeacher.teacher_id,
                ),
            )
            .where(
                TeachingClassTeacher.teacher_id == teacher_id,
                TeachingClassTeacher.status == "active",
                CourseTeacherAssignment.status == "active",
                TeachingClass.status == "active",
            )
            .order_by(TeachingClass.code, TeachingClass.name)
        )
        if course_id is not None:
            statement = statement.where(TeachingClass.course_id == course_id)
        result = await self.session.execute(statement)
        return result.scalars().unique().all()

    async def get_class(self, class_id: UUID) -> TeachingClass | None:
        return await self.session.get(TeachingClass, class_id)

    async def get_teacher_class(
        self, *, teacher_id: UUID, class_id: UUID
    ) -> TeachingClass | None:
        statement = (
            select(TeachingClass)
            .join(
                TeachingClassTeacher,
                TeachingClassTeacher.teaching_class_id == TeachingClass.id,
            )
            .join(
                CourseTeacherAssignment,
                and_(
                    CourseTeacherAssignment.course_id == TeachingClass.course_id,
                    CourseTeacherAssignment.teacher_id == TeachingClassTeacher.teacher_id,
                ),
            )
            .where(
                TeachingClass.id == class_id,
                TeachingClass.status == "active",
                TeachingClassTeacher.teacher_id == teacher_id,
                TeachingClassTeacher.status == "active",
                CourseTeacherAssignment.status == "active",
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def enrollment_counts(self, class_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not class_ids:
            return {}
        result = await self.session.execute(
            select(CourseEnrollment.teaching_class_id, func.count(CourseEnrollment.id))
            .where(
                CourseEnrollment.teaching_class_id.in_(class_ids),
                CourseEnrollment.status == "enrolled",
            )
            .group_by(CourseEnrollment.teaching_class_id)
        )
        return {class_id: int(count) for class_id, count in result.all() if class_id is not None}

    async def list_roster(self, class_id: UUID) -> Sequence[tuple[CourseEnrollment, User]]:
        result = await self.session.execute(
            select(CourseEnrollment, User)
            .join(User, User.id == CourseEnrollment.student_id)
            .where(
                CourseEnrollment.teaching_class_id == class_id,
                CourseEnrollment.status == "enrolled",
            )
            .order_by(User.display_name, User.email)
        )
        return result.all()

    async def list_groups(self, class_id: UUID) -> Sequence[StudentGroup]:
        result = await self.session.execute(
            select(StudentGroup)
            .where(StudentGroup.teaching_class_id == class_id)
            .order_by(StudentGroup.status.desc(), StudentGroup.name)
        )
        return result.scalars().all()

    async def get_group(self, group_id: UUID) -> StudentGroup | None:
        return await self.session.get(StudentGroup, group_id)

    async def get_group_for_class(
        self, *, group_id: UUID, class_id: UUID
    ) -> StudentGroup | None:
        result = await self.session.execute(
            select(StudentGroup).where(
                StudentGroup.id == group_id,
                StudentGroup.teaching_class_id == class_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_group_by_name(self, *, class_id: UUID, name: str) -> StudentGroup | None:
        result = await self.session.execute(
            select(StudentGroup).where(
                StudentGroup.teaching_class_id == class_id,
                StudentGroup.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_group_members(
        self, group_ids: Sequence[UUID]
    ) -> Sequence[tuple[StudentGroupMember, User]]:
        if not group_ids:
            return []
        result = await self.session.execute(
            select(StudentGroupMember, User)
            .join(User, User.id == StudentGroupMember.student_id)
            .where(StudentGroupMember.group_id.in_(group_ids))
            .order_by(User.display_name, User.email)
        )
        return result.all()

    async def get_active_enrollment(
        self, *, class_id: UUID, student_id: UUID
    ) -> CourseEnrollment | None:
        result = await self.session.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.teaching_class_id == class_id,
                CourseEnrollment.student_id == student_id,
                CourseEnrollment.status == "enrolled",
            )
        )
        return result.scalar_one_or_none()

    async def get_group_member(
        self, *, group_id: UUID, student_id: UUID
    ) -> StudentGroupMember | None:
        result = await self.session.execute(
            select(StudentGroupMember).where(
                StudentGroupMember.group_id == group_id,
                StudentGroupMember.student_id == student_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def create_group(
        self, *, class_id: UUID, name: str, actor_user_id: UUID
    ) -> StudentGroup:
        row = StudentGroup(
            id=uuid4(),
            teaching_class_id=class_id,
            name=name,
            status="active",
            created_by=actor_user_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_group_member(
        self,
        *,
        group_id: UUID,
        student_id: UUID,
        status: str,
        actor_user_id: UUID,
    ) -> StudentGroupMember:
        row = StudentGroupMember(
            id=uuid4(),
            group_id=group_id,
            student_id=student_id,
            status=status,
            changed_by=actor_user_id,
            changed_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def set_group_member_state(
        self, row: StudentGroupMember, *, status: str, actor_user_id: UUID
    ) -> StudentGroupMember:
        row.status = status
        row.changed_by = actor_user_id
        row.changed_at = datetime.now(UTC)
        await self.session.flush()
        return row

    async def get_audit_by_request(
        self, *, actor_user_id: UUID, request_id: str
    ) -> GovernanceAuditEvent | None:
        result = await self.session.execute(
            select(GovernanceAuditEvent).where(
                GovernanceAuditEvent.actor_user_id == actor_user_id,
                GovernanceAuditEvent.request_id == request_id,
            )
        )
        return result.scalar_one_or_none()

    async def write_audit(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        object_type: str,
        object_id: UUID,
        reason: str | None,
        result_status: str,
        request_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceAuditEvent:
        row = GovernanceAuditEvent(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            result_status=result_status,
            request_id=request_id,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
