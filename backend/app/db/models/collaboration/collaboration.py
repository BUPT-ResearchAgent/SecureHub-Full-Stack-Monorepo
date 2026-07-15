# Status: real

"""Durable collaboration records for signals, course updates, and messages.

The models retain references to existing documents, knowledge nodes, users,
courses, and Runtime evidence.  They deliberately do not reuse Runtime's
``agent_messages`` transcript table for interpersonal communication.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExternalSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An evidence-bound output of one fixed policy, hot, or job Skill."""

    __tablename__ = "external_signals"
    __table_args__ = (
        CheckConstraint("kind IN ('policy','hot','job')", name="ck_external_signals_kind"),
        CheckConstraint(
            "status IN ('ingested','validated','rejected','expired')",
            name="ck_external_signals_status",
        ),
        UniqueConstraint("kind", "source_fingerprint", name="uq_external_signals_kind_fingerprint"),
    )

    source_document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_evidence_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ingested")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CourseUpdateSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned proposal; accepting it never mutates the course row."""

    __tablename__ = "course_update_suggestions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','pending_teacher_decision','adopted','rejected','superseded','withdrawn')",
            name="ck_course_update_suggestions_status",
        ),
        UniqueConstraint(
            "course_id", "signal_id", "version_no", name="uq_course_update_suggestions_course_signal_version"
        ),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_signals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_evidence_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending_teacher_decision", index=True
    )


class CourseUpdateImpact(UUIDPrimaryKeyMixin, Base):
    """A suggestion's reference to an existing course knowledge node."""

    __tablename__ = "course_update_impacts"
    __table_args__ = (
        CheckConstraint(
            "impact_type IN ('add','revise','retire','emphasize')",
            name="ck_course_update_impacts_type",
        ),
        UniqueConstraint(
            "suggestion_id", "knowledge_node_id", "impact_type",
            name="uq_course_update_impacts_suggestion_node_type",
        ),
    )

    suggestion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_update_suggestions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    knowledge_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    impact_type: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class CourseUpdateDecision(UUIDPrimaryKeyMixin, Base):
    """A teacher's explicit, auditable decision on one update proposal."""

    __tablename__ = "course_update_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('adopt','reject')", name="ck_course_update_decisions_decision"),
        UniqueConstraint("suggestion_id", name="uq_course_update_decisions_suggestion"),
    )

    suggestion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_update_suggestions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-to-user message or announcement; never a Runtime transcript."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('course','class','individual')", name="ck_messages_scope_type"
        ),
        CheckConstraint(
            "safety_state IN ('accepted','rejected')", name="ck_messages_safety_state"
        ),
        CheckConstraint(
            "status IN ('draft','sent','partially_delivered','recalled','expired')",
            name="ck_messages_status",
        ),
        CheckConstraint(
            "(scope_type = 'course' AND course_id IS NOT NULL AND teaching_class_id IS NULL AND target_user_id IS NULL) "
            "OR (scope_type = 'class' AND course_id IS NOT NULL AND teaching_class_id IS NOT NULL AND target_user_id IS NULL) "
            "OR (scope_type = 'individual' AND course_id IS NOT NULL AND teaching_class_id IS NULL AND target_user_id IS NOT NULL)",
            name="ck_messages_scope_shape",
        ),
        UniqueConstraint("sender_user_id", "idempotency_key", name="uq_messages_sender_idempotency"),
    )

    sender_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teaching_class_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teaching_classes.id", ondelete="RESTRICT"),
        index=True,
    )
    target_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    safety_state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="accepted")
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="draft", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    recall_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recalled_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    recall_reason: Mapped[str | None] = mapped_column(Text)


class MessageDelivery(UUIDPrimaryKeyMixin, Base):
    """Per-recipient durable delivery and read state."""

    __tablename__ = "message_deliveries"
    __table_args__ = (
        CheckConstraint(
            "delivery_state IN ('unread','read','recalled')", name="ck_message_deliveries_state"
        ),
        UniqueConstraint("message_id", "recipient_user_id", name="uq_message_deliveries_message_recipient"),
        Index("ix_message_deliveries_recipient_state", "recipient_user_id", "delivery_state"),
    )

    message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    delivery_state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="unread")
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
