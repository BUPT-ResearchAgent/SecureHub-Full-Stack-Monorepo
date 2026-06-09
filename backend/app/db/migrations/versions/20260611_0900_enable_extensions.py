# Status: [planned]

"""data-layer v2: enable extensions

Revision ID: 20260611_0900
Revises: 20260610_1000
Create Date: 2026-06-11 09:00:00

The v1 init migration already runs ``CREATE EXTENSION IF NOT EXISTS vector``;
this v2 head re-asserts it (idempotent) so a fresh ``alembic upgrade head``
into a freshly bootstrapped database without v1 history still ends up with
pgvector. Idempotent on PostgreSQL and a no-op on every other dialect.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260611_0900"
down_revision: str | None = "20260610_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Intentionally left as a no-op: the v1 init's downgrade owns
    # ``DROP EXTENSION vector``, and tearing it down here would race with
    # any sibling table that still holds vector columns.
    pass
