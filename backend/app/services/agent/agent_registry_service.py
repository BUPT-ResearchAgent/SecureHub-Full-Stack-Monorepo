# Status: planned

"""Per task brief §6.3 — AgentRegistryService reads ``agents`` + ``agent_skills``
and produces the agent-manifest payload the runtime router needs."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class AgentManifest:
    agent_id: UUID
    name: str
    role_description: str
    risk_level: str
    tools: list[str]
    skills: list[str]


class AgentRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_manifests(self) -> Sequence[AgentManifest]:
        raise NotImplementedError("planned: P0")

    async def get_manifest(self, name: str) -> AgentManifest | None:
        raise NotImplementedError("planned: P0")

    async def capability_vector(self, name: str) -> dict[str, Any] | None:
        raise NotImplementedError("planned: P1")
