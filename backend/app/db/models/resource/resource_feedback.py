# Status: real

"""Student resource feedback records linked to the existing artifact lineage."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResourceFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A structured learner request whose terminal effect is reconciled from a real run."""

    __tablename__ = "resource_feedback"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted','retry_requested','regenerated','provider_unavailable','failed','rejected')",
            name="ck_resource_feedback_status",
        ),
        Index("ix_resource_feedback_student_course_status", "student_id", "course_id", "status"),
    )

    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generated_resources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    kp_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="RESTRICT"),
        index=True,
    )
    recommendation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_resource_recommendations.id", ondelete="RESTRICT"),
        index=True,
    )
    follow_up_recommendation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_resource_recommendations.id", ondelete="RESTRICT"),
        index=True,
    )
    retry_workflow_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    resulting_resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generated_resources.id", ondelete="RESTRICT"),
        index=True,
    )
    feedback_kinds: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="submitted")
    outcome: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


__all__ = ["ResourceFeedback"]
