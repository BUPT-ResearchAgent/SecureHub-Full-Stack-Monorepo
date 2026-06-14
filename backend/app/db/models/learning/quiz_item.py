# Status: [planned]

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class QuizItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quiz_items"
    __table_args__ = (
        CheckConstraint(
            "type IN ('single_choice','multi_choice','fill','short_answer','code')",
            name="ck_quiz_items_type",
        ),
    )

    # v2: kp_id now references knowledge_nodes.
    kp_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id"),
        index=True,
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by_skill: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_skills.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
