# Status: real

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
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
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_quiz_items_difficulty"),
        CheckConstraint("length(trim(answer)) > 0", name="ck_quiz_items_answer_nonempty"),
        CheckConstraint("content_version >= 1", name="ck_quiz_items_content_version"),
        CheckConstraint(
            "review_status IN ('draft','pre-generated','curated',"
            "'codex-reviewed-pending-human','rejected','withdrawn')",
            name="ck_quiz_items_review_status",
        ),
        CheckConstraint(
            "source_status IN ('seeded','curated','generated','imported','legacy-migrated')",
            name="ck_quiz_items_source_status",
        ),
        Index("uq_quiz_items_canonical_key", "canonical_key", unique=True),
    )

    # v2: kp_id now references knowledge_nodes.
    kp_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id"),
        index=True,
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(160), nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="pre-generated"
    )
    source_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="legacy-migrated"
    )
    generated_by_skill: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_skills.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
