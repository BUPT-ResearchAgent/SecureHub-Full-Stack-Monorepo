# Status: real

"""Create T5 password-policy and redacted API-risk governance state.

Revision ID: 20260715_1084
Revises: 20260715_1083
Create Date: 2026-07-15 18:20:00

No table in this revision stores a password, hash copy, Authorization header,
Cookie, token, raw request payload, full IP address, or raw device value.
Existing ``users`` remains the only password-hash location; policy compliance
is a version/state overlay and API request audit values are hashed or bucketed.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1084"
down_revision: str | None = "20260715_1083"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"securehub:{name}"))


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "password_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("rules_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_password_policies_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("version_no", name="uq_password_policies_version"),
    )
    op.create_index("ix_password_policies_created_by", "password_policies", ["created_by"])
    op.create_index(
        "uq_password_policies_one_active",
        "password_policies",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "account_password_compliance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluated_policy_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="remediation_required"),
        sa.Column("remediation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remediated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exemption_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exemption_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('compliant','remediation_required','remediated','temporarily_exempt')",
            name="ck_account_password_compliance_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", name="uq_account_password_compliance_user"),
    )
    op.create_index("ix_account_password_compliance_user_id", "account_password_compliance", ["user_id"])
    op.create_index("ix_account_password_compliance_updated_by", "account_password_compliance", ["updated_by"])

    op.create_table(
        "api_request_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("route_template", sa.String(length=256), nullable=False),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("outcome_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("device_hash", sa.String(length=128), nullable=True),
        sa.Column("rate_bucket", sa.String(length=64), nullable=False),
        sa.Column("request_size_bucket", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("redaction_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("outcome_status >= 0 AND outcome_status <= 599", name="ck_api_request_audit_events_status"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_api_request_audit_events_occurred_at", ["occurred_at"]),
        ("ix_api_request_audit_events_actor_user_id", ["actor_user_id"]),
        ("ix_api_request_audit_events_ip_hash", ["ip_hash"]),
        ("ix_api_request_audit_events_device_hash", ["device_hash"]),
        ("ix_api_request_audit_events_correlation_id", ["correlation_id"]),
        ("ix_api_request_audit_events_expires_at", ["expires_at"]),
        ("ix_api_request_audit_events_occurred_route", ["occurred_at", "route_template"]),
        ("ix_api_request_audit_events_ip_time", ["ip_hash", "occurred_at"]),
        ("ix_api_request_audit_events_device_time", ["device_hash", "occurred_at"]),
        ("ix_api_request_audit_events_actor_time", ["actor_user_id", "occurred_at"]),
    ):
        op.create_index(name, "api_request_audit_events", columns)

    op.create_table(
        "api_risk_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("predicate", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("scope IN ('user','ip','device','api')", name="ck_api_risk_rules_scope"),
        sa.CheckConstraint("action IN ('alert','throttle','block')", name="ck_api_risk_rules_action"),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_api_risk_rules_status"),
        sa.CheckConstraint("threshold > 0", name="ck_api_risk_rules_threshold"),
        sa.CheckConstraint("window_seconds > 0", name="ck_api_risk_rules_window"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", "version_no", name="uq_api_risk_rules_code_version"),
    )
    op.create_index("ix_api_risk_rules_created_by", "api_risk_rules", ["created_by"])
    op.create_index(
        "uq_api_risk_rules_active_code",
        "api_risk_rules",
        ["code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "api_risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("request_audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("baseline_version", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_api_risk_events_severity"),
        sa.CheckConstraint("decision IN ('allow','throttle','block','released')", name="ck_api_risk_events_decision"),
        sa.CheckConstraint(
            "status IN ('observed','alerted','mitigated','released','false_positive')",
            name="ck_api_risk_events_status",
        ),
        sa.ForeignKeyConstraint(["request_audit_id"], ["api_request_audit_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rule_id"], ["api_risk_rules.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_api_risk_events_request_audit_id", ["request_audit_id"]),
        ("ix_api_risk_events_rule_id", ["rule_id"]),
        ("ix_api_risk_events_opened_at", ["opened_at"]),
        ("ix_api_risk_events_status_opened", ["status", "opened_at"]),
    ):
        op.create_index(name, "api_risk_events", columns)

    op.create_table(
        "api_risk_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("risk_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=24), nullable=False, server_default="automatic"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('alert','throttle','block','release','review')", name="ck_api_risk_actions_action"),
        sa.CheckConstraint(
            "result IN ('automatic','succeeded','false_positive','false_negative','confirmed')",
            name="ck_api_risk_actions_result",
        ),
        sa.ForeignKeyConstraint(["risk_event_id"], ["api_risk_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_api_risk_actions_risk_event_id", ["risk_event_id"]),
        ("ix_api_risk_actions_actor_user_id", ["actor_user_id"]),
        ("ix_api_risk_actions_event_created", ["risk_event_id", "created_at"]),
    ):
        op.create_index(name, "api_risk_actions", columns)

    op.bulk_insert(
        sa.table(
            "password_policies",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("version_no", sa.Integer()),
            sa.column("rules_json", postgresql.JSONB()),
            sa.column("status", sa.String()),
            sa.column("note", sa.Text()),
        ),
        [
            {
                "id": _stable_id("password-policy:v1"),
                "version_no": 1,
                "rules_json": {
                    "min_length": 8,
                    "max_length": 72,
                    "require_upper": True,
                    "require_lower": True,
                    "require_digit": True,
                    "require_symbol": True,
                },
                "status": "active",
                "note": "T5 基线策略；旧账号只按合规记录版本进入整改，不扫描哈希。",
            }
        ],
    )
    op.bulk_insert(
        sa.table(
            "api_risk_rules",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("code", sa.String()),
            sa.column("version_no", sa.Integer()),
            sa.column("scope", sa.String()),
            sa.column("predicate", postgresql.JSONB()),
            sa.column("threshold", sa.Integer()),
            sa.column("window_seconds", sa.Integer()),
            sa.column("action", sa.String()),
            sa.column("status", sa.String()),
        ),
        [
            {
                "id": _stable_id("api-risk-rule:auth-ip-burst:v1"),
                "code": "auth-ip-burst",
                "version_no": 1,
                "scope": "ip",
                "predicate": {"route_prefix": "/api/v1/auth", "method": "POST"},
                "threshold": 20,
                "window_seconds": 60,
                "action": "throttle",
                "status": "active",
            }
        ],
    )


def downgrade() -> None:
    for name in (
        "ix_api_risk_actions_event_created",
        "ix_api_risk_actions_actor_user_id",
        "ix_api_risk_actions_risk_event_id",
    ):
        op.drop_index(name, table_name="api_risk_actions")
    op.drop_table("api_risk_actions")

    for name in (
        "ix_api_risk_events_status_opened",
        "ix_api_risk_events_opened_at",
        "ix_api_risk_events_rule_id",
        "ix_api_risk_events_request_audit_id",
    ):
        op.drop_index(name, table_name="api_risk_events")
    op.drop_table("api_risk_events")

    op.drop_index("uq_api_risk_rules_active_code", table_name="api_risk_rules")
    op.drop_index("ix_api_risk_rules_created_by", table_name="api_risk_rules")
    op.drop_table("api_risk_rules")

    for name in (
        "ix_api_request_audit_events_actor_time",
        "ix_api_request_audit_events_device_time",
        "ix_api_request_audit_events_ip_time",
        "ix_api_request_audit_events_occurred_route",
        "ix_api_request_audit_events_expires_at",
        "ix_api_request_audit_events_correlation_id",
        "ix_api_request_audit_events_device_hash",
        "ix_api_request_audit_events_ip_hash",
        "ix_api_request_audit_events_actor_user_id",
        "ix_api_request_audit_events_occurred_at",
    ):
        op.drop_index(name, table_name="api_request_audit_events")
    op.drop_table("api_request_audit_events")

    op.drop_index("ix_account_password_compliance_updated_by", table_name="account_password_compliance")
    op.drop_index("ix_account_password_compliance_user_id", table_name="account_password_compliance")
    op.drop_table("account_password_compliance")

    op.drop_index("uq_password_policies_one_active", table_name="password_policies")
    op.drop_index("ix_password_policies_created_by", table_name="password_policies")
    op.drop_table("password_policies")
