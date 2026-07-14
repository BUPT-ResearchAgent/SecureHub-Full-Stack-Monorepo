# Status: real

"""Frozen public contracts for the durable SecureHub agent runtime.

This module deliberately contains framework-neutral data only.  It is shared by
the runtime engine, persistence adapters, HTTP adapters and SSE gateway; it
must not import LangGraph, FastAPI, a provider SDK, or an agent implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    REWORKING = "reworking"
    PAUSING = "pausing"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class StepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ExecutionMode(StrEnum):
    FIXTURE = "fixture"
    REAL = "real"


class ProviderCallStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


class ProviderCallOutcome(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    KNOWN_ERROR = "known_error"


class ArtifactStatus(StrEnum):
    STAGING = "staging"
    ACTIVE = "active"
    ORPHANED = "orphaned"
    DELETED = "deleted"


class EventType(StrEnum):
    PROGRESS = "progress"
    EVIDENCE = "evidence"
    TOKEN = "token"
    ARTIFACT = "artifact"
    TRACE = "trace"
    DONE = "done"
    ERROR = "error"


SSE_EVENT_TYPES = frozenset(event.value for event in EventType)
TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.CANCELLED, RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.BLOCKED}
)
TERMINAL_STEP_STATUSES = frozenset(
    {StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.BLOCKED, StepStatus.CANCELLED, StepStatus.SKIPPED}
)


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    INVALID_WORKFLOW = "INVALID_WORKFLOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    GUARDRAIL_BLOCKED = "GUARDRAIL_BLOCKED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_UNKNOWN_OUTCOME = "PROVIDER_UNKNOWN_OUTCOME"
    STRICT_PARSE_FAILED = "STRICT_PARSE_FAILED"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    AGENT_RUN_PERSIST_FAILED = "AGENT_RUN_PERSIST_FAILED"
    ARTIFACT_PERSIST_FAILED = "ARTIFACT_PERSIST_FAILED"
    LEASE_FENCED = "LEASE_FENCED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    RUN_FORBIDDEN = "RUN_FORBIDDEN"
    RUN_CANCELLED = "RUN_CANCELLED"
    SEMANTIC_VERSION_INCOMPATIBLE = "SEMANTIC_VERSION_INCOMPATIBLE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    INTERNAL = "INTERNAL"


class RuntimeErrorDetail(BaseModel):
    """Sanitised error data safe for persistence and SSE.

    Raw provider payloads, prompts and reasoning are intentionally absent.
    """

    code: ErrorCode | str
    message: str
    recoverable: bool = False
    retry_after_seconds: int | None = None


class RuntimeSemanticVersion(BaseModel):
    workflow_definition_digest: str
    catalog_version: str
    provider_policy_version: str
    checkpoint_schema_version: str
    runtime_build_sha: str


class ProviderSelection(BaseModel):
    requested_provider: str | None = None
    requested_model: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None
    policy_version: str = "v1"


class EvidenceRef(BaseModel):
    evidence_snapshot_id: UUID | str
    chunk_id: UUID | str
    document_id: UUID | str | None = None
    content_digest: str
    citation: str | None = None
    source: str | None = None
    rights: str | None = None


class ArtifactRef(BaseModel):
    resource_id: UUID | str
    resource_type: str
    schema_version: str = "v1"
    producer_agent_run_id: UUID | str | None = None
    evidence_snapshot_ids: list[UUID | str] = Field(default_factory=list)
    quality_score: float | None = None
    content_digest: str | None = None
    object_key: str | None = None
    parent_resource_id: UUID | str | None = None
    lineage_root_id: UUID | str | None = None
    version: int = Field(default=1, ge=1)


class QualityDefectCode(StrEnum):
    EVIDENCE_MISSING = "evidence_missing"
    FACT_CONFLICT = "fact_conflict"
    SCHEMA_INVALID = "schema_invalid"
    INSTRUCTIONAL_MISMATCH = "instructional_mismatch"
    CITATION_MISMATCH = "citation_mismatch"
    SAFETY_VIOLATION = "safety_violation"


class QualityDefect(BaseModel):
    code: QualityDefectCode
    message: str = Field(min_length=1, max_length=400)
    target_node: str | None = None
    resource_type: str | None = None
    recoverable: bool = True


class BudgetLimits(BaseModel):
    """Explicit limits used at platform, root, node and provider boundaries."""

    max_tokens: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, gt=0)
    max_nodes: int | None = Field(default=None, ge=1)
    max_provider_calls: int | None = Field(default=None, ge=1)
    # Provider ceilings are opt-in per provider. Root limits still apply to
    # every provider call; these prevent one fallback target from consuming a
    # disproportionate share of a root's allocation.
    provider_max_tokens: dict[str, int] = Field(default_factory=dict)


class BudgetUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    provider_calls: int = Field(default=0, ge=0)
    nodes: int = Field(default=0, ge=0)
    reserved_tokens: int = Field(default=0, ge=0)


class EventEnvelope(BaseModel):
    """The only externally serialised SSE envelope.

    ``sequence`` is a per-run PostgreSQL sequence, and is emitted as SSE ``id``.
    Event-specific data lives in ``payload`` so the event vocabulary stays fixed.
    """

    model_config = ConfigDict(use_enum_values=True)

    workflow_run_id: UUID | str
    sequence: int = Field(ge=1)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: ExecutionMode | None = None
    requested_provider: str | None = None
    requested_model: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None

    @field_validator("payload")
    @classmethod
    def forbid_internal_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"prompt", "messages", "reasoning", "reasoning_content", "api_key", "authorization"}
        overlap = forbidden.intersection(payload)
        if overlap:
            raise ValueError(f"event payload includes forbidden fields: {sorted(overlap)!r}")
        return payload

    @property
    def terminal(self) -> bool:
        return self.event_type in {EventType.DONE, EventType.ERROR}

    def as_sse_payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "workflow_run_id": str(self.workflow_run_id),
            "sequence": self.sequence,
            "event_type": str(self.event_type),
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }
        for key in (
            "mode",
            "requested_provider",
            "requested_model",
            "actual_provider",
            "actual_model",
        ):
            value = getattr(self, key)
            if value is not None:
                result[key] = str(value)
        return result


class RuntimePortDefinition(BaseModel):
    name: str
    timeout_seconds: float = Field(gt=0)


class WorkflowActionDefinition(BaseModel):
    name: str
    input_schema_name: str
    output_schema_name: str
    idempotency_required: bool = True


class ModelToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: Literal["low", "medium", "high"] = "low"
    permission: Literal["ALLOW", "ASK", "DENY"] = "DENY"


__all__ = [
    "ArtifactRef",
    "ArtifactStatus",
    "ErrorCode",
    "EventEnvelope",
    "EventType",
    "EvidenceRef",
    "BudgetLimits",
    "BudgetUsage",
    "ExecutionMode",
    "ModelToolDefinition",
    "ProviderCallOutcome",
    "ProviderCallStatus",
    "ProviderSelection",
    "RunStatus",
    "RuntimeErrorDetail",
    "RuntimePortDefinition",
    "RuntimeSemanticVersion",
    "QualityDefect",
    "QualityDefectCode",
    "SSE_EVENT_TYPES",
    "StepStatus",
    "TERMINAL_RUN_STATUSES",
    "TERMINAL_STEP_STATUSES",
    "WorkflowActionDefinition",
]
