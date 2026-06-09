# Status: [planned]

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QuizAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single user submission for one ``quiz_items`` row. Feeds the assessment
    loop (``outcome_evaluator.run_assessment``) and the capability radar chart.
    """

    __tablename__ = "quiz_attempts"

    quiz_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    submitted_answer: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
