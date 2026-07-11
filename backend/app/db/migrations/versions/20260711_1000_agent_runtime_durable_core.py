# Status: real

"""Agent Runtime v1.1 durable core.

Revision ID: 20260711_1000
Revises: 20260611_0960
Create Date: 2026-07-11 10:00:00

Adds the durable workflow root/step/event/checkpoint/evidence/provider-call
schema and only additive links to legacy AgentRun/resource/storage rows.  The
new ``workflow_events`` table is both the append-only SSE source and a
transactional outbox; Redis remains an optional projection.

The migration intentionally keeps old ``storage_objects.status='ready'``
rows valid. New Artifact Saga writes use staging/active/orphaned/deleted and
the newly added lifecycle columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260711_1000"
down_revision: str | None = "20260611_0960"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json() -> sa.types.TypeEngine[object]:
    """Use JSONB in PostgreSQL and env.py's JSON fallback in SQLite."""
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # Root must exist before the remaining Runtime records and the legacy
    # AgentRun/resource foreign-key additions.
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_name", sa.String(length=120), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("workflow_definition_digest", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("catalog_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("provider_policy_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("checkpoint_schema_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("runtime_build_sha", sa.String(length=128), nullable=False, server_default="unknown"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="real"),
        sa.Column("requested_provider", sa.String(length=64), nullable=True),
        sa.Column("requested_model", sa.String(length=128), nullable=True),
        sa.Column("input_payload", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("output_ref", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("budget", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_event_sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "user_id",
            "workflow_name",
            "idempotency_key",
            name="uq_workflow_runs_user_workflow_idempotency",
        ),
    )
    op.create_index("ix_workflow_runs_workflow_name", "workflow_runs", ["workflow_name"])
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index("ix_workflow_runs_lease_owner", "workflow_runs", ["lease_owner"])
    op.create_index("ix_workflow_runs_lease_expires_at", "workflow_runs", ["lease_expires_at"])
    op.create_index("ix_workflow_runs_status_lease", "workflow_runs", ["status", "lease_expires_at"])

    # AgentRun already exists. Creating the step table first allows each new
    # attempt to point at a real child AgentRun without a second runtime table.
    op.create_table(
        "workflow_step_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(length=120), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_skills.id"), nullable=True),
        sa.Column("agent_name", sa.String(length=120), nullable=True),
        sa.Column("skill_name", sa.String(length=120), nullable=True),
        sa.Column("skill_version", sa.String(length=64), nullable=True),
        sa.Column("skill_definition_digest", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_digest", sa.String(length=128), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_ref", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("output_ref", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quality", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(length=96), nullable=True),
        sa.Column("error", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workflow_run_id", "node_id", "attempt", name="uq_workflow_step_attempts_run_node_attempt"
        ),
    )
    op.create_index("ix_workflow_step_attempts_workflow_run_id", "workflow_step_attempts", ["workflow_run_id"])
    op.create_index("ix_workflow_step_attempts_agent_run_id", "workflow_step_attempts", ["agent_run_id"])
    op.create_index("ix_workflow_step_attempts_status", "workflow_step_attempts", ["status"])
    op.create_index(
        "ix_workflow_step_attempts_run_status",
        "workflow_step_attempts",
        ["workflow_run_id", "status"],
    )

    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checkpoint_seq", sa.Integer(), nullable=False),
        sa.Column("workflow_definition_digest", sa.String(length=128), nullable=False),
        sa.Column("catalog_version", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_schema_version", sa.String(length=64), nullable=False),
        sa.Column("runtime_build_sha", sa.String(length=128), nullable=False),
        sa.Column("state_json", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("event_cursor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workflow_run_id", "checkpoint_seq", name="uq_workflow_checkpoints_run_seq"),
    )
    op.create_index("ix_workflow_checkpoints_workflow_run_id", "workflow_checkpoints", ["workflow_run_id"])

    op.create_table(
        "workflow_evidence_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chunk_id", sa.String(length=128), nullable=True),
        sa.Column("document_id", sa.String(length=128), nullable=True),
        sa.Column("chunk_version", sa.String(length=64), nullable=True),
        sa.Column("content_digest", sa.String(length=128), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("citation", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rights", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_evidence_snapshots_workflow_run_id", "workflow_evidence_snapshots", ["workflow_run_id"])
    op.create_index("ix_workflow_evidence_snapshots_step_attempt_id", "workflow_evidence_snapshots", ["step_attempt_id"])
    op.create_index("ix_workflow_evidence_snapshots_agent_run_id", "workflow_evidence_snapshots", ["agent_run_id"])
    op.create_index("ix_workflow_evidence_snapshots_chunk_id", "workflow_evidence_snapshots", ["chunk_id"])
    op.create_index("ix_workflow_evidence_snapshots_document_id", "workflow_evidence_snapshots", ["document_id"])
    op.create_index(
        "ix_workflow_evidence_snapshots_run_step",
        "workflow_evidence_snapshots",
        ["workflow_run_id", "step_attempt_id"],
    )

    op.create_table(
        "workflow_provider_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stream_attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("provider_policy_version", sa.String(length=64), nullable=False),
        sa.Column("request_digest", sa.String(length=128), nullable=False),
        sa.Column("provider_request_id", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="started"),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("response_ref", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("response_digest", sa.String(length=128), nullable=True),
        sa.Column("visible_token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unknown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workflow_run_id",
            "step_attempt_id",
            "attempt",
            "stream_attempt",
            name="uq_workflow_provider_calls_attempt",
        ),
    )
    op.create_index("ix_workflow_provider_calls_workflow_run_id", "workflow_provider_calls", ["workflow_run_id"])
    op.create_index("ix_workflow_provider_calls_step_attempt_id", "workflow_provider_calls", ["step_attempt_id"])
    op.create_index("ix_workflow_provider_calls_agent_run_id", "workflow_provider_calls", ["agent_run_id"])
    op.create_index("ix_workflow_provider_calls_provider_request_id", "workflow_provider_calls", ["provider_request_id"])
    op.create_index("ix_workflow_provider_calls_status", "workflow_provider_calls", ["status"])
    op.create_index("ix_workflow_provider_calls_outcome", "workflow_provider_calls", ["outcome"])
    op.create_index(
        "ix_workflow_provider_calls_run_status",
        "workflow_provider_calls",
        ["workflow_run_id", "status"],
    )

    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("payload", _json(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "step_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "provider_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_provider_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("publish_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_publish_error", sa.Text(), nullable=True),
        sa.Column("publish_lease_owner", sa.String(length=128), nullable=True),
        sa.Column("publish_lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workflow_run_id", "sequence", name="uq_workflow_events_run_sequence"),
    )
    op.create_index("ix_workflow_events_workflow_run_id", "workflow_events", ["workflow_run_id"])
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"])
    op.create_index("ix_workflow_events_step_attempt_id", "workflow_events", ["step_attempt_id"])
    op.create_index("ix_workflow_events_agent_run_id", "workflow_events", ["agent_run_id"])
    op.create_index("ix_workflow_events_provider_call_id", "workflow_events", ["provider_call_id"])
    op.create_index("ix_workflow_events_published_at", "workflow_events", ["published_at"])
    op.create_index("ix_workflow_events_next_publish_at", "workflow_events", ["next_publish_at"])
    op.create_index(
        "ix_workflow_events_outbox",
        "workflow_events",
        ["published_at", "publish_ready_at", "next_publish_at"],
    )

    # Additive legacy links. batch_alter_table is required for SQLite tests
    # and remains valid on PostgreSQL.
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", name="fk_agent_runs_workflow_run_id_workflow_runs"), nullable=True))
        batch.add_column(sa.Column("step_attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_step_attempts.id", name="fk_agent_runs_step_attempt_id_workflow_step_attempts"), nullable=True))
        batch.add_column(sa.Column("attempt", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("provider", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("model", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("error_code", sa.String(length=96), nullable=True))
        batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_agent_runs_workflow_run_id", ["workflow_run_id"])
        batch.create_index("ix_agent_runs_step_attempt_id", ["step_attempt_id"])

    with op.batch_alter_table("generated_resources") as batch:
        batch.add_column(sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", name="fk_generated_resources_workflow_run_id_workflow_runs"), nullable=True))
        batch.add_column(sa.Column("step_attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_step_attempts.id", name="fk_generated_resources_step_attempt_id_workflow_step_attempts"), nullable=True))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_index("ix_generated_resources_workflow_run_id", ["workflow_run_id"])
        batch.create_index("ix_generated_resources_step_attempt_id", ["step_attempt_id"])

    with op.batch_alter_table("storage_objects") as batch:
        batch.add_column(sa.Column("staging_key", sa.Text(), nullable=True))
        batch.add_column(sa.Column("active_key", sa.Text(), nullable=True))
        batch.add_column(sa.Column("checksum", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("orphaned_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_storage_objects_checksum", ["checksum"])


def downgrade() -> None:
    # This physical downgrade is only for empty/disposable databases. Production
    # rollback follows the v1.1 forward-compatible feature-flag strategy.
    with op.batch_alter_table("storage_objects") as batch:
        batch.drop_index("ix_storage_objects_checksum")
        batch.drop_column("deleted_at")
        batch.drop_column("orphaned_at")
        batch.drop_column("activated_at")
        batch.drop_column("checksum")
        batch.drop_column("active_key")
        batch.drop_column("staging_key")

    with op.batch_alter_table("generated_resources") as batch:
        batch.drop_index("ix_generated_resources_step_attempt_id")
        batch.drop_index("ix_generated_resources_workflow_run_id")
        batch.drop_column("version")
        batch.drop_column("step_attempt_id")
        batch.drop_column("workflow_run_id")

    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_index("ix_agent_runs_step_attempt_id")
        batch.drop_index("ix_agent_runs_workflow_run_id")
        batch.drop_column("finished_at")
        batch.drop_column("started_at")
        batch.drop_column("error_code")
        batch.drop_column("model")
        batch.drop_column("provider")
        batch.drop_column("attempt")
        batch.drop_column("step_attempt_id")
        batch.drop_column("workflow_run_id")

    op.drop_table("workflow_events")
    op.drop_table("workflow_provider_calls")
    op.drop_table("workflow_evidence_snapshots")
    op.drop_table("workflow_checkpoints")
    op.drop_table("workflow_step_attempts")
    op.drop_table("workflow_runs")
