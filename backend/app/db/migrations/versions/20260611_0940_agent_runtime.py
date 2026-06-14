# Status: [planned]

"""data-layer v2: agent runtime

Revision ID: 20260611_0940
Revises: 20260611_0930
Create Date: 2026-06-11 09:40:00

v1 already provisions ``agents`` / ``agent_skills`` / ``agent_runs``. This
migration adds the per-user / per-workflow trace indexes the frontend
visualisation needs, plus the agent_runs.parent_run_id index that the v1
migration declared at the column level but never materialised on dialects
that ignore the inline ``index=True`` flag during ``create_table``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260611_0940"
down_revision: str | None = "20260611_0930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_agent_runs_workflow_created",
        "agent_runs",
        ["workflow_name", "created_at"],
    )
    op.create_index(
        "ix_agent_runs_user_created",
        "agent_runs",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_runs_user_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_workflow_created", table_name="agent_runs")
