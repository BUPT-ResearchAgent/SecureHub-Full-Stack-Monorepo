# Status: real

"""T5 account-policy and redacted API-risk persistence.

The models deliberately never contain a password, password hash, bearer
credential, Cookie, raw device identifier, raw IP address, or request payload.
Identity remains authoritative in ``users`` and business audits remain in the
existing append-only ``governance_audit_events`` table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PasswordPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned validation rules; user hashes stay exclusively on ``users``."""

    __tablename__ = "password_policies"
    __table_args__ = (
        CheckConstraint("status IN ('draft','active','retired')", name="ck_password_policies_status"),
        UniqueConstraint("version_no", name="uq_password_policies_version"),
        Index(
            "uq_password_policies_one_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class AccountPasswordCompliance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-account policy-version state without password material."""

    __tablename__ = "account_password_compliance"
    __table_args__ = (
        CheckConstraint(
            "status IN ('compliant','remediation_required','remediated','temporarily_exempt')",
            name="ck_account_password_compliance_status",
        ),
        UniqueConstraint("user_id", name="uq_account_password_compliance_user"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Zero means this legacy account has not supplied a plaintext password
    # while the active policy existed.  It never means a hash was inspected.
    evaluated_policy_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="remediation_required")
    remediation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remediated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exemption_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    exemption_reason: Mapped[str | None] = mapped_column(Text)


class ApiRequestAuditEvent(UUIDPrimaryKeyMixin, Base):
    """One redacted request observation; never a request-body or header log."""

    __tablename__ = "api_request_audit_events"
    __table_args__ = (
        CheckConstraint("outcome_status >= 0 AND outcome_status <= 599", name="ck_api_request_audit_events_status"),
        Index("ix_api_request_audit_events_occurred_route", "occurred_at", "route_template"),
        Index("ix_api_request_audit_events_ip_time", "ip_hash", "occurred_at"),
        Index("ix_api_request_audit_events_device_time", "device_hash", "occurred_at"),
        Index("ix_api_request_audit_events_actor_time", "actor_user_id", "occurred_at"),
    )

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    route_template: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(12), nullable=False)
    outcome_status: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    ip_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    device_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    rate_bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    request_size_bucket: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    redaction_version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="v1")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ApiRiskRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned threshold/baseline rule applied to redacted audit events."""

    __tablename__ = "api_risk_rules"
    __table_args__ = (
        CheckConstraint("scope IN ('user','ip','device','api')", name="ck_api_risk_rules_scope"),
        CheckConstraint("action IN ('alert','throttle','block')", name="ck_api_risk_rules_action"),
        CheckConstraint("status IN ('draft','active','retired')", name="ck_api_risk_rules_status"),
        CheckConstraint("threshold > 0", name="ck_api_risk_rules_threshold"),
        CheckConstraint("window_seconds > 0", name="ck_api_risk_rules_window"),
        UniqueConstraint("code", "version_no", name="uq_api_risk_rules_code_version"),
        Index(
            "uq_api_risk_rules_active_code",
            "code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(96), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    predicate: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiRiskEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An explainable decision derived from a redacted request and rule."""

    __tablename__ = "api_risk_events"
    __table_args__ = (
        CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_api_risk_events_severity"),
        CheckConstraint("decision IN ('allow','throttle','block','released')", name="ck_api_risk_events_decision"),
        CheckConstraint(
            "status IN ('observed','alerted','mitigated','released','false_positive')",
            name="ck_api_risk_events_status",
        ),
        Index("ix_api_risk_events_status_opened", "status", "opened_at"),
    )

    request_audit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("api_request_audit_events.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("api_risk_rules.id", ondelete="RESTRICT"), index=True
    )
    baseline_version: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ApiRiskAction(UUIDPrimaryKeyMixin, Base):
    """Automated or human disposition/replay record for one risk event."""

    __tablename__ = "api_risk_actions"
    __table_args__ = (
        CheckConstraint("action IN ('alert','throttle','block','release','review')", name="ck_api_risk_actions_action"),
        CheckConstraint(
            "result IN ('automatic','succeeded','false_positive','false_negative','confirmed')",
            name="ck_api_risk_actions_result",
        ),
        Index("ix_api_risk_actions_event_created", "risk_event_id", "created_at"),
    )

    risk_event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("api_risk_events.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False, server_default="automatic")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
