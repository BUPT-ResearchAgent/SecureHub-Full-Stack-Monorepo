# Status: planned

"""Per task brief §6.3 — SkillRegistryService owns the prompt-template /
version / output-schema lookup for every ``agent_skills`` row.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class SkillSpec:
    skill_id: UUID
    agent_name: str
    skill_name: str
    prompt_template: str
    applicable_domains: list[str]
    required_tools: list[str]
    output_schema: dict[str, Any]
    version: int


class SkillRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_skill(
        self, agent_name: str, skill_name: str, *, version: int | None = None
    ) -> SkillSpec | None:
        raise NotImplementedError("planned: P0")

    async def list_skills(self, agent_name: str) -> Sequence[SkillSpec]:
        raise NotImplementedError("planned: P0")
