# Status: real

"""Create T4 collaboration, administrator governance, and live KPI state.

Revision ID: 20260715_1083
Revises: 20260715_1082
Create Date: 2026-07-15 16:10:00

All tables reference existing users, courses, documents, knowledge nodes,
teacher assets, and Runtime evidence.  ``messages`` is intentionally separate
from Runtime ``agent_messages``; no source text, course copy, or profile copy
is introduced.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1083"
down_revision: str | None = "20260715_1082"
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
        "role_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("permission_codes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active','retired')", name="ck_role_definitions_status"),
        sa.UniqueConstraint("code", "version_no", name="uq_role_definitions_code_version"),
    )
    op.create_index(
        "uq_role_definitions_active_code",
        "role_definitions",
        ["code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "user_role_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active','revoked')", name="ck_user_role_grants_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["role_id"], ["role_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_user_role_grants_user_id", ["user_id"]),
        ("ix_user_role_grants_role_id", ["role_id"]),
        ("ix_user_role_grants_granted_by", ["granted_by"]),
    ):
        op.create_index(name, "user_role_grants", columns)
    op.create_index(
        "uq_user_role_grants_active",
        "user_role_grants",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "external_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ingested"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('policy','hot','job')", name="ck_external_signals_kind"),
        sa.CheckConstraint(
            "status IN ('ingested','validated','rejected','expired')",
            name="ck_external_signals_status",
        ),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["evidence_snapshot_id"], ["workflow_evidence_snapshots.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("kind", "source_fingerprint", name="uq_external_signals_kind_fingerprint"),
    )
    for name, columns in (
        ("ix_external_signals_source_document_id", ["source_document_id"]),
        ("ix_external_signals_agent_run_id", ["agent_run_id"]),
        ("ix_external_signals_evidence_snapshot_id", ["evidence_snapshot_id"]),
        ("ix_external_signals_created_by", ["created_by"]),
    ):
        op.create_index(name, "external_signals", columns)

    op.create_table(
        "course_update_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("diff", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_teacher_decision"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft','pending_teacher_decision','adopted','rejected','superseded','withdrawn')",
            name="ck_course_update_suggestions_status",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signal_id"], ["external_signals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["evidence_snapshot_id"], ["workflow_evidence_snapshots.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "course_id", "signal_id", "version_no", name="uq_course_update_suggestions_course_signal_version"
        ),
    )
    for name, columns in (
        ("ix_course_update_suggestions_course_id", ["course_id"]),
        ("ix_course_update_suggestions_signal_id", ["signal_id"]),
        ("ix_course_update_suggestions_agent_run_id", ["agent_run_id"]),
        ("ix_course_update_suggestions_evidence_snapshot_id", ["evidence_snapshot_id"]),
        ("ix_course_update_suggestions_created_by", ["created_by"]),
        ("ix_course_update_suggestions_status", ["status"]),
    ):
        op.create_index(name, "course_update_suggestions", columns)

    op.create_table(
        "course_update_impacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impact_type", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "impact_type IN ('add','revise','retire','emphasize')",
            name="ck_course_update_impacts_type",
        ),
        sa.ForeignKeyConstraint(
            ["suggestion_id"], ["course_update_suggestions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["knowledge_node_id"], ["knowledge_nodes.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "suggestion_id", "knowledge_node_id", "impact_type",
            name="uq_course_update_impacts_suggestion_node_type",
        ),
    )
    op.create_index("ix_course_update_impacts_suggestion_id", "course_update_impacts", ["suggestion_id"])
    op.create_index("ix_course_update_impacts_knowledge_node_id", "course_update_impacts", ["knowledge_node_id"])

    op.create_table(
        "course_update_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('adopt','reject')", name="ck_course_update_decisions_decision"),
        sa.ForeignKeyConstraint(
            ["suggestion_id"], ["course_update_suggestions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("suggestion_id", name="uq_course_update_decisions_suggestion"),
    )
    op.create_index("ix_course_update_decisions_suggestion_id", "course_update_decisions", ["suggestion_id"])
    op.create_index("ix_course_update_decisions_teacher_id", "course_update_decisions", ["teacher_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teaching_class_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("safety_state", sa.String(length=16), nullable=False, server_default="accepted"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recall_deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recalled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recalled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recall_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("scope_type IN ('course','class','individual')", name="ck_messages_scope_type"),
        sa.CheckConstraint(
            "safety_state IN ('accepted','rejected')", name="ck_messages_safety_state"
        ),
        sa.CheckConstraint(
            "status IN ('draft','sent','partially_delivered','recalled','expired')",
            name="ck_messages_status",
        ),
        sa.CheckConstraint(
            "(scope_type = 'course' AND course_id IS NOT NULL AND teaching_class_id IS NULL AND target_user_id IS NULL) "
            "OR (scope_type = 'class' AND course_id IS NOT NULL AND teaching_class_id IS NOT NULL AND target_user_id IS NULL) "
            "OR (scope_type = 'individual' AND course_id IS NOT NULL AND teaching_class_id IS NULL AND target_user_id IS NOT NULL)",
            name="ck_messages_scope_shape",
        ),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teaching_class_id"], ["teaching_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recalled_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("sender_user_id", "idempotency_key", name="uq_messages_sender_idempotency"),
    )
    for name, columns in (
        ("ix_messages_sender_user_id", ["sender_user_id"]),
        ("ix_messages_course_id", ["course_id"]),
        ("ix_messages_teaching_class_id", ["teaching_class_id"]),
        ("ix_messages_target_user_id", ["target_user_id"]),
        ("ix_messages_status", ["status"]),
        ("ix_messages_sent_at", ["sent_at"]),
    ):
        op.create_index(name, "messages", columns)

    op.create_table(
        "message_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_state", sa.String(length=16), nullable=False, server_default="unread"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recalled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "delivery_state IN ('unread','read','recalled')", name="ck_message_deliveries_state"
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("message_id", "recipient_user_id", name="uq_message_deliveries_message_recipient"),
    )
    op.create_index("ix_message_deliveries_message_id", "message_deliveries", ["message_id"])
    op.create_index("ix_message_deliveries_recipient_user_id", "message_deliveries", ["recipient_user_id"])
    op.create_index(
        "ix_message_deliveries_recipient_state",
        "message_deliveries",
        ["recipient_user_id", "delivery_state"],
    )

    op.create_table(
        "course_resource_governance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('active','restricted','withdrawn')",
            name="ck_course_resource_governance_state",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["course_asset_governance.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("asset_id", name="uq_course_resource_governance_asset"),
    )
    op.create_index("ix_course_resource_governance_asset_id", "course_resource_governance", ["asset_id"])
    op.create_index("ix_course_resource_governance_changed_by", "course_resource_governance", ["changed_by"])

    op.create_table(
        "kpi_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("query_key", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_relations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        *_timestamps(),
        sa.CheckConstraint("status IN ('active','retired')", name="ck_kpi_definitions_status"),
        sa.UniqueConstraint("code", "version_no", name="uq_kpi_definitions_code_version"),
    )
    op.create_index(
        "uq_kpi_definitions_active_code",
        "kpi_definitions",
        ["code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    admin_role_id = _stable_id("role:administrator:v1")
    op.bulk_insert(
        sa.table(
            "role_definitions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("code", sa.String()),
            sa.column("version_no", sa.Integer()),
            sa.column("permission_codes", postgresql.JSONB()),
            sa.column("status", sa.String()),
            sa.column("description", sa.Text()),
        ),
        [
            {
                "id": admin_role_id,
                "code": "administrator",
                "version_no": 1,
                "permission_codes": [
                    "admin.users.read",
                    "admin.roles.write",
                    "admin.resources.govern",
                    "admin.kpi.read",
                ],
                "status": "active",
                "description": "平台治理、角色、课程资源与真实 KPI 管理权限。",
            }
        ],
    )
    kpis = (
        ("active_teaching_classes", "active_teaching_classes", "状态为 active 的教学班总数。", ["teaching_classes"]),
        ("enrolled_students", "enrolled_students", "状态为 enrolled 的课程选课记录总数。", ["course_enrollments"]),
        ("published_grades", "published_grades", "状态为 published 的教师成绩决定总数。", ["assessment_grade_decisions"]),
        ("pending_course_updates", "pending_course_updates", "待课程教师处置的 Evidence 绑定课程更新建议总数。", ["course_update_suggestions", "external_signals"]),
        ("sent_messages_7d", "sent_messages_7d", "最近七天实际投递的站内消息总数。", ["messages", "message_deliveries"]),
        ("unread_deliveries", "unread_deliveries", "当前尚未读取且未撤回的消息投递总数。", ["message_deliveries"]),
    )
    op.bulk_insert(
        sa.table(
            "kpi_definitions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("code", sa.String()),
            sa.column("version_no", sa.Integer()),
            sa.column("query_key", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("source_relations", postgresql.JSONB()),
            sa.column("status", sa.String()),
        ),
        [
            {
                "id": _stable_id(f"kpi:{code}:v1"),
                "code": code,
                "version_no": 1,
                "query_key": query_key,
                "description": description,
                "source_relations": relations,
                "status": "active",
            }
            for code, query_key, description, relations in kpis
        ],
    )
    # A demo grant is inserted only when the deterministic demo teacher exists.
    # Deployments without that account receive no implicit administrator and
    # must bootstrap one through their controlled deployment process.
    op.execute(
        sa.text(
            """
            INSERT INTO user_role_grants
                (id, user_id, role_id, granted_by, granted_at, status, reason, created_at, updated_at)
            SELECT :grant_id, u.id, :role_id, u.id, NOW(), 'active',
                   'competition demo bootstrap administrator', NOW(), NOW()
            FROM users AS u
            WHERE u.email = 'demo-course-teacher@securehub.local'
              AND NOT EXISTS (
                SELECT 1 FROM user_role_grants AS g
                WHERE g.user_id = u.id AND g.role_id = :role_id AND g.status = 'active'
              )
            """
        ).bindparams(
            grant_id=_stable_id("role-grant:demo-course-teacher:administrator:v1"), role_id=admin_role_id
        )
    )


def downgrade() -> None:
    op.drop_index("uq_kpi_definitions_active_code", table_name="kpi_definitions")
    op.drop_table("kpi_definitions")

    op.drop_index("ix_course_resource_governance_changed_by", table_name="course_resource_governance")
    op.drop_index("ix_course_resource_governance_asset_id", table_name="course_resource_governance")
    op.drop_table("course_resource_governance")

    op.drop_index("ix_message_deliveries_recipient_state", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_recipient_user_id", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_message_id", table_name="message_deliveries")
    op.drop_table("message_deliveries")
    for name in (
        "ix_messages_sent_at",
        "ix_messages_status",
        "ix_messages_target_user_id",
        "ix_messages_teaching_class_id",
        "ix_messages_course_id",
        "ix_messages_sender_user_id",
    ):
        op.drop_index(name, table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_course_update_decisions_teacher_id", table_name="course_update_decisions")
    op.drop_index("ix_course_update_decisions_suggestion_id", table_name="course_update_decisions")
    op.drop_table("course_update_decisions")
    op.drop_index("ix_course_update_impacts_knowledge_node_id", table_name="course_update_impacts")
    op.drop_index("ix_course_update_impacts_suggestion_id", table_name="course_update_impacts")
    op.drop_table("course_update_impacts")
    for name in (
        "ix_course_update_suggestions_status",
        "ix_course_update_suggestions_created_by",
        "ix_course_update_suggestions_evidence_snapshot_id",
        "ix_course_update_suggestions_agent_run_id",
        "ix_course_update_suggestions_signal_id",
        "ix_course_update_suggestions_course_id",
    ):
        op.drop_index(name, table_name="course_update_suggestions")
    op.drop_table("course_update_suggestions")
    for name in (
        "ix_external_signals_created_by",
        "ix_external_signals_evidence_snapshot_id",
        "ix_external_signals_agent_run_id",
        "ix_external_signals_source_document_id",
    ):
        op.drop_index(name, table_name="external_signals")
    op.drop_table("external_signals")

    op.drop_index("uq_user_role_grants_active", table_name="user_role_grants")
    for name in (
        "ix_user_role_grants_granted_by",
        "ix_user_role_grants_role_id",
        "ix_user_role_grants_user_id",
    ):
        op.drop_index(name, table_name="user_role_grants")
    op.drop_table("user_role_grants")
    op.drop_index("uq_role_definitions_active_code", table_name="role_definitions")
    op.drop_table("role_definitions")
