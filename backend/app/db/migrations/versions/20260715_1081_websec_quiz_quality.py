# Status: real

"""Add stable WebSec quiz quality metadata, evidence bindings, and reports.

Revision ID: 20260715_1081
Revises: 20260715_1080
Create Date: 2026-07-15 11:20:00

The migration only extends ``quiz_items`` and references existing
``knowledge_nodes``/``chunks``/``users`` rows.  It does not create a parallel
course, knowledge, user, or profile authority.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1081"
down_revision: str | None = "20260715_1080"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing early demo rows receive deterministic legacy keys.  The WebSec
    # seed subsequently assigns their stable canonical keys and citations.
    op.add_column("quiz_items", sa.Column("canonical_key", sa.String(length=160), nullable=True))
    op.execute(
        "UPDATE quiz_items "
        "SET canonical_key = 'legacy:' || CAST(id AS TEXT) "
        "WHERE canonical_key IS NULL"
    )
    op.alter_column("quiz_items", "canonical_key", nullable=False)
    op.create_index("uq_quiz_items_canonical_key", "quiz_items", ["canonical_key"], unique=True)

    op.add_column(
        "quiz_items",
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "quiz_items",
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "quiz_items",
        sa.Column("review_status", sa.String(length=40), nullable=False, server_default="pre-generated"),
    )
    op.add_column(
        "quiz_items",
        sa.Column("source_status", sa.String(length=32), nullable=False, server_default="legacy-migrated"),
    )
    op.create_check_constraint(
        "ck_quiz_items_difficulty", "quiz_items", "difficulty BETWEEN 1 AND 5"
    )
    op.create_check_constraint(
        "ck_quiz_items_answer_nonempty", "quiz_items", "length(trim(answer)) > 0"
    )
    op.create_check_constraint(
        "ck_quiz_items_content_version", "quiz_items", "content_version >= 1"
    )
    op.create_check_constraint(
        "ck_quiz_items_review_status",
        "quiz_items",
        "review_status IN ('draft','pre-generated','curated',"
        "'codex-reviewed-pending-human','rejected','withdrawn')",
    )
    op.create_check_constraint(
        "ck_quiz_items_source_status",
        "quiz_items",
        "source_status IN ('seeded','curated','generated','imported','legacy-migrated')",
    )
    op.alter_column("quiz_items", "content_version", server_default=None)
    op.alter_column("quiz_items", "explanation", server_default=None)
    op.alter_column("quiz_items", "review_status", server_default=None)
    op.alter_column("quiz_items", "source_status", server_default=None)

    op.create_table(
        "quiz_item_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("quiz_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("citation_label", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["quiz_item_id"], ["quiz_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("quiz_item_id", "chunk_id", name="uq_quiz_item_evidences_item_chunk"),
    )
    op.create_index("ix_quiz_item_evidences_quiz_item_id", "quiz_item_evidences", ["quiz_item_id"])
    op.create_index("ix_quiz_item_evidences_chunk_id", "quiz_item_evidences", ["chunk_id"])

    op.create_table(
        "quiz_quality_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("quiz_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validator_version", sa.String(length=64), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("item_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("failure_codes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("result IN ('pending','passed','failed')", name="ck_quiz_quality_reports_result"),
        sa.ForeignKeyConstraint(["quiz_item_id"], ["quiz_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "quiz_item_id",
            "validator_version",
            "input_fingerprint",
            name="uq_quiz_quality_reports_reproducible_run",
        ),
    )
    op.create_index("ix_quiz_quality_reports_quiz_item_id", "quiz_quality_reports", ["quiz_item_id"])
    op.create_index(
        "ix_quiz_quality_reports_item_reviewed",
        "quiz_quality_reports",
        ["quiz_item_id", "reviewed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_quiz_quality_reports_item_reviewed", table_name="quiz_quality_reports")
    op.drop_index("ix_quiz_quality_reports_quiz_item_id", table_name="quiz_quality_reports")
    op.drop_table("quiz_quality_reports")

    op.drop_index("ix_quiz_item_evidences_chunk_id", table_name="quiz_item_evidences")
    op.drop_index("ix_quiz_item_evidences_quiz_item_id", table_name="quiz_item_evidences")
    op.drop_table("quiz_item_evidences")

    op.drop_constraint("ck_quiz_items_source_status", "quiz_items", type_="check")
    op.drop_constraint("ck_quiz_items_review_status", "quiz_items", type_="check")
    op.drop_constraint("ck_quiz_items_content_version", "quiz_items", type_="check")
    op.drop_constraint("ck_quiz_items_answer_nonempty", "quiz_items", type_="check")
    op.drop_constraint("ck_quiz_items_difficulty", "quiz_items", type_="check")
    op.drop_column("quiz_items", "source_status")
    op.drop_column("quiz_items", "review_status")
    op.drop_column("quiz_items", "explanation")
    op.drop_column("quiz_items", "content_version")
    op.drop_index("uq_quiz_items_canonical_key", table_name="quiz_items")
    op.drop_column("quiz_items", "canonical_key")
