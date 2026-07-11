# Status: real

"""Add the durable learning path projection used by course_plan_v1.

Revision ID: 20260711_1020
Revises: 20260711_1010
Create Date: 2026-07-11 10:20:00

The ORM existed before the Wave 3 adapter, but no historical migration created
the table. This additive migration makes PersistLearningPath a real
WorkflowAction rather than an in-memory compatibility response.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260711_1020"
down_revision: str | None = "20260711_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_learning_paths_user_id", "learning_paths", ["user_id"])
    op.create_index("ix_learning_paths_course_id", "learning_paths", ["course_id"])
    op.create_index("ix_learning_paths_status", "learning_paths", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_paths_status", table_name="learning_paths")
    op.drop_index("ix_learning_paths_course_id", table_name="learning_paths")
    op.drop_index("ix_learning_paths_user_id", table_name="learning_paths")
    op.drop_table("learning_paths")
