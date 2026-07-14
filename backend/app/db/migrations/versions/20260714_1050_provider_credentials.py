# Status: real

"""Add encrypted user provider credentials and root credential provenance.

Revision ID: 20260714_1050
Revises: 20260712_1040
Create Date: 2026-07-14 03:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260714_1050"
down_revision: str | None = "20260712_1040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_status", sa.String(length=16), nullable=False, server_default="unverified"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("provider IN ('deepseek', 'xfyun')", name="ck_provider_credentials_provider"),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'invalid', 'error')",
            name="ck_provider_credentials_verification_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "provider", "name", name="uq_provider_credentials_user_provider_name"),
    )
    op.create_index("ix_provider_credentials_user_id", "provider_credentials", ["user_id"])
    op.create_index("ix_provider_credentials_provider", "provider_credentials", ["provider"])
    op.create_index(
        "uq_provider_credentials_active_user_provider",
        "provider_credentials",
        ["user_id", "provider"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )
    with op.batch_alter_table("workflow_runs") as batch:
        batch.add_column(sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True))
        batch.create_foreign_key(
            "fk_workflow_runs_credential_id_provider_credentials",
            "provider_credentials",
            ["credential_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_workflow_runs_credential_id", "workflow_runs", ["credential_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_credential_id", table_name="workflow_runs")
    with op.batch_alter_table("workflow_runs") as batch:
        batch.drop_constraint("fk_workflow_runs_credential_id_provider_credentials", type_="foreignkey")
        batch.drop_column("credential_id")
    op.drop_index("uq_provider_credentials_active_user_provider", table_name="provider_credentials")
    op.drop_index("ix_provider_credentials_provider", table_name="provider_credentials")
    op.drop_index("ix_provider_credentials_user_id", table_name="provider_credentials")
    op.drop_table("provider_credentials")
