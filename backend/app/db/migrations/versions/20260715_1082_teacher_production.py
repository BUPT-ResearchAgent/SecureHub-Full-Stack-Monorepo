# Status: real

"""Create governed teacher-production state for F1 / FG-02 / FG-05 / FG-06.

Revision ID: 20260715_1082
Revises: 20260715_1081
Create Date: 2026-07-15 14:20:00

All new rows reference the existing users, courses, unified knowledge asset
tables, learning facts, and Runtime evidence/run records.  No parallel user,
course, profile, document/chunk/vector, or Agent authority is introduced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1082"
down_revision: str | None = "20260715_1081"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "course_document_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bound_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False, server_default="teaching_material"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active','withdrawn','deleted')", name="ck_course_document_bindings_status"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bound_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("course_id", "document_id", name="uq_course_document_bindings_course_document"),
    )
    op.create_index("ix_course_document_bindings_course_id", "course_document_bindings", ["course_id"])
    op.create_index("ix_course_document_bindings_document_id", "course_document_bindings", ["document_id"])
    op.create_index("ix_course_document_bindings_bound_by", "course_document_bindings", ["bound_by"])

    op.create_table(
        "course_asset_governance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("binding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="processing"),
        sa.Column("correction_of_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('uploading','processing','ready','correction_pending','corrected','withdrawn','deleted')",
            name="ck_course_asset_governance_state",
        ),
        sa.ForeignKeyConstraint(["binding_id"], ["course_document_bindings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_asset_id"], ["document_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_resource_id"], ["generated_resources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["correction_of_id"], ["course_asset_governance.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["withdrawn_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("binding_id", "version_no", name="uq_course_asset_governance_binding_version"),
    )
    op.create_index("ix_course_asset_governance_binding_id", "course_asset_governance", ["binding_id"])
    op.create_index("ix_course_asset_governance_document_asset_id", "course_asset_governance", ["document_asset_id"])
    op.create_index("ix_course_asset_governance_current_resource_id", "course_asset_governance", ["current_resource_id"])
    op.create_index("ix_course_asset_governance_owner_teacher_id", "course_asset_governance", ["owner_teacher_id"])
    op.create_index("ix_course_asset_governance_correction_of_id", "course_asset_governance", ["correction_of_id"])
    op.create_index("ix_course_asset_governance_owner_state", "course_asset_governance", ["owner_teacher_id", "state"])

    op.create_table(
        "quiz_review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("quiz_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_status", sa.String(length=40), nullable=False),
        sa.Column("after_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('publish','reject','withdraw')", name="ck_quiz_review_decisions_decision"
        ),
        sa.ForeignKeyConstraint(["quiz_item_id"], ["quiz_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_quiz_review_decisions_quiz_item_id", "quiz_review_decisions", ["quiz_item_id"])
    op.create_index("ix_quiz_review_decisions_teacher_id", "quiz_review_decisions", ["teacher_id"])
    op.create_index("ix_quiz_review_decisions_item_created", "quiz_review_decisions", ["quiz_item_id", "created_at"])

    op.create_table(
        "class_weakness_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("score_version", sa.String(length=64), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("aggregates", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["group_id"], ["student_groups.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "course_id", "teaching_class_id", "group_id", "input_fingerprint",
            name="uq_class_weakness_snapshots_reproducible_input",
        ),
    )
    op.create_index("ix_class_weakness_snapshots_course_id", "class_weakness_snapshots", ["course_id"])
    op.create_index("ix_class_weakness_snapshots_teaching_class_id", "class_weakness_snapshots", ["teaching_class_id"])
    op.create_index("ix_class_weakness_snapshots_group_id", "class_weakness_snapshots", ["group_id"])
    op.create_index("ix_class_weakness_snapshots_scope", "class_weakness_snapshots", ["course_id", "teaching_class_id", "group_id"])

    op.create_table(
        "teaching_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("diff", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending','adopted','rejected','superseded','withdrawn')",
            name="ck_teaching_recommendations_status",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["group_id"], ["student_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["class_weakness_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_snapshot_id"], ["workflow_evidence_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("course_id", "version_no", name="uq_teaching_recommendations_course_version"),
    )
    for name, columns in (
        ("ix_teaching_recommendations_course_id", ["course_id"]),
        ("ix_teaching_recommendations_teaching_class_id", ["teaching_class_id"]),
        ("ix_teaching_recommendations_group_id", ["group_id"]),
        ("ix_teaching_recommendations_source_snapshot_id", ["source_snapshot_id"]),
        ("ix_teaching_recommendations_evidence_snapshot_id", ["evidence_snapshot_id"]),
        ("ix_teaching_recommendations_agent_run_id", ["agent_run_id"]),
        ("ix_teaching_recommendations_created_by", ["created_by"]),
    ):
        op.create_index(name, "teaching_recommendations", columns)

    op.create_table(
        "teaching_recommendation_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('adopt','reject','withdraw')",
            name="ck_teaching_recommendation_decisions_decision",
        ),
        sa.ForeignKeyConstraint(["recommendation_id"], ["teaching_recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_teaching_recommendation_decisions_recommendation_id", "teaching_recommendation_decisions", ["recommendation_id"])
    op.create_index("ix_teaching_recommendation_decisions_teacher_id", "teaching_recommendation_decisions", ["teacher_id"])
    op.create_index("ix_teaching_recommendation_decisions_recommendation", "teaching_recommendation_decisions", ["recommendation_id", "created_at"])

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("logical_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('assignment','exam')", name="ck_assessments_kind"),
        sa.CheckConstraint(
            "status IN ('draft','published','closed','withdrawn')", name="ck_assessments_status"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("course_id", "logical_key", name="uq_assessments_course_logical_key"),
    )
    op.create_index("ix_assessments_course_id", "assessments", ["course_id"])
    op.create_index("ix_assessments_owner_teacher_id", "assessments", ["owner_teacher_id"])

    op.create_table(
        "assessment_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('draft','published','withdrawn')", name="ck_assessment_versions_state"
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("assessment_id", "version_no", name="uq_assessment_versions_assessment_version"),
    )
    op.create_index("ix_assessment_versions_assessment_id", "assessment_versions", ["assessment_id"])
    op.create_index("ix_assessment_versions_created_by", "assessment_versions", ["created_by"])

    op.create_table(
        "assessment_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quiz_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("grading_mode", sa.String(length=16), nullable=False),
        sa.Column("question_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint(
            "grading_mode IN ('objective','subjective')", name="ck_assessment_items_grading_mode"
        ),
        sa.CheckConstraint("points > 0", name="ck_assessment_items_points_positive"),
        sa.ForeignKeyConstraint(["assessment_version_id"], ["assessment_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quiz_item_id"], ["quiz_items.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("assessment_version_id", "position", name="uq_assessment_items_version_position"),
        sa.UniqueConstraint("assessment_version_id", "quiz_item_id", name="uq_assessment_items_version_quiz"),
    )
    op.create_index("ix_assessment_items_assessment_version_id", "assessment_items", ["assessment_version_id"])
    op.create_index("ix_assessment_items_quiz_item_id", "assessment_items", ["quiz_item_id"])

    op.create_table(
        "assessment_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allow_late", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "target_type IN ('class','group','student')", name="ck_assessment_assignments_target_type"
        ),
        sa.CheckConstraint(
            "status IN ('active','closed','withdrawn')", name="ck_assessment_assignments_status"
        ),
        sa.ForeignKeyConstraint(["assessment_version_id"], ["assessment_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["group_id"], ["student_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "assessment_version_id", "target_type", "teaching_class_id", "group_id", "student_id",
            name="uq_assessment_assignments_target",
        ),
    )
    for name, columns in (
        ("ix_assessment_assignments_assessment_version_id", ["assessment_version_id"]),
        ("ix_assessment_assignments_teaching_class_id", ["teaching_class_id"]),
        ("ix_assessment_assignments_group_id", ["group_id"]),
        ("ix_assessment_assignments_student_id", ["student_id"]),
        ("ix_assessment_assignments_assigned_by", ["assigned_by"]),
        ("ix_assessment_assignments_class_status", ["teaching_class_id", "status"]),
    ):
        op.create_index(name, "assessment_assignments", columns)

    op.create_table(
        "assessment_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('open','submitted','late','locked')", name="ck_assessment_submissions_status"
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["assessment_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_assessment_submissions_assignment_student"),
    )
    op.create_index("ix_assessment_submissions_assignment_id", "assessment_submissions", ["assignment_id"])
    op.create_index("ix_assessment_submissions_student_id", "assessment_submissions", ["student_id"])

    op.create_table(
        "assessment_grade_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("objective_score", sa.Float(), nullable=True),
        sa.Column("ai_suggested_score", sa.Float(), nullable=True),
        sa.Column("ai_agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_evidence_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_suggestion_status", sa.String(length=24), nullable=False, server_default="not_requested"),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("graded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending','auto_scored','teacher_reviewed','published','withdrawn')",
            name="ck_assessment_grade_decisions_status",
        ),
        sa.CheckConstraint(
            "ai_suggestion_status IN ('not_requested','suggested','rejected')",
            name="ck_assessment_grade_decisions_ai_status",
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["assessment_submissions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ai_agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ai_evidence_snapshot_id"], ["workflow_evidence_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["graded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("submission_id", name="uq_assessment_grade_decisions_submission"),
    )
    for name, columns in (
        ("ix_assessment_grade_decisions_submission_id", ["submission_id"]),
        ("ix_assessment_grade_decisions_ai_agent_run_id", ["ai_agent_run_id"]),
        ("ix_assessment_grade_decisions_ai_evidence_snapshot_id", ["ai_evidence_snapshot_id"]),
        ("ix_assessment_grade_decisions_graded_by", ["graded_by"]),
    ):
        op.create_index(name, "assessment_grade_decisions", columns)

    # The current pointer is added only after both tables exist, avoiding a
    # circular create-time FK while retaining an explicit published lineage.
    op.create_table(
        "course_syllabuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_published_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("course_id", name="uq_course_syllabuses_course"),
    )
    op.create_index("ix_course_syllabuses_course_id", "course_syllabuses", ["course_id"])
    op.create_index("ix_course_syllabuses_current_published_version_id", "course_syllabuses", ["current_published_version_id"])

    op.create_table(
        "course_syllabus_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("syllabus_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("typed_content", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content_schema_version", sa.String(length=32), nullable=False, server_default="syllabus-v1"),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("generated_from_agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('draft','generation_pending','review_pending','published','superseded','withdrawn')",
            name="ck_course_syllabus_versions_state",
        ),
        sa.ForeignKeyConstraint(["syllabus_id"], ["course_syllabuses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_from_agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_snapshot_id"], ["workflow_evidence_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("syllabus_id", "version_no", name="uq_course_syllabus_versions_syllabus_version"),
    )
    for name, columns in (
        ("ix_course_syllabus_versions_syllabus_id", ["syllabus_id"]),
        ("ix_course_syllabus_versions_generated_from_agent_run_id", ["generated_from_agent_run_id"]),
        ("ix_course_syllabus_versions_evidence_snapshot_id", ["evidence_snapshot_id"]),
        ("ix_course_syllabus_versions_created_by", ["created_by"]),
    ):
        op.create_index(name, "course_syllabus_versions", columns)
    op.create_foreign_key(
        "fk_course_syllabuses_current_published_version",
        "course_syllabuses",
        "course_syllabus_versions",
        ["current_published_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "syllabus_review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('approve','reject','withdraw')", name="ck_syllabus_review_decisions_decision"
        ),
        sa.ForeignKeyConstraint(["version_id"], ["course_syllabus_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_syllabus_review_decisions_version_id", "syllabus_review_decisions", ["version_id"])
    op.create_index("ix_syllabus_review_decisions_reviewer_id", "syllabus_review_decisions", ["reviewer_id"])
    op.create_index("ix_syllabus_review_decisions_version", "syllabus_review_decisions", ["version_id", "created_at"])

    op.create_table(
        "syllabus_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("generated_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ready"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("format IN ('json','markdown')", name="ck_syllabus_exports_format"),
        sa.CheckConstraint("status IN ('ready','withdrawn','failed')", name="ck_syllabus_exports_status"),
        sa.ForeignKeyConstraint(["version_id"], ["course_syllabus_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generated_resource_id"], ["generated_resources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["storage_object_id"], ["storage_objects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_syllabus_exports_version_id", ["version_id"]),
        ("ix_syllabus_exports_generated_resource_id", ["generated_resource_id"]),
        ("ix_syllabus_exports_storage_object_id", ["storage_object_id"]),
        ("ix_syllabus_exports_created_by", ["created_by"]),
    ):
        op.create_index(name, "syllabus_exports", columns)


def downgrade() -> None:
    for name in (
        "ix_syllabus_exports_created_by",
        "ix_syllabus_exports_storage_object_id",
        "ix_syllabus_exports_generated_resource_id",
        "ix_syllabus_exports_version_id",
    ):
        op.drop_index(name, table_name="syllabus_exports")
    op.drop_table("syllabus_exports")

    for name in (
        "ix_syllabus_review_decisions_version",
        "ix_syllabus_review_decisions_reviewer_id",
        "ix_syllabus_review_decisions_version_id",
    ):
        op.drop_index(name, table_name="syllabus_review_decisions")
    op.drop_table("syllabus_review_decisions")

    op.drop_constraint(
        "fk_course_syllabuses_current_published_version", "course_syllabuses", type_="foreignkey"
    )
    for name in (
        "ix_course_syllabus_versions_created_by",
        "ix_course_syllabus_versions_evidence_snapshot_id",
        "ix_course_syllabus_versions_generated_from_agent_run_id",
        "ix_course_syllabus_versions_syllabus_id",
    ):
        op.drop_index(name, table_name="course_syllabus_versions")
    op.drop_table("course_syllabus_versions")
    op.drop_index("ix_course_syllabuses_current_published_version_id", table_name="course_syllabuses")
    op.drop_index("ix_course_syllabuses_course_id", table_name="course_syllabuses")
    op.drop_table("course_syllabuses")

    for name in (
        "ix_assessment_grade_decisions_graded_by",
        "ix_assessment_grade_decisions_ai_evidence_snapshot_id",
        "ix_assessment_grade_decisions_ai_agent_run_id",
        "ix_assessment_grade_decisions_submission_id",
    ):
        op.drop_index(name, table_name="assessment_grade_decisions")
    op.drop_table("assessment_grade_decisions")
    op.drop_index("ix_assessment_submissions_student_id", table_name="assessment_submissions")
    op.drop_index("ix_assessment_submissions_assignment_id", table_name="assessment_submissions")
    op.drop_table("assessment_submissions")
    for name in (
        "ix_assessment_assignments_class_status",
        "ix_assessment_assignments_assigned_by",
        "ix_assessment_assignments_student_id",
        "ix_assessment_assignments_group_id",
        "ix_assessment_assignments_teaching_class_id",
        "ix_assessment_assignments_assessment_version_id",
    ):
        op.drop_index(name, table_name="assessment_assignments")
    op.drop_table("assessment_assignments")
    op.drop_index("ix_assessment_items_quiz_item_id", table_name="assessment_items")
    op.drop_index("ix_assessment_items_assessment_version_id", table_name="assessment_items")
    op.drop_table("assessment_items")
    op.drop_index("ix_assessment_versions_created_by", table_name="assessment_versions")
    op.drop_index("ix_assessment_versions_assessment_id", table_name="assessment_versions")
    op.drop_table("assessment_versions")
    op.drop_index("ix_assessments_owner_teacher_id", table_name="assessments")
    op.drop_index("ix_assessments_course_id", table_name="assessments")
    op.drop_table("assessments")

    op.drop_index(
        "ix_teaching_recommendation_decisions_recommendation", table_name="teaching_recommendation_decisions"
    )
    op.drop_index(
        "ix_teaching_recommendation_decisions_teacher_id", table_name="teaching_recommendation_decisions"
    )
    op.drop_index(
        "ix_teaching_recommendation_decisions_recommendation_id", table_name="teaching_recommendation_decisions"
    )
    op.drop_table("teaching_recommendation_decisions")
    for name in (
        "ix_teaching_recommendations_created_by",
        "ix_teaching_recommendations_agent_run_id",
        "ix_teaching_recommendations_evidence_snapshot_id",
        "ix_teaching_recommendations_source_snapshot_id",
        "ix_teaching_recommendations_group_id",
        "ix_teaching_recommendations_teaching_class_id",
        "ix_teaching_recommendations_course_id",
    ):
        op.drop_index(name, table_name="teaching_recommendations")
    op.drop_table("teaching_recommendations")
    op.drop_index("ix_class_weakness_snapshots_scope", table_name="class_weakness_snapshots")
    op.drop_index("ix_class_weakness_snapshots_group_id", table_name="class_weakness_snapshots")
    op.drop_index("ix_class_weakness_snapshots_teaching_class_id", table_name="class_weakness_snapshots")
    op.drop_index("ix_class_weakness_snapshots_course_id", table_name="class_weakness_snapshots")
    op.drop_table("class_weakness_snapshots")
    op.drop_index("ix_quiz_review_decisions_item_created", table_name="quiz_review_decisions")
    op.drop_index("ix_quiz_review_decisions_teacher_id", table_name="quiz_review_decisions")
    op.drop_index("ix_quiz_review_decisions_quiz_item_id", table_name="quiz_review_decisions")
    op.drop_table("quiz_review_decisions")
    for name in (
        "ix_course_asset_governance_owner_state",
        "ix_course_asset_governance_correction_of_id",
        "ix_course_asset_governance_owner_teacher_id",
        "ix_course_asset_governance_current_resource_id",
        "ix_course_asset_governance_document_asset_id",
        "ix_course_asset_governance_binding_id",
    ):
        op.drop_index(name, table_name="course_asset_governance")
    op.drop_table("course_asset_governance")
    op.drop_index("ix_course_document_bindings_bound_by", table_name="course_document_bindings")
    op.drop_index("ix_course_document_bindings_document_id", table_name="course_document_bindings")
    op.drop_index("ix_course_document_bindings_course_id", table_name="course_document_bindings")
    op.drop_table("course_document_bindings")
