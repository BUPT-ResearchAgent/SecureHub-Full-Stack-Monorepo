# Status: real

"""Create the durable tasks owned by an existing learning path.

Revision ID: 20260717_1110
Revises: 20260717_1100
Create Date: 2026-07-17 10:20:00

``LearningTask`` has long been part of the path projection model, but no
historical migration created its table.  The table is additive and references
the existing learning-path and unified knowledge-node authorities.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260717_1110"
down_revision: str | None = "20260717_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "learning_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "path_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kp_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="todo"),
        sa.Column("metadata", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_learning_tasks_path_id", "learning_tasks", ["path_id"])
    op.create_index("ix_learning_tasks_kp_id", "learning_tasks", ["kp_id"])
    op.create_index("ix_learning_tasks_status", "learning_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_tasks_status", table_name="learning_tasks")
    op.drop_index("ix_learning_tasks_kp_id", table_name="learning_tasks")
    op.drop_index("ix_learning_tasks_path_id", table_name="learning_tasks")
    op.drop_table("learning_tasks")
