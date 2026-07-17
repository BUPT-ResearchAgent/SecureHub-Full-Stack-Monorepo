# Status: real

"""Add durable student path-replan and resource-feedback loop records.

Revision ID: 20260717_1100
Revises: 20260716_1090
Create Date: 2026-07-17 10:00:00

The migration extends existing learning paths, generated resources, workflow
runs and knowledge nodes.  It deliberately introduces no parallel learner,
course, profile, knowledge asset or artifact authority.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260717_1100"
down_revision: str | None = "20260716_1090"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "learning_path_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="baseline"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("diff", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("task_snapshot", _json(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("state IN ('active','historical')", name="ck_learning_path_versions_state"),
        sa.CheckConstraint("kind IN ('baseline','replan','revert')", name="ck_learning_path_versions_kind"),
        sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trigger_event_id"], ["learning_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trigger_workflow_run_id"], ["workflow_runs.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "course_id", "version_no", name="uq_learning_path_versions_user_course_version"),
    )
    for name, columns in (
        ("ix_learning_path_versions_path_id", ["path_id"]),
        ("ix_learning_path_versions_user_id", ["user_id"]),
        ("ix_learning_path_versions_course_id", ["course_id"]),
        ("ix_learning_path_versions_parent_version_id", ["parent_version_id"]),
        ("ix_learning_path_versions_trigger_event_id", ["trigger_event_id"]),
        ("ix_learning_path_versions_trigger_workflow_run_id", ["trigger_workflow_run_id"]),
        ("ix_learning_path_versions_user_course_state", ["user_id", "course_id", "state"]),
    ):
        op.create_index(name, "learning_path_versions", columns)

    op.create_table(
        "learning_path_replan_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_path_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accepted_path_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("affected_kp_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("expected_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proposed_task_snapshot", _json(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("recommendation_plan", _json(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("status IN ('pending','deferred','accepted','reverted','expired')", name="ck_learning_path_replan_candidates_status"),
        sa.CheckConstraint("expected_minutes >= 0", name="ck_learning_path_replan_candidates_minutes"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_path_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["accepted_path_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trigger_event_id"], ["learning_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trigger_workflow_run_id"], ["workflow_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["affected_kp_id"], ["knowledge_nodes.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", "course_id", "input_fingerprint", name="uq_learning_path_replan_candidates_input"),
    )
    for name, columns in (
        ("ix_learning_path_replan_candidates_student_id", ["student_id"]),
        ("ix_learning_path_replan_candidates_course_id", ["course_id"]),
        ("ix_learning_path_replan_candidates_source_path_version_id", ["source_path_version_id"]),
        ("ix_learning_path_replan_candidates_accepted_path_version_id", ["accepted_path_version_id"]),
        ("ix_learning_path_replan_candidates_trigger_event_id", ["trigger_event_id"]),
        ("ix_learning_path_replan_candidates_trigger_workflow_run_id", ["trigger_workflow_run_id"]),
        ("ix_learning_path_replan_candidates_affected_kp_id", ["affected_kp_id"]),
        ("ix_learning_path_replan_candidates_student_course_status", ["student_id", "course_id", "status"]),
    ):
        op.create_index(name, "learning_path_replan_candidates", columns)

    op.create_table(
        "learning_path_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("source_path_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resulting_path_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('accept','defer','revert')", name="ck_learning_path_decisions_decision"),
        sa.ForeignKeyConstraint(["candidate_id"], ["learning_path_replan_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_path_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resulting_path_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_learning_path_decisions_candidate_id", ["candidate_id"]),
        ("ix_learning_path_decisions_student_id", ["student_id"]),
        ("ix_learning_path_decisions_candidate_created", ["candidate_id", "created_at"]),
    ):
        op.create_index(name, "learning_path_decisions", columns)

    op.create_table(
        "course_resource_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kp_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("path_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("match_context", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('scheduled','accepted','deferred','rejected','superseded','feedback_received','completed')", name="ck_course_resource_recommendations_status"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resource_id"], ["generated_resources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["kp_id"], ["knowledge_nodes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["path_version_id"], ["learning_path_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_candidate_id"], ["learning_path_replan_candidates.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_course_resource_recommendations_student_id", ["student_id"]),
        ("ix_course_resource_recommendations_course_id", ["course_id"]),
        ("ix_course_resource_recommendations_resource_id", ["resource_id"]),
        ("ix_course_resource_recommendations_kp_id", ["kp_id"]),
        ("ix_course_resource_recommendations_path_version_id", ["path_version_id"]),
        ("ix_course_resource_recommendations_source_candidate_id", ["source_candidate_id"]),
        ("ix_course_resource_recommendations_student_course_status", ["student_id", "course_id", "status"]),
    ):
        op.create_index(name, "course_resource_recommendations", columns)

    op.create_table(
        "resource_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kp_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("follow_up_recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retry_workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resulting_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_kinds", _json(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="submitted"),
        sa.Column("outcome", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("status IN ('submitted','retry_requested','regenerated','provider_unavailable','failed','rejected')", name="ck_resource_feedback_status"),
        sa.ForeignKeyConstraint(["resource_id"], ["generated_resources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["kp_id"], ["knowledge_nodes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["course_resource_recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["follow_up_recommendation_id"], ["course_resource_recommendations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retry_workflow_run_id"], ["workflow_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resulting_resource_id"], ["generated_resources.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_resource_feedback_resource_id", ["resource_id"]),
        ("ix_resource_feedback_student_id", ["student_id"]),
        ("ix_resource_feedback_course_id", ["course_id"]),
        ("ix_resource_feedback_kp_id", ["kp_id"]),
        ("ix_resource_feedback_recommendation_id", ["recommendation_id"]),
        ("ix_resource_feedback_follow_up_recommendation_id", ["follow_up_recommendation_id"]),
        ("ix_resource_feedback_retry_workflow_run_id", ["retry_workflow_run_id"]),
        ("ix_resource_feedback_resulting_resource_id", ["resulting_resource_id"]),
        ("ix_resource_feedback_student_course_status", ["student_id", "course_id", "status"]),
    ):
        op.create_index(name, "resource_feedback", columns)


def downgrade() -> None:
    for name in (
        "ix_resource_feedback_student_course_status", "ix_resource_feedback_resulting_resource_id",
        "ix_resource_feedback_retry_workflow_run_id", "ix_resource_feedback_follow_up_recommendation_id",
        "ix_resource_feedback_recommendation_id", "ix_resource_feedback_kp_id",
        "ix_resource_feedback_course_id", "ix_resource_feedback_student_id", "ix_resource_feedback_resource_id",
    ):
        op.drop_index(name, table_name="resource_feedback")
    op.drop_table("resource_feedback")

    for name in (
        "ix_course_resource_recommendations_student_course_status", "ix_course_resource_recommendations_source_candidate_id",
        "ix_course_resource_recommendations_path_version_id", "ix_course_resource_recommendations_kp_id",
        "ix_course_resource_recommendations_resource_id", "ix_course_resource_recommendations_course_id",
        "ix_course_resource_recommendations_student_id",
    ):
        op.drop_index(name, table_name="course_resource_recommendations")
    op.drop_table("course_resource_recommendations")

    for name in (
        "ix_learning_path_decisions_candidate_created", "ix_learning_path_decisions_student_id",
        "ix_learning_path_decisions_candidate_id",
    ):
        op.drop_index(name, table_name="learning_path_decisions")
    op.drop_table("learning_path_decisions")

    for name in (
        "ix_learning_path_replan_candidates_student_course_status", "ix_learning_path_replan_candidates_affected_kp_id",
        "ix_learning_path_replan_candidates_trigger_workflow_run_id", "ix_learning_path_replan_candidates_trigger_event_id",
        "ix_learning_path_replan_candidates_accepted_path_version_id", "ix_learning_path_replan_candidates_source_path_version_id",
        "ix_learning_path_replan_candidates_course_id", "ix_learning_path_replan_candidates_student_id",
    ):
        op.drop_index(name, table_name="learning_path_replan_candidates")
    op.drop_table("learning_path_replan_candidates")

    for name in (
        "ix_learning_path_versions_user_course_state", "ix_learning_path_versions_trigger_workflow_run_id",
        "ix_learning_path_versions_trigger_event_id", "ix_learning_path_versions_parent_version_id",
        "ix_learning_path_versions_course_id", "ix_learning_path_versions_user_id", "ix_learning_path_versions_path_id",
    ):
        op.drop_index(name, table_name="learning_path_versions")
    op.drop_table("learning_path_versions")
