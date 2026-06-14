# Status: [planned]

"""data-layer v2: generated resources & storage

Revision ID: 20260611_0950
Revises: 20260611_0940
Create Date: 2026-06-11 09:50:00

Creates the two terminal tables of the v2 asset pipeline:

- ``generated_resources``: the single landing table for every A3 learning
  artefact (course doc / PPT / mindmap / quiz set / hands-on lab / video
  storyboard / reading list / assessment report) with citation chain back to
  ``agent_runs`` + ``evidence_chunk_ids``;
- ``storage_objects``: provider-agnostic file handle (local / minio / s3 /
  oss / cos / r2). P0 uses ``provider='local'``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260611_0950"
down_revision: str | None = "20260611_0940"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "kp_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("resource_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column(
            "evidence_chunk_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="ready",
            index=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_generated_resources_user_course_type",
        "generated_resources",
        ["user_id", "course_id", "resource_type"],
    )

    op.create_table(
        "storage_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider",
            sa.String(length=32),
            nullable=False,
            server_default="local",
        ),
        sa.Column("bucket", sa.String(length=128), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=False, unique=True),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="ready",
            index=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("storage_objects")
    op.drop_index(
        "ix_generated_resources_user_course_type",
        table_name="generated_resources",
    )
    op.drop_table("generated_resources")
