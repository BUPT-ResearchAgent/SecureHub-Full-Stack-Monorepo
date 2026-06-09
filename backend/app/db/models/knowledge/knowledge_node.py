# Status: [planned]

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Generic knowledge graph node — supersedes v1 ``knowledge_points`` and
    extends it with ``domain`` + ``node_type`` so course concepts, job skills,
    policy topics, fund directions, etc. all share one graph table.
    """

    __tablename__ = "knowledge_nodes"

    domain: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    course_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    node_type: Mapped[str] = mapped_column(String(64), default="concept", nullable=False)
    level: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
