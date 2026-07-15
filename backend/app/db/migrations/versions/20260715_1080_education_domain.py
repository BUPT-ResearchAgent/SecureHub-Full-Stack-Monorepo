# Status: real

"""Create durable education relationships and governance audit records.

Revision ID: 20260715_1080
Revises: 20260714_1070
Create Date: 2026-07-15 10:08:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1080"
down_revision: str | None = "20260714_1070"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "course_teacher_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_role", sa.String(length=24), nullable=False, server_default="teacher"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "assignment_role IN ('owner', 'teacher', 'assistant')",
            name="ck_course_teacher_assignments_role",
        ),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_course_teacher_assignments_status"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_course_teacher_assignments_course_id", "course_teacher_assignments", ["course_id"])
    op.create_index("ix_course_teacher_assignments_teacher_id", "course_teacher_assignments", ["teacher_id"])
    op.create_index(
        "uq_course_teacher_assignments_active",
        "course_teacher_assignments",
        ["course_id", "teacher_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "teaching_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_teaching_classes_status"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("course_id", "code", name="uq_teaching_classes_course_code"),
        sa.UniqueConstraint("id", "course_id", name="uq_teaching_classes_id_course"),
    )
    op.create_index("ix_teaching_classes_course_id", "teaching_classes", ["course_id"])

    op.create_table(
        "teaching_class_teachers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="teacher"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("role IN ('owner', 'teacher', 'assistant')", name="ck_teaching_class_teachers_role"),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_teaching_class_teachers_status"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_teaching_class_teachers_class_id", "teaching_class_teachers", ["teaching_class_id"])
    op.create_index("ix_teaching_class_teachers_teacher_id", "teaching_class_teachers", ["teacher_id"])
    op.create_index(
        "uq_teaching_class_teachers_active",
        "teaching_class_teachers",
        ["teaching_class_id", "teacher_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "course_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="enrolled"),
        sa.Column("enrolled_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('enrolled', 'dropped', 'completed')", name="ck_course_enrollments_status"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enrolled_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["teaching_class_id", "course_id"],
            ["teaching_classes.id", "teaching_classes.course_id"],
            name="fk_course_enrollments_teaching_class_course",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("course_id", "student_id", name="uq_course_enrollments_course_student"),
    )
    op.create_index("ix_course_enrollments_course_id", "course_enrollments", ["course_id"])
    op.create_index("ix_course_enrollments_student_id", "course_enrollments", ["student_id"])
    op.create_index("ix_course_enrollments_class_id", "course_enrollments", ["teaching_class_id"])

    op.create_table(
        "student_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_student_groups_status"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("teaching_class_id", "name", name="uq_student_groups_class_name"),
    )
    op.create_index("ix_student_groups_class_id", "student_groups", ["teaching_class_id"])

    op.create_table(
        "student_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'removed')", name="ck_student_group_members_status"),
        sa.ForeignKeyConstraint(["group_id"], ["student_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("group_id", "student_id", name="uq_student_group_members_group_student"),
    )
    op.create_index("ix_student_group_members_group_id", "student_group_members", ["group_id"])
    op.create_index("ix_student_group_members_student_id", "student_group_members", ["student_id"])

    op.create_table(
        "governance_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("result_status", sa.String(length=24), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_governance_audit_events_actor_id", "governance_audit_events", ["actor_user_id"])
    op.create_index("ix_governance_audit_events_object_id", "governance_audit_events", ["object_id"])
    op.create_index(
        "uq_governance_audit_events_actor_request",
        "governance_audit_events",
        ["actor_user_id", "request_id"],
        unique=True,
        postgresql_where=sa.text("request_id IS NOT NULL"),
        sqlite_where=sa.text("request_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_governance_audit_events_actor_request", table_name="governance_audit_events")
    op.drop_index("ix_governance_audit_events_object_id", table_name="governance_audit_events")
    op.drop_index("ix_governance_audit_events_actor_id", table_name="governance_audit_events")
    op.drop_table("governance_audit_events")

    op.drop_index("ix_student_group_members_student_id", table_name="student_group_members")
    op.drop_index("ix_student_group_members_group_id", table_name="student_group_members")
    op.drop_table("student_group_members")

    op.drop_index("ix_student_groups_class_id", table_name="student_groups")
    op.drop_table("student_groups")

    op.drop_index("ix_course_enrollments_class_id", table_name="course_enrollments")
    op.drop_index("ix_course_enrollments_student_id", table_name="course_enrollments")
    op.drop_index("ix_course_enrollments_course_id", table_name="course_enrollments")
    op.drop_table("course_enrollments")

    op.drop_index("uq_teaching_class_teachers_active", table_name="teaching_class_teachers")
    op.drop_index("ix_teaching_class_teachers_teacher_id", table_name="teaching_class_teachers")
    op.drop_index("ix_teaching_class_teachers_class_id", table_name="teaching_class_teachers")
    op.drop_table("teaching_class_teachers")

    op.drop_index("ix_teaching_classes_course_id", table_name="teaching_classes")
    op.drop_table("teaching_classes")

    op.drop_index("uq_course_teacher_assignments_active", table_name="course_teacher_assignments")
    op.drop_index("ix_course_teacher_assignments_teacher_id", table_name="course_teacher_assignments")
    op.drop_index("ix_course_teacher_assignments_course_id", table_name="course_teacher_assignments")
    op.drop_table("course_teacher_assignments")
