# Status: [planned]

from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeEdge(Base):
    """Directed, typed edge between two ``knowledge_nodes`` rows. Supersedes v1
    ``kp_prerequisites`` whose two-column PK is widened to
    ``(source_id, target_id, edge_type)``.
    """

    __tablename__ = "knowledge_edges"
    __table_args__ = (
        CheckConstraint("source_id != target_id", name="ck_knowledge_edges_no_self_loop"),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    edge_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
