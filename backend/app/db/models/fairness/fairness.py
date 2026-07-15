# Status: real

"""Consent-gated, aggregate-only educational fairness records.

These tables deliberately reference existing users and T3 assessment-grade
decisions.  They contain no protected attribute columns, do not copy scores,
and cannot express a punitive action against an individual.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FairnessPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned purpose, consent, retention, and threshold boundary."""

    __tablename__ = "fairness_policies"
    __table_args__ = (
        CheckConstraint("status IN ('draft','active','retired')", name="ck_fairness_policies_status"),
        CheckConstraint("minimum_sample > 0", name="ck_fairness_policies_minimum_sample"),
        CheckConstraint("retention_days > 0", name="ck_fairness_policies_retention_days"),
        UniqueConstraint("code", "version_no", name="uq_fairness_policies_code_version"),
        Index(
            "uq_fairness_policies_active_code",
            "code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(96), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_group_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    minimum_sample: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    pass_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="60")
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="90")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FairnessConsent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A participant's revocable, scoped consent for one policy."""

    __tablename__ = "fairness_consents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('granted','withdrawn','expired')", name="ck_fairness_consents_status"
        ),
        UniqueConstraint("user_id", "policy_id", "scope", name="uq_fairness_consents_user_policy_scope"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_policies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False, server_default="assessment_fairness")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="granted")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FairnessGroupAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Minimal non-sensitive grouping, usable only with a live consent."""

    __tablename__ = "fairness_group_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "policy_id", "group_key", name="uq_fairness_group_assignment"),
        Index("ix_fairness_group_assignments_policy_key", "policy_id", "group_key"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_policies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)
    minimal_group_value: Mapped[str] = mapped_column(String(96), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class FairnessMetricRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reproducible aggregate run over published T3 final grades only."""

    __tablename__ = "fairness_metric_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','completed','insufficient_sample','rejected')",
            name="ck_fairness_metric_runs_status",
        ),
        Index("ix_fairness_metric_runs_policy_finished", "policy_id", "finished_at"),
    )

    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_policies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assessment_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    dataset_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    rejection_code: Mapped[str | None] = mapped_column(String(64))
    limitations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    initiated_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FairnessMetricCell(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One aggregate group statistic; no individual score is persisted here."""

    __tablename__ = "fairness_metric_cells"
    __table_args__ = (
        UniqueConstraint("run_id", "group_key", "group_value", name="uq_fairness_metric_cells_group"),
        CheckConstraint("sample_size > 0", name="ck_fairness_metric_cells_sample_size"),
        Index("ix_fairness_metric_cells_run", "run_id"),
    )

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_metric_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)
    group_value: Mapped[str] = mapped_column(String(96), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_score: Mapped[float] = mapped_column(Float, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float)
    fpr: Mapped[float | None] = mapped_column(Float)
    fnr: Mapped[float | None] = mapped_column(Float)
    equal_opportunity_delta: Mapped[float | None] = mapped_column(Float)
    confidence_interval: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    limitations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FairnessAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Human-review prompt only; it cannot affect a grade or account."""

    __tablename__ = "fairness_alerts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','under_review','resolved','dismissed')",
            name="ck_fairness_alerts_status",
        ),
        CheckConstraint("severity IN ('low','medium','high')", name="ck_fairness_alerts_severity"),
        Index("ix_fairness_alerts_status_opened", "status", "opened_at"),
    )

    metric_cell_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_metric_cells.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    alert_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FairnessReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reasoned human disposition of a fairness alert."""

    __tablename__ = "fairness_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('under_review','resolved','dismissed')",
            name="ck_fairness_reviews_status",
        ),
        Index("ix_fairness_reviews_alert_reviewed", "alert_id", "reviewed_at"),
    )

    alert_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fairness_alerts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FairnessAppeal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A student request for human explanation, never an automatic regrade."""

    __tablename__ = "fairness_appeals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted','reviewing','resolved','closed')",
            name="ck_fairness_appeals_status",
        ),
        Index("ix_fairness_appeals_appellant_status", "appellant_user_id", "status"),
    )

    grade_decision_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_grade_decisions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    appellant_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="submitted")
    reviewer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    response_note: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
