# Status: real

"""Durable, framework-neutral persistence models for the Agent Runtime.

These rows are deliberately independent from LangGraph and process-local run
registries.  PostgreSQL is the source of truth; the models also remain usable
with the repository's SQLite test configuration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.runtime.contracts import SSE_EVENT_TYPES, TERMINAL_RUN_STATUSES


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Durable root execution record and per-run event sequence allocator."""

    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "workflow_name",
            "idempotency_key",
            name="uq_workflow_runs_user_workflow_idempotency",
        ),
        Index("ix_workflow_runs_status_lease", "status", "lease_expires_at"),
    )

    workflow_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    workflow_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    workflow_definition_digest: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    catalog_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    provider_policy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    checkpoint_schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    runtime_build_sha: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    # Root creation resolves this once. The runtime only receives this stable
    # opaque identifier, never an API key or a mutable global Settings value.
    credential_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="real")
    requested_provider: Mapped[str | None] = mapped_column(String(64))
    requested_model: Mapped[str | None] = mapped_column(String(128))
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    budget: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(128), index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowStepAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One durable attempt of a framework-neutral workflow node."""

    __tablename__ = "workflow_step_attempts"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id", "node_id", "attempt", name="uq_workflow_step_attempts_run_node_attempt"
        ),
        Index("ix_workflow_step_attempts_run_status", "workflow_run_id", "status"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(120), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agents.id"))
    skill_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_skills.id"))
    agent_name: Mapped[str | None] = mapped_column(String(120))
    skill_name: Mapped[str | None] = mapped_column(String(120))
    skill_version: Mapped[str | None] = mapped_column(String(64))
    skill_definition_digest: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    prompt_digest: Mapped[str | None] = mapped_column(String(128))
    agent_run_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_runs.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    input_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Float)
    error_code: Mapped[str | None] = mapped_column(String(96))
    error: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class WorkflowCheckpoint(UUIDPrimaryKeyMixin, Base):
    """RuntimeEngine's only durable checkpoint representation."""

    __tablename__ = "workflow_checkpoints"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "checkpoint_seq", name="uq_workflow_checkpoints_run_seq"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkpoint_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_definition_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_build_sha: Mapped[str] = mapped_column(String(128), nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    event_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkflowEvidenceSnapshot(UUIDPrimaryKeyMixin, Base):
    """Immutable, minimal citation snapshot for one retrieved evidence item."""

    __tablename__ = "workflow_evidence_snapshots"
    __table_args__ = (
        Index("ix_workflow_evidence_snapshots_run_step", "workflow_run_id", "step_attempt_id"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_attempt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"), index=True
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )
    # IDs are stored as stable strings rather than foreign keys: snapshots
    # must survive source deletion and fixture evidence may use non-UUID IDs.
    chunk_id: Mapped[str | None] = mapped_column(String(128), index=True)
    document_id: Mapped[str | None] = mapped_column(String(128), index=True)
    chunk_version: Mapped[str | None] = mapped_column(String(64))
    content_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    citation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rank: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkflowProviderCall(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Auditable provider call journal with explicit unknown-outcome semantics."""

    __tablename__ = "workflow_provider_calls"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "step_attempt_id",
            "attempt",
            "stream_attempt",
            name="uq_workflow_provider_calls_attempt",
        ),
        Index("ix_workflow_provider_calls_run_status", "workflow_run_id", "status"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_attempt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"), index=True
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stream_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(256), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="started", index=True)
    outcome: Mapped[str | None] = mapped_column(String(32), index=True)
    response_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    response_digest: Mapped[str | None] = mapped_column(String(128))
    visible_token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unknown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only SSE event and Transactional Outbox row."""

    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "sequence", name="uq_workflow_events_run_sequence"),
        Index("ix_workflow_events_outbox", "published_at", "publish_ready_at", "next_publish_at"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    step_attempt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_step_attempts.id", ondelete="SET NULL"), index=True
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True
    )
    provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_provider_calls.id", ondelete="SET NULL"), index=True
    )
    # Artifact events stay NULL until the object reaches active status.
    publish_ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    publish_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_publish_error: Mapped[str | None] = mapped_column(Text)
    publish_lease_owner: Mapped[str | None] = mapped_column(String(128))
    publish_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkflowApproval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Durable human-in-the-loop decision for a root or high-risk node."""

    __tablename__ = "workflow_approvals"
    __table_args__ = (
        Index("ix_workflow_approvals_run_status", "workflow_run_id", "status"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str | None] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requested_by: Mapped[str | None] = mapped_column(String(128))
    decided_by: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowAuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only control/audit facts without prompt or provider-response text."""

    __tablename__ = "workflow_audit_logs"
    __table_args__ = (
        Index("ix_workflow_audit_logs_run_created", "workflow_run_id", "created_at"),
    )

    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    node_id: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
