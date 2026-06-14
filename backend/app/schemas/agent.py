# Status: real

"""Pydantic schemas for agent registry, run trace, and Day 0 contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

JsonObject = dict[str, object]


class AgentRunDTO(BaseModel):
    id: str
    workflow_name: str
    agent_name: str
    skill_name: str
    status: str
    duration_ms: int | None = None
    quality_score: float | None = None
    created_at: datetime


class AgentRunDetailDTO(AgentRunDTO):
    input_summary: JsonObject = Field(default_factory=dict)
    output_summary: JsonObject = Field(default_factory=dict)
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    parent_run_id: str | None = None
    token_usage: JsonObject | None = None


class AgentRunListResponse(BaseModel):
    items: list[AgentRunDTO]
    total: int
    page: int
    page_size: int


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
    input_summary: JsonObject = Field(default_factory=dict)
    output_summary: JsonObject = Field(default_factory=dict)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    quality_score: float | None = None
    duration_ms: int | None = None
    created_at: datetime


class AgentRunListOut(BaseModel):
    items: list[AgentRunOut]
    total: int
