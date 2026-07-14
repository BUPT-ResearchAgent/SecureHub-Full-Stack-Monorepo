# Status: real

"""Keep root-selected credential IDs when a credential is deleted.

Revision ID: 20260714_1060
Revises: 20260714_1050
Create Date: 2026-07-14 03:25:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260714_1060"
down_revision: str | None = "20260714_1050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The opaque root ID is deliberately not a foreign key. SET NULL would
    # cause an old root to take the environment-key fallback after deletion.
    # Keeping its ID lets the resolver fail closed instead.
    with op.batch_alter_table("workflow_runs") as batch:
        batch.drop_constraint("fk_workflow_runs_credential_id_provider_credentials", type_="foreignkey")


def downgrade() -> None:
    # Restoring the previous schema also restores its previous SET NULL
    # behavior; operators should drain/delete affected roots before rollback.
    with op.batch_alter_table("workflow_runs") as batch:
        batch.create_foreign_key(
            "fk_workflow_runs_credential_id_provider_credentials",
            "provider_credentials",
            ["credential_id"],
            ["id"],
            ondelete="SET NULL",
        )
