# Status: real

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SkillContract(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_tools: list[str]
    required_domains: list[str]
    evidence_floor: int = 3
    guardrails: list[str]
    quality_check: bool = True
    log_run: bool = True
    fixtures: dict[str, Any] | None = None
    timeout_seconds: float = 60
    retry: dict[str, int | float] = Field(default_factory=lambda: {"max": 1, "backoff": 1.0})
    fallback: str | None = None


class BaseSkill(ABC):
    name: ClassVar[str]
    agent_name: ClassVar[str]
    contract: ClassVar[SkillContract]

    @abstractmethod
    async def run(self, inp: BaseModel, ctx: "HarnessContext") -> BaseModel:
        raise NotImplementedError
