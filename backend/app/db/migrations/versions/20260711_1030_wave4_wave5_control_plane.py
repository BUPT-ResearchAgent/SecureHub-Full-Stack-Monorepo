# Status: real

"""Add Wave 4 lineage and Wave 5 HITL/audit persistence.

Revision ID: 20260711_1030
Revises: 20260711_1020
Create Date: 2026-07-11 10:30:00

The migration is additive. Approval decisions, audit facts and artifact
lineage remain durable even when a root is later blocked or a worker is fenced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260711_1030"
down_revision: str | None = "20260711_1020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "workflow_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(length=120), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("request", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("decision", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("requested_by", sa.String(length=128), nullable=True),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_approvals_workflow_run_id", "workflow_approvals", ["workflow_run_id"])
    op.create_index("ix_workflow_approvals_node_id", "workflow_approvals", ["node_id"])
    op.create_index("ix_workflow_approvals_kind", "workflow_approvals", ["kind"])
    op.create_index("ix_workflow_approvals_status", "workflow_approvals", ["status"])
    op.create_index("ix_workflow_approvals_run_status", "workflow_approvals", ["workflow_run_id", "status"])

    op.create_table(
        "workflow_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("node_id", sa.String(length=120), nullable=True),
        sa.Column("details", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_audit_logs_workflow_run_id", "workflow_audit_logs", ["workflow_run_id"])
    op.create_index("ix_workflow_audit_logs_action", "workflow_audit_logs", ["action"])
    op.create_index("ix_workflow_audit_logs_run_created", "workflow_audit_logs", ["workflow_run_id", "created_at"])

    op.create_table(
        "resource_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("resource_id", "version", name="uq_resource_versions_resource_version"),
    )
    op.create_index("ix_resource_versions_resource_id", "resource_versions", ["resource_id"])

    with op.batch_alter_table("generated_resources") as batch:
        batch.add_column(sa.Column("parent_resource_id", postgresql.UUID(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("lineage_root_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_generated_resources_parent_resource_id", "generated_resources", ["parent_resource_id"])
    op.create_index("ix_generated_resources_lineage_root_id", "generated_resources", ["lineage_root_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_resources_lineage_root_id", table_name="generated_resources")
    op.drop_index("ix_generated_resources_parent_resource_id", table_name="generated_resources")
    with op.batch_alter_table("generated_resources") as batch:
        batch.drop_column("lineage_root_id")
        batch.drop_column("parent_resource_id")

    op.drop_index("ix_resource_versions_resource_id", table_name="resource_versions")
    op.drop_table("resource_versions")

    op.drop_index("ix_workflow_audit_logs_run_created", table_name="workflow_audit_logs")
    op.drop_index("ix_workflow_audit_logs_action", table_name="workflow_audit_logs")
    op.drop_index("ix_workflow_audit_logs_workflow_run_id", table_name="workflow_audit_logs")
    op.drop_table("workflow_audit_logs")

    op.drop_index("ix_workflow_approvals_run_status", table_name="workflow_approvals")
    op.drop_index("ix_workflow_approvals_status", table_name="workflow_approvals")
    op.drop_index("ix_workflow_approvals_kind", table_name="workflow_approvals")
    op.drop_index("ix_workflow_approvals_node_id", table_name="workflow_approvals")
    op.drop_index("ix_workflow_approvals_workflow_run_id", table_name="workflow_approvals")
    op.drop_table("workflow_approvals")
