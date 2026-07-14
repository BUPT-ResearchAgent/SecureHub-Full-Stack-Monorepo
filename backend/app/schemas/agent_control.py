# Status: real

"""DTOs for the durable, versioned Workflow Run control plane.

Legacy Agent-Run fields remain accepted during rollout, but every response now
uses the durable ``workflow_runs.id`` as its sole public root identifier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


WorkflowExecutionMode = Literal["fixture", "real"]
WorkflowRunStatus = Literal[
    "queued",
    "running",
    "reworking",
    "pausing",
    "paused",
    "waiting_approval",
    "cancelling",
    "succeeded",
    "failed",
    "blocked",
    "cancelled",
]
WorkflowNodeStatus = Literal[
    "pending",
    "ready",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "skipped",
    "cancelled",
]


class WorkflowRunStartRequest(BaseModel):
    workflow: str = Field(min_length=1, max_length=120)
    user_id: str = Field(min_length=1)
    course_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    mode: WorkflowExecutionMode = "real"
    provider: str | None = None
    model: str | None = None
    stream: bool = True
    budget: dict[str, Any] = Field(default_factory=dict)

    # Compatibility fields used by the Agent Run v0.4 endpoint.  They are
    # folded into ``input`` and never form another durable root shape.
    topic: str | None = None
    goal: str | None = None

    @model_validator(mode="after")
    def normalise_mode_and_input(self) -> "WorkflowRunStartRequest":
        if self.mode == "fixture":
            if self.provider not in {None, "fixture"}:
                raise ValueError("fixture mode requires provider='fixture'")
            self.provider = "fixture"
            self.model = self.model or "fixture-v1"
        elif self.provider == "fixture":
            raise ValueError("real mode cannot use provider='fixture'")
        merged = dict(self.input)
        if self.course_id is not None:
            merged.setdefault("course_id", self.course_id)
        if self.topic is not None:
            merged.setdefault("topic", self.topic)
        if self.goal is not None:
            merged.setdefault("goal", self.goal)
        self.input = merged
        return self


class AgentManifestItem(BaseModel):
    name: str
    stable_id: UUID | None = None
    role_description: str
    capability_vector: list[float]
    tools: list[str]
    risk_level: str
    skills: list[str]


class AgentManifestResponse(BaseModel):
    agents: list[AgentManifestItem]
    total: int
    catalog_version: str = "production-catalog-v1"


class WorkflowNodeResponse(BaseModel):
    node_id: str
    status: WorkflowNodeStatus
    agent_name: str | None = None
    skill_name: str | None = None
    step_attempt_id: UUID | None = None
    agent_run_id: UUID | None = None
    attempt: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    quality_score: float | None = None
    error_code: str | None = None


class WorkflowRunStartResponse(BaseModel):
    run_id: UUID
    workflow: str
    status: WorkflowRunStatus
    events_url: str
    cancel_url: str
    mode: WorkflowExecutionMode
    requested_provider: str | None = None
    requested_model: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None
    # Legacy aliases are intentionally duplicated only in the HTTP response.
    provider: str | None = None
    model: str | None = None


class WorkflowRunResponse(BaseModel):
    run_id: UUID
    workflow: str
    workflow_version: str | None = None
    status: WorkflowRunStatus
    mode: WorkflowExecutionMode
    requested_provider: str | None = None
    requested_model: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_requested: bool = False
    child_runs: list[WorkflowNodeResponse] = Field(default_factory=list)
    nodes: list[WorkflowNodeResponse] = Field(default_factory=list)
    child_run_count: int = 0
    final_output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class WorkflowRunControlResponse(BaseModel):
    run_id: UUID
    status: WorkflowRunStatus
    compatibility: Literal["compatible", "migratable", "incompatible"] | None = None


class WorkflowApprovalDecisionRequest(BaseModel):
    approved: bool
    decision: dict[str, Any] = Field(default_factory=dict)


class WorkflowApprovalResponse(BaseModel):
    approval_id: UUID
    run_id: UUID
    node_id: str | None = None
    kind: str
    status: Literal["pending", "approved", "rejected"]
    request: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunCancelResponse(WorkflowRunControlResponse):
    cancel_requested: bool = True


__all__ = [
    "AgentManifestItem",
    "AgentManifestResponse",
    "WorkflowRunCancelResponse",
    "WorkflowApprovalDecisionRequest",
    "WorkflowApprovalResponse",
    "WorkflowRunControlResponse",
    "WorkflowRunResponse",
    "WorkflowRunStartRequest",
    "WorkflowRunStartResponse",
]
