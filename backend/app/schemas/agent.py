# Status: partial-real

"""Pydantic schemas for the ``/api/v1/agents`` + ``/api/v1/agent-runs``
surfaces (data-layer v2).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentOut(BaseModel):
    id: UUID
    name: str
    role_description: str
    risk_level: str
    tools: list[str]
    enabled: bool


class AgentListOut(BaseModel):
    items: list[AgentOut]
    total: int


class AgentRunOut(BaseModel):
    id: UUID
    workflow_name: str
    agent_id: UUID | None = None
    skill_id: UUID | None = None
    user_id: UUID | None = None
    parent_run_id: UUID | None = None
    status: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    quality_score: float | None = None
    duration_ms: int | None = None
    created_at: datetime


class AgentRunListOut(BaseModel):
    items: list[AgentRunOut]
    total: int
