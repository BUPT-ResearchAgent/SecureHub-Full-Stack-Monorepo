# Status: partial-real

"""DTOs for the fixed multi-agent workflow Run API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


WorkflowExecutionMode = Literal["fixture", "real", "fallback"]
WorkflowRunStatus = Literal[
    "queued",
    "running",
    "cancelling",
    "succeeded",
    "failed",
    "blocked",
    "cancelled",
]
WorkflowNodeStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "skipped",
    "cancelled",
]


class WorkflowRunStartRequest(BaseModel):
    workflow: Literal["course_learning_minimal"] = "course_learning_minimal"
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    topic: str = Field(default="SQL 注入", min_length=1)
    goal: str = Field(default="为初学者生成证据驱动的学习路径和入门资源", min_length=1)
    mode: Literal["fixture", "real"] = "fixture"
    provider: str | None = None
    stream: bool = True

    @model_validator(mode="after")
    def validate_mode_provider(self) -> "WorkflowRunStartRequest":
        if self.mode == "fixture":
            if self.provider not in {None, "fixture"}:
                raise ValueError("fixture mode requires provider='fixture'")
            self.provider = "fixture"
        elif self.provider == "fixture":
            raise ValueError("real mode cannot use provider='fixture'")
        return self


class AgentManifestItem(BaseModel):
    name: str
    role_description: str
    capability_vector: list[float]
    tools: list[str]
    risk_level: str
    skills: list[str]


class AgentManifestResponse(BaseModel):
    agents: list[AgentManifestItem]
    total: int


class WorkflowNodeResponse(BaseModel):
    node_id: str
    agent_name: str
    skill_name: str
    status: WorkflowNodeStatus
    agent_run_id: UUID | None = None
    persistence: Literal["registry", "agent_runs"] = "registry"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    quality_score: float | None = None
    evidence_count: int = 0


class WorkflowRunStartResponse(BaseModel):
    run_id: UUID
    workflow: str
    status: WorkflowRunStatus
    events_url: str
    cancel_url: str
    mode: WorkflowExecutionMode
    provider: str
    model: str | None = None


class WorkflowRunResponse(BaseModel):
    run_id: UUID
    workflow: str
    status: WorkflowRunStatus
    mode: WorkflowExecutionMode
    provider: str
    model: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_requested: bool
    child_runs: list[WorkflowNodeResponse]
    child_run_count: int
    final_output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class WorkflowRunCancelResponse(BaseModel):
    run_id: UUID
    status: WorkflowRunStatus
    cancel_requested: bool = True
