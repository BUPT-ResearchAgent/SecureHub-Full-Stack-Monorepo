# Status: [planned]

from uuid import UUID

from pydantic import BaseModel


class KnowledgeGraphNode(BaseModel):
    id: UUID
    name: str
    level: int


class KnowledgeGraphService:
    async def prerequisites(self, kp_id: UUID) -> list[KnowledgeGraphNode]:
        raise NotImplementedError("TODO: load prerequisite nodes for a knowledge point")

    async def descendants(self, kp_id: UUID) -> list[KnowledgeGraphNode]:
        raise NotImplementedError("TODO: load descendant knowledge points")

    async def topological_order(self, course_id: UUID) -> list[KnowledgeGraphNode]:
        raise NotImplementedError("TODO: compute topological order from kp_prerequisites")
