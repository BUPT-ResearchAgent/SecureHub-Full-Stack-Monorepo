# Status: [planned]

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class LearningEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_events"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # v2: kp_id now references knowledge_nodes (the table v1 knowledge_points
    # was renamed into); kept ``kp_id`` as column name for backward compatibility
    # with existing reducers / repositories.
    kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id"),
    )
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
