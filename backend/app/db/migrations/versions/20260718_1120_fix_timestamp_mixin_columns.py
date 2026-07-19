# Status: real

"""Align fairness and benchmark tables with ``TimestampMixin``.

Revision ID: 20260718_1120
Revises: 20260717_1110
Create Date: 2026-07-18 14:10:00

The original fairness/benchmark DDL (20260715_1085) omitted the shared
``created_at`` and ``updated_at`` columns on three tables whose ORM models
inherit ``TimestampMixin``.  This additive migration repairs existing
databases without changing data or the historical migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_1120"
down_revision: str | None = "20260717_1110"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = ("fairness_metric_runs", "fairness_reviews", "benchmark_runs")


def upgrade() -> None:
    for table_name in _TABLES:
        op.add_column(
            table_name,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.add_column(
            table_name,
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    for table_name in reversed(_TABLES):
        op.drop_column(table_name, "updated_at")
        op.drop_column(table_name, "created_at")
