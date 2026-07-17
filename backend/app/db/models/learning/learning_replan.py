# Status: real

"""Durable learner-owned path versioning and recommendation records.

These rows extend the existing ``learning_paths`` / ``learning_tasks``
authority.  A replan always creates a new path and immutable version record;
completed work remains attached to its historical path instead of being
overwritten by a recommendation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearningPathVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable view of one learner path at a durable decision boundary."""

    __tablename__ = "learning_path_versions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('active','historical')",
            name="ck_learning_path_versions_state",
        ),
        CheckConstraint(
            "kind IN ('baseline','replan','revert')",
            name="ck_learning_path_versions_kind",
        ),
        UniqueConstraint(
            "user_id", "course_id", "version_no",
            name="uq_learning_path_versions_user_course_version",
        ),
        Index("ix_learning_path_versions_user_course_state", "user_id", "course_id", "state"),
    )

    path_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
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
    parent_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    trigger_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_events.id", ondelete="RESTRICT"),
        index=True,
    )
    trigger_workflow_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="baseline")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    task_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class LearningPathReplanCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A computed but student-unapproved path change proposal."""

    __tablename__ = "learning_path_replan_candidates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','deferred','accepted','reverted','expired')",
            name="ck_learning_path_replan_candidates_status",
        ),
        CheckConstraint("expected_minutes >= 0", name="ck_learning_path_replan_candidates_minutes"),
        UniqueConstraint(
            "student_id", "course_id", "input_fingerprint",
            name="uq_learning_path_replan_candidates_input",
        ),
        Index("ix_learning_path_replan_candidates_student_course_status", "student_id", "course_id", "status"),
    )

    student_id: Mapped[UUID] = mapped_column(
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
    source_path_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    accepted_path_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    trigger_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_events.id", ondelete="RESTRICT"),
        index=True,
    )
    trigger_workflow_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    affected_kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="RESTRICT"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proposed_task_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    recommendation_plan: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class LearningPathDecision(UUIDPrimaryKeyMixin, Base):
    """Append-only student decision audit for a replan candidate."""

    __tablename__ = "learning_path_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accept','defer','revert')",
            name="ck_learning_path_decisions_decision",
        ),
        Index("ix_learning_path_decisions_candidate_created", "candidate_id", "created_at"),
    )

    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_replan_candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    source_path_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resulting_path_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
    )
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CourseResourceRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A student-specific downstream push derived from a path decision or feedback."""

    __tablename__ = "course_resource_recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled','accepted','deferred','rejected','superseded','feedback_received','completed')",
            name="ck_course_resource_recommendations_status",
        ),
        Index("ix_course_resource_recommendations_student_course_status", "student_id", "course_id", "status"),
    )

    student_id: Mapped[UUID] = mapped_column(
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
    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generated_resources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="RESTRICT"),
        index=True,
    )
    path_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    source_candidate_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_path_replan_candidates.id", ondelete="RESTRICT"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled")
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    match_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = [
    "CourseResourceRecommendation",
    "LearningPathDecision",
    "LearningPathReplanCandidate",
    "LearningPathVersion",
]
