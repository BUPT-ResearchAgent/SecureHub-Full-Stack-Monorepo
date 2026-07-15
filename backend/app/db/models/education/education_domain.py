# Status: real

"""Durable teaching relationships and append-only governance audit records.

The models intentionally reference the existing ``users`` and ``courses``
authorities.  They do not duplicate identity, course, profile, or knowledge
asset data.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CourseTeacherAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A teacher's durable authority boundary for a course."""

    __tablename__ = "course_teacher_assignments"
    __table_args__ = (
        CheckConstraint(
            "assignment_role IN ('owner', 'teacher', 'assistant')",
            name="ck_course_teacher_assignments_role",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_course_teacher_assignments_status",
        ),
        Index(
            "uq_course_teacher_assignments_active",
            "course_id",
            "teacher_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_role: Mapped[str] = mapped_column(String(24), nullable=False, server_default="teacher")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TeachingClass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A teaching section under one existing course."""

    __tablename__ = "teaching_classes"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_teaching_classes_status"),
        UniqueConstraint("course_id", "code", name="uq_teaching_classes_course_code"),
        # Required by the composite enrollment FK: it prevents a class from
        # being paired with a course other than its own.
        UniqueConstraint("id", "course_id", name="uq_teaching_classes_id_course"),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )


class TeachingClassTeacher(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A course-authorized teacher's assignment to one teaching class."""

    __tablename__ = "teaching_class_teachers"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'teacher', 'assistant')",
            name="ck_teaching_class_teachers_role",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_teaching_class_teachers_status",
        ),
        Index(
            "uq_teaching_class_teachers_active",
            "teaching_class_id",
            "teacher_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    teaching_class_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teaching_classes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False, server_default="teacher")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CourseEnrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The single durable enrollment authority for a student/course pair."""

    __tablename__ = "course_enrollments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('enrolled', 'dropped', 'completed')",
            name="ck_course_enrollments_status",
        ),
        UniqueConstraint("course_id", "student_id", name="uq_course_enrollments_course_student"),
        ForeignKeyConstraint(
            ["teaching_class_id", "course_id"],
            ["teaching_classes.id", "teaching_classes.course_id"],
            name="fk_course_enrollments_teaching_class_course",
            ondelete="RESTRICT",
        ),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teaching_class_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="enrolled")
    enrolled_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudentGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named student group inside one teaching class."""

    __tablename__ = "student_groups"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_student_groups_status"),
        UniqueConstraint("teaching_class_id", "name", name="uq_student_groups_class_name"),
    )

    teaching_class_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teaching_classes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )


class StudentGroupMember(UUIDPrimaryKeyMixin, Base):
    """Latest membership state; every change is also preserved in audit events."""

    __tablename__ = "student_group_members"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'removed')",
            name="ck_student_group_members_status",
        ),
        UniqueConstraint("group_id", "student_id", name="uq_student_group_members_group_student"),
    )

    group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("student_groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    changed_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GovernanceAuditEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only business audit, deliberately separate from Runtime audit logs."""

    __tablename__ = "governance_audit_events"
    __table_args__ = (
        Index(
            "uq_governance_audit_events_actor_request",
            "actor_user_id",
            "request_id",
            unique=True,
            postgresql_where=text("request_id IS NOT NULL"),
            sqlite_where=text("request_id IS NOT NULL"),
        ),
    )

    actor_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    result_status: Mapped[str] = mapped_column(String(24), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
