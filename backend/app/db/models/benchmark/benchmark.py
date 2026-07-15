# Status: real

"""Versioned, redacted benchmark manifests and deterministic run records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BenchmarkDatasetVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A frozen, non-user-effect evaluation corpus manifest."""

    __tablename__ = "benchmark_dataset_versions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('content_relevance','api_misuse','fairness')",
            name="ck_benchmark_dataset_versions_kind",
        ),
        CheckConstraint("status IN ('draft','frozen','retired')", name="ck_benchmark_dataset_versions_status"),
        UniqueConstraint("kind", "semantic_version", name="uq_benchmark_dataset_versions_kind_version"),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    label_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_path: Mapped[str] = mapped_column(String(256), nullable=False)
    data_path: Mapped[str] = mapped_column(String(256), nullable=False)
    source_note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="frozen")
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )


class BenchmarkRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A deterministic execution with recorded dataset and config fingerprints."""

    __tablename__ = "benchmark_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed','failed','rejected')",
            name="ck_benchmark_runs_status",
        ),
        Index("ix_benchmark_runs_dataset_finished", "dataset_version_id", "finished_at"),
    )

    dataset_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_dataset_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    code_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    config_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="queued")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    executed_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BenchmarkCaseResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One redacted case outcome; no raw request or learner payload is stored."""

    __tablename__ = "benchmark_case_results"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('tp','tn','fp','fn','not_scored')",
            name="ck_benchmark_case_results_decision",
        ),
        UniqueConstraint("run_id", "case_key", name="uq_benchmark_case_results_run_case"),
        Index("ix_benchmark_case_results_run_decision", "run_id", "decision"),
    )

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("benchmark_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    case_key: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_label: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(128))
    redacted_payload_reference: Mapped[str] = mapped_column(String(256), nullable=False)
