# Status: [planned]

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearningTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """P1 extension: a node inside a ``learning_paths`` DAG. Each task can be
    bound to a ``knowledge_nodes`` row to anchor recommended resources.
    """

    __tablename__ = "learning_tasks"

    path_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="todo", index=True, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
