# Status: real

"""Shared types for the skill harness layer."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    success = "success"
    failed = "failed"
    blocked = "blocked"


class EvidenceCard(BaseModel):
    """A normalized evidence record exposed to LLM prompts and frontend."""

    chunk_id: str
    document_id: str | None = None
    domain: str = "course_websec"
    source: str | None = None
    excerpt: str = ""
    reliability: float = 0.0
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillIO(BaseModel):
    """Generic base for skill inputs and outputs used across the harness."""

    pass


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0
    model: str = "unknown"


class HarnessTelemetry(BaseModel):
    """Per-skill telemetry collected during a harness run."""

    duration_ms: int = 0
    evidence_count: int = 0
    quality_score: float | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    status: RunStatus = RunStatus.success
    agent_id: UUID | str | None = None
    skill_id: UUID | str | None = None
