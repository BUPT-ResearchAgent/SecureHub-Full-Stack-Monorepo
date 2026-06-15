# Status: real

"""Shared types for the skill harness layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar
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


@dataclass(slots=True)
class SkillContract:
    """Legacy BaseSkill contract kept for dev-era skill tests."""

    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_tools: list[str] = field(default_factory=list)
    required_domains: list[str] = field(default_factory=list)
    evidence_floor: int = 3
    guardrails: list[str] = field(default_factory=list)
    quality_check: bool = True
    log_run: bool = True
    retry: dict[str, Any] = field(default_factory=dict)
    fallback: str | None = "mock"


class BaseSkill(ABC):
    """Legacy skill interface supported alongside the new SkillSpec API."""

    name: ClassVar[str]
    agent_name: ClassVar[str]
    contract: ClassVar[SkillContract]

    @abstractmethod
    async def run(self, inp: BaseModel, ctx: Any) -> BaseModel:
        raise NotImplementedError


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
