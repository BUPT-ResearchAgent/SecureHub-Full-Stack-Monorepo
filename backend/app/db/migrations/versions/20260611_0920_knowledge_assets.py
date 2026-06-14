# Status: [planned]

"""data-layer v2: knowledge assets

Revision ID: 20260611_0920
Revises: 20260611_0910
Create Date: 2026-06-11 09:20:00

Touches the unified knowledge asset layer:

- ``documents``: relax ``raw_text`` to NULL, add ``content_hash`` + ``status``
- ``chunks``: relax ``embedding`` to NULL, add ``embedding_status`` /
  ``token_count`` / UNIQUE(document_id, chunk_index)
- create ``document_assets``
- rename ``knowledge_points`` → ``knowledge_nodes`` and add
  ``domain`` / ``node_type`` / ``metadata`` so non-course domains can use it
- drop legacy ``kp_prerequisites`` (its 2-col PK widens), create
  ``knowledge_edges`` with PK ``(source_id, target_id, edge_type)``
- on PostgreSQL: HNSW (fallback IVFFlat) on ``chunks.embedding`` + GIN on
  ``documents.metadata`` / ``chunks.metadata``
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260611_0920"
down_revision: str | None = "20260611_0910"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ------- documents: relax raw_text, add content_hash + status -------
    with op.batch_alter_table("documents") as batch:
        batch.alter_column("raw_text", existing_type=sa.Text(), nullable=True)
        batch.add_column(sa.Column("content_hash", sa.String(length=128), nullable=True))
        batch.add_column(
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            )
        )
        # v1 init forgot the standard ``created_at`` / ``updated_at`` pair —
        # v2 Document ORM extends ``TimestampMixin`` which selects them.
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )

    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_domain_status", "documents", ["domain", "status"])

    # ------- chunks: relax embedding, add embedding_status + token_count -------
    with op.batch_alter_table("chunks") as batch:
        batch.alter_column(
            "embedding",
            existing_type=sa.LargeBinary() if not is_pg else None,
            nullable=True,
        )
        batch.add_column(sa.Column("token_count", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "embedding_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            )
        )
        # v1 omitted the standard timestamps — Chunk now extends TimestampMixin.
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch.create_unique_constraint(
            "uq_chunks_document_index", ["document_id", "chunk_index"]
        )

    op.create_index(
        "ix_chunks_domain_embedding_status",
        "chunks",
        ["domain", "embedding_status"],
    )

    # ------- document_assets (new) -------
    op.create_table(
        "document_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asset_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True, index=True),
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

    # ------- knowledge_points -> knowledge_nodes (rename + extend) -------
    # On PostgreSQL ``rename_table`` keeps every FK string (quiz_items.kp_id,
    # learning_events.kp_id, kp_prerequisites) pointing at the new name. On
    # SQLite, FK enforcement is off by default so the stale FK reference is
    # harmless until the table is rebuilt later.
    op.rename_table("knowledge_points", "knowledge_nodes")
    with op.batch_alter_table("knowledge_nodes") as batch:
        batch.add_column(
            sa.Column(
                "domain",
                sa.String(length=64),
                nullable=False,
                server_default="course_websec",
            )
        )
        batch.add_column(
            sa.Column(
                "node_type",
                sa.String(length=64),
                nullable=False,
                server_default="concept",
            )
        )
        batch.add_column(
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.alter_column("level", existing_type=sa.Integer(), nullable=True)
        batch.alter_column(
            "course_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )

    op.create_index("ix_knowledge_nodes_domain", "knowledge_nodes", ["domain"])
    op.create_index("ix_knowledge_nodes_course_id", "knowledge_nodes", ["course_id"])

    # ------- kp_prerequisites -> knowledge_edges (drop + recreate) -------
    op.drop_table("kp_prerequisites")
    op.create_table(
        "knowledge_edges",
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("edge_type", sa.String(length=64), primary_key=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.CheckConstraint(
            "source_id != target_id", name="ck_knowledge_edges_no_self_loop"
        ),
    )

    # ------- PG-only: HNSW + GIN indexes -------
    if is_pg:
        # HNSW is pgvector >= 0.5.0; older builds raise → fall back to IVFFlat.
        try:
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        except Exception:  # pragma: no cover — environment-dependent
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat "
                "ON chunks USING ivfflat (embedding vector_cosine_ops) "
                "WITH (lists = 100)"
            )
        op.create_index(
            "idx_documents_metadata_gin",
            "documents",
            ["metadata"],
            postgresql_using="gin",
        )
        op.create_index(
            "idx_chunks_metadata_gin",
            "chunks",
            ["metadata"],
            postgresql_using="gin",
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        for name in (
            "idx_chunks_metadata_gin",
            "idx_documents_metadata_gin",
            "idx_chunks_embedding_ivfflat",
            "idx_chunks_embedding_hnsw",
        ):
            op.execute(f"DROP INDEX IF EXISTS {name}")

    op.drop_table("knowledge_edges")
    op.create_table(
        "kp_prerequisites",
        sa.Column(
            "kp_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "prereq_kp_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.CheckConstraint("kp_id != prereq_kp_id", name="ck_kp_prereq_no_self_loop"),
    )

    op.drop_index("ix_knowledge_nodes_course_id", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_domain", table_name="knowledge_nodes")
    with op.batch_alter_table("knowledge_nodes") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("metadata")
        batch.drop_column("node_type")
        batch.drop_column("domain")
    op.rename_table("knowledge_nodes", "knowledge_points")

    op.drop_table("document_assets")

    op.drop_index("ix_chunks_domain_embedding_status", table_name="chunks")
    with op.batch_alter_table("chunks") as batch:
        batch.drop_constraint("uq_chunks_document_index", type_="unique")
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("embedding_status")
        batch.drop_column("token_count")

    op.drop_index("ix_documents_domain_status", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("status")
        batch.drop_column("content_hash")
