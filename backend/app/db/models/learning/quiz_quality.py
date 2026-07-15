# Status: real

"""Durable evidence bindings and reproducible quality reports for quiz items.

Both tables reference existing learning and knowledge authorities.  They do
not duplicate question text, knowledge-node content, chunks, users, courses,
or learner profiles.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class QuizItemEvidence(UUIDPrimaryKeyMixin, Base):
    """An evidence citation from one question to an existing knowledge chunk."""

    __tablename__ = "quiz_item_evidences"
    __table_args__ = (
        UniqueConstraint("quiz_item_id", "chunk_id", name="uq_quiz_item_evidences_item_chunk"),
    )

    quiz_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    citation_label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuizQualityReport(UUIDPrimaryKeyMixin, Base):
    """Per-item result of a versioned deterministic WebSec quality run."""

    __tablename__ = "quiz_quality_reports"
    __table_args__ = (
        CheckConstraint("result IN ('pending','passed','failed')", name="ck_quiz_quality_reports_result"),
        UniqueConstraint(
            "quiz_item_id",
            "validator_version",
            "input_fingerprint",
            name="uq_quiz_quality_reports_reproducible_run",
        ),
        Index("ix_quiz_quality_reports_item_reviewed", "quiz_item_id", "reviewed_at"),
    )

    quiz_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    item_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_codes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Automated validation is deliberately not a human review.  An optional
    # actor can be added only by a later explicit human-review workflow.
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
