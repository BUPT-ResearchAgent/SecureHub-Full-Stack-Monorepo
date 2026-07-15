# Status: real

"""Create T6 consent-gated fairness and reproducible benchmark state.

Revision ID: 20260715_1085
Revises: 20260715_1084
Create Date: 2026-07-15 20:05:00

No protected-attribute column is added.  Group values are limited by the
service to the RFC's non-sensitive teaching cohort/class keys; metric cells
are aggregate-only and cannot modify a student's score, authority, or status.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260715_1085"
down_revision: str | None = "20260715_1084"
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
        "fairness_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("allowed_group_keys", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("minimum_sample", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("pass_score", sa.Float(), nullable=False, server_default="60"),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_fairness_policies_status"),
        sa.CheckConstraint("minimum_sample > 0", name="ck_fairness_policies_minimum_sample"),
        sa.CheckConstraint("retention_days > 0", name="ck_fairness_policies_retention_days"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", "version_no", name="uq_fairness_policies_code_version"),
    )
    op.create_index("ix_fairness_policies_created_by", "fairness_policies", ["created_by"])
    op.create_index(
        "uq_fairness_policies_active_code",
        "fairness_policies",
        ["code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "fairness_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="assessment_fairness"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="granted"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('granted','withdrawn','expired')", name="ck_fairness_consents_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["fairness_policies.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "policy_id", "scope", name="uq_fairness_consents_user_policy_scope"),
    )
    op.create_index("ix_fairness_consents_user_id", "fairness_consents", ["user_id"])
    op.create_index("ix_fairness_consents_policy_id", "fairness_consents", ["policy_id"])

    op.create_table(
        "fairness_group_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_key", sa.String(length=64), nullable=False),
        sa.Column("minimal_group_value", sa.String(length=96), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["fairness_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "policy_id", "group_key", name="uq_fairness_group_assignment"),
    )
    for name, columns in (
        ("ix_fairness_group_assignments_user_id", ["user_id"]),
        ("ix_fairness_group_assignments_policy_id", ["policy_id"]),
        ("ix_fairness_group_assignments_assigned_by", ["assigned_by"]),
        ("ix_fairness_group_assignments_policy_key", ["policy_id", "group_key"]),
    ):
        op.create_index(name, "fairness_group_assignments", columns)

    op.create_table(
        "fairness_metric_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_scope", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dataset_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("threshold_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("rejection_code", sa.String(length=64), nullable=True),
        sa.Column("limitations", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','completed','insufficient_sample','rejected')",
            name="ck_fairness_metric_runs_status",
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["fairness_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_fairness_metric_runs_policy_id", ["policy_id"]),
        ("ix_fairness_metric_runs_dataset_fingerprint", ["dataset_fingerprint"]),
        ("ix_fairness_metric_runs_initiated_by", ["initiated_by"]),
        ("ix_fairness_metric_runs_policy_finished", ["policy_id", "finished_at"]),
    ):
        op.create_index(name, "fairness_metric_runs", columns)

    op.create_table(
        "fairness_metric_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_key", sa.String(length=64), nullable=False),
        sa.Column("group_value", sa.String(length=96), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("mean_score", sa.Float(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("fpr", sa.Float(), nullable=True),
        sa.Column("fnr", sa.Float(), nullable=True),
        sa.Column("equal_opportunity_delta", sa.Float(), nullable=True),
        sa.Column("confidence_interval", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("limitations", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
        sa.CheckConstraint("sample_size > 0", name="ck_fairness_metric_cells_sample_size"),
        sa.ForeignKeyConstraint(["run_id"], ["fairness_metric_runs.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "group_key", "group_value", name="uq_fairness_metric_cells_group"),
    )
    op.create_index("ix_fairness_metric_cells_run_id", "fairness_metric_cells", ["run_id"])
    op.create_index("ix_fairness_metric_cells_run", "fairness_metric_cells", ["run_id"])

    op.create_table(
        "fairness_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("metric_cell_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_kind", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('open','under_review','resolved','dismissed')", name="ck_fairness_alerts_status"
        ),
        sa.CheckConstraint("severity IN ('low','medium','high')", name="ck_fairness_alerts_severity"),
        sa.ForeignKeyConstraint(["metric_cell_id"], ["fairness_metric_cells.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_fairness_alerts_metric_cell_id", "fairness_alerts", ["metric_cell_id"])
    op.create_index("ix_fairness_alerts_status_opened", "fairness_alerts", ["status", "opened_at"])

    op.create_table(
        "fairness_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('under_review','resolved','dismissed')", name="ck_fairness_reviews_status"
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["fairness_alerts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_fairness_reviews_alert_id", "fairness_reviews", ["alert_id"])
    op.create_index("ix_fairness_reviews_reviewer_id", "fairness_reviews", ["reviewer_id"])
    op.create_index("ix_fairness_reviews_alert_reviewed", "fairness_reviews", ["alert_id", "reviewed_at"])

    op.create_table(
        "fairness_appeals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("grade_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appellant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="submitted"),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('submitted','reviewing','resolved','closed')", name="ck_fairness_appeals_status"
        ),
        sa.ForeignKeyConstraint(["grade_decision_id"], ["assessment_grade_decisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["appellant_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_fairness_appeals_grade_decision_id", ["grade_decision_id"]),
        ("ix_fairness_appeals_appellant_user_id", ["appellant_user_id"]),
        ("ix_fairness_appeals_reviewer_id", ["reviewer_id"]),
        ("ix_fairness_appeals_appellant_status", ["appellant_user_id", "status"]),
    ):
        op.create_index(name, "fairness_appeals", columns)

    op.create_table(
        "benchmark_dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("semantic_version", sa.String(length=32), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("label_schema_version", sa.String(length=64), nullable=False),
        sa.Column("manifest_path", sa.String(length=256), nullable=False),
        sa.Column("data_path", sa.String(length=256), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="frozen"),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "kind IN ('content_relevance','api_misuse','fairness')",
            name="ck_benchmark_dataset_versions_kind",
        ),
        sa.CheckConstraint(
            "status IN ('draft','frozen','retired')", name="ck_benchmark_dataset_versions_status"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("kind", "semantic_version", name="uq_benchmark_dataset_versions_kind_version"),
    )
    op.create_index("ix_benchmark_dataset_versions_created_by", "benchmark_dataset_versions", ["created_by"])

    op.create_table(
        "benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("code_revision", sa.String(length=128), nullable=False),
        sa.Column("config_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("executed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','failed','rejected')", name="ck_benchmark_runs_status"
        ),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["benchmark_dataset_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["executed_by"], ["users.id"], ondelete="RESTRICT"),
    )
    for name, columns in (
        ("ix_benchmark_runs_dataset_version_id", ["dataset_version_id"]),
        ("ix_benchmark_runs_config_fingerprint", ["config_fingerprint"]),
        ("ix_benchmark_runs_executed_by", ["executed_by"]),
        ("ix_benchmark_runs_dataset_finished", ["dataset_version_id", "finished_at"]),
    ):
        op.create_index(name, "benchmark_runs", columns)

    op.create_table(
        "benchmark_case_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_key", sa.String(length=128), nullable=False),
        sa.Column("expected_label", sa.String(length=64), nullable=False),
        sa.Column("predicted_label", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("failure_reason", sa.String(length=128), nullable=True),
        sa.Column("redacted_payload_reference", sa.String(length=256), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "decision IN ('tp','tn','fp','fn','not_scored')", name="ck_benchmark_case_results_decision"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "case_key", name="uq_benchmark_case_results_run_case"),
    )
    op.create_index("ix_benchmark_case_results_run_id", "benchmark_case_results", ["run_id"])
    op.create_index("ix_benchmark_case_results_run_decision", "benchmark_case_results", ["run_id", "decision"])

    # DDL keeps the colon-bearing JSONB literal out of SQLAlchemy's bind-parameter
    # parser while remaining compilable in Alembic's PostgreSQL offline mode.
    # These are immutable metadata assets, not user data, and use no
    # request-derived values.
    op.execute(
        sa.DDL(
            f"""
        INSERT INTO fairness_policies
          (id, code, version_no, purpose, allowed_group_keys, minimum_sample,
           pass_score, thresholds, retention_days, status)
        VALUES
          ('{_stable_id("fairness-policy:cohort:v1")}'::uuid, 'fairness-cohort', 1,
           '经明确同意后，对已发布教育评估的非敏感 cohort 聚合公平监控；不用于个体处分。',
           '["cohort"]'::jsonb, 20, 60.0,
           '{{"max_mean_score_gap":10.0,"max_pass_rate_gap":0.2}}'::jsonb, 90, 'active')
            """
        )
    )
    benchmark_rows = (
        (
            "benchmark:content-relevance:v1",
            "content_relevance",
            "1.0.0",
            "5aae2345c0c1e6c8c0e694ce077f70a0ebfa5290572e8aa827a200e7827706b6",
            "content-relevance-label-v1",
            "manifests/content-relevance-v1.json",
            "data/content-relevance-v1.jsonl",
            "冻结、脱敏的非用户评测样本；只验证标注与判定复现性，不代表真实学习效果。",
        ),
        (
            "benchmark:api-misuse:v1",
            "api_misuse",
            "1.0.0",
            "c90bb474ba1eb2de3dea3a285505d05ed3862f2dbd50750ffbd6d6b29d43a272",
            "api-misuse-label-v1",
            "manifests/api-misuse-v1.json",
            "data/api-misuse-v1.jsonl",
            "冻结、脱敏的规则评测样本；不含凭据、IP、设备或原始请求负载，也不声明真实攻击率。",
        ),
        (
            "benchmark:fairness:v1",
            "fairness",
            "1.0.0",
            "ac71a28b01980d2c16898800eceb596e95d0dd88c323d312b0e06ace4bf73adf",
            "fairness-review-label-v1",
            "manifests/fairness-v1.json",
            "data/fairness-v1.jsonl",
            "冻结的非用户评测样本，只验证聚合阈值告警复现性，不得表述为真实群体效果。",
        ),
    )
    for seed_key, kind, semantic_version, manifest_hash, label_version, manifest_path, data_path, note in benchmark_rows:
        op.execute(
            f"""
            INSERT INTO benchmark_dataset_versions
              (id, kind, semantic_version, manifest_hash, label_schema_version,
               manifest_path, data_path, source_note, status)
            VALUES
              ('{_stable_id(seed_key)}'::uuid, '{kind}', '{semantic_version}', '{manifest_hash}',
               '{label_version}', '{manifest_path}', '{data_path}', '{note}', 'frozen')
            """
        )


def downgrade() -> None:
    op.drop_index("ix_benchmark_case_results_run_decision", table_name="benchmark_case_results")
    op.drop_index("ix_benchmark_case_results_run_id", table_name="benchmark_case_results")
    op.drop_table("benchmark_case_results")

    for name in (
        "ix_benchmark_runs_dataset_finished",
        "ix_benchmark_runs_executed_by",
        "ix_benchmark_runs_config_fingerprint",
        "ix_benchmark_runs_dataset_version_id",
    ):
        op.drop_index(name, table_name="benchmark_runs")
    op.drop_table("benchmark_runs")

    op.drop_index("ix_benchmark_dataset_versions_created_by", table_name="benchmark_dataset_versions")
    op.drop_table("benchmark_dataset_versions")

    for name in (
        "ix_fairness_appeals_appellant_status",
        "ix_fairness_appeals_reviewer_id",
        "ix_fairness_appeals_appellant_user_id",
        "ix_fairness_appeals_grade_decision_id",
    ):
        op.drop_index(name, table_name="fairness_appeals")
    op.drop_table("fairness_appeals")

    op.drop_index("ix_fairness_reviews_alert_reviewed", table_name="fairness_reviews")
    op.drop_index("ix_fairness_reviews_reviewer_id", table_name="fairness_reviews")
    op.drop_index("ix_fairness_reviews_alert_id", table_name="fairness_reviews")
    op.drop_table("fairness_reviews")

    op.drop_index("ix_fairness_alerts_status_opened", table_name="fairness_alerts")
    op.drop_index("ix_fairness_alerts_metric_cell_id", table_name="fairness_alerts")
    op.drop_table("fairness_alerts")

    op.drop_index("ix_fairness_metric_cells_run", table_name="fairness_metric_cells")
    op.drop_index("ix_fairness_metric_cells_run_id", table_name="fairness_metric_cells")
    op.drop_table("fairness_metric_cells")

    for name in (
        "ix_fairness_metric_runs_policy_finished",
        "ix_fairness_metric_runs_initiated_by",
        "ix_fairness_metric_runs_dataset_fingerprint",
        "ix_fairness_metric_runs_policy_id",
    ):
        op.drop_index(name, table_name="fairness_metric_runs")
    op.drop_table("fairness_metric_runs")

    for name in (
        "ix_fairness_group_assignments_policy_key",
        "ix_fairness_group_assignments_assigned_by",
        "ix_fairness_group_assignments_policy_id",
        "ix_fairness_group_assignments_user_id",
    ):
        op.drop_index(name, table_name="fairness_group_assignments")
    op.drop_table("fairness_group_assignments")

    op.drop_index("ix_fairness_consents_policy_id", table_name="fairness_consents")
    op.drop_index("ix_fairness_consents_user_id", table_name="fairness_consents")
    op.drop_table("fairness_consents")

    op.drop_index("uq_fairness_policies_active_code", table_name="fairness_policies")
    op.drop_index("ix_fairness_policies_created_by", table_name="fairness_policies")
    op.drop_table("fairness_policies")
