# Status: real

"""Add server-authoritative demo roles to user identities.

Revision ID: 20260714_1070
Revises: 20260714_1060
Create Date: 2026-07-14 16:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_1070"
down_revision: str | None = "20260714_1060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE_CHECK = "role IN ('student', 'course_teacher', 'research_mentor', 'career_mentor', 'hybrid')"


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "role",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'student'"),
            )
        )
        batch.create_check_constraint("ck_users_role", _ROLE_CHECK)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role", type_="check")
        batch.drop_column("role")
