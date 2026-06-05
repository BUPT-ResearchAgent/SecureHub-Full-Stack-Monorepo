# Status: [planned]

from abc import ABC, abstractmethod
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InsufficientEvidence(RuntimeError):
    pass


class SafetyBlocked(RuntimeError):
    pass


class ToolUnavailable(RuntimeError):
    pass


class AgentCapability(BaseModel):
    policy: float = 0.0
    hot: float = 0.0
    job: float = 0.0
    competition: float = 0.0
    planning: float = 0.0
    topic: float = 0.0
    doc: float = 0.0
    task: float = 0.0
    eval: float = 0.0

    def as_vector(self) -> list[float]:
        base = [
            self.policy,
            self.hot,
            self.job,
            self.competition,
            self.planning,
            self.topic,
            self.doc,
            self.task,
            self.eval,
        ]
        return base + [0.0] * (64 - len(base))


class SkillContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str | None = None
    workflow_name: str = "course_learning"
    persona_summary: str = ""
    stream: bool = False
    config: Any = Field(default=None)

    async def log_run(
        self,
        *,
        agent_id: UUID | str | None = None,
        skill_id: UUID | str | None = None,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID | str],
        quality_score: float | None = None,
        status: str = "success",
        duration_ms: int | None = None,
        token_usage: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError("TODO: write agent run through runtime.logger")


class BaseSkill(ABC):
    name: ClassVar[str]
    applicable_domains: ClassVar[list[str]] = []
    output_schema: ClassVar[type[BaseModel] | None] = None
    agent_id: UUID | str | None = None
    skill_id: UUID | str | None = None

    @abstractmethod
    async def run(self, inp: BaseModel, ctx: SkillContext) -> BaseModel:
        raise NotImplementedError("TODO: implement skill execution")


class BaseAgent(ABC):
    name: ClassVar[str]
    role_description: ClassVar[str]
    capability_vector: ClassVar[AgentCapability]
    tools: ClassVar[list[str]] = ["rag.retrieve", "llm.xfyun"]
    risk_level: ClassVar[str] = "low"
    skills: ClassVar[dict[str, type[BaseSkill]]] = {}

    @classmethod
    def manifest(cls) -> dict[str, Any]:
        return {
            "name": cls.name,
            "role_description": cls.role_description,
            "capability_vector": cls.capability_vector.as_vector(),
            "tools": cls.tools,
            "risk_level": cls.risk_level,
            "skills": list(cls.skills.keys()),
        }
