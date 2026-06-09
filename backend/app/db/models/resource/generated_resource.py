# Status: [planned]

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedResource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single landing table for every A3 learning artefact: course doc, PPT,
    mindmap, quiz set, hands-on lab, video storyboard, reading list,
    assessment report. ``evidence_chunk_ids`` and ``agent_run_id`` carry the
    citation chain back to RAG and the agent run that produced it.
    """

    __tablename__ = "generated_resources"

    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    course_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("courses.id"), index=True)
    kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id"),
        index=True,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    object_key: Mapped[str | None] = mapped_column(Text)
    evidence_chunk_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)).with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )
    quality_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
