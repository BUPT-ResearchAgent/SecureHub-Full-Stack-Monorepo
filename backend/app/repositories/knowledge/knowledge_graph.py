# Status: real

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.repositories.base import BaseRepository


class KnowledgeGraphRepository(BaseRepository):
    """Combined access for ``knowledge_nodes`` + ``knowledge_edges`` so the
    learning-path service can walk the graph through a single port.
    """

    # ----- nodes -----
    async def get_node(self, node_id: UUID) -> KnowledgeNode | None:
        result = await self.session.execute(
            select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def list_nodes(
        self,
        *,
        domain: str | None = None,
        course_id: UUID | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[KnowledgeNode]:
        stmt = select(KnowledgeNode)
        if domain is not None:
            stmt = stmt.where(KnowledgeNode.domain == domain)
        if course_id is not None:
            stmt = stmt.where(KnowledgeNode.course_id == course_id)
        stmt = stmt.order_by(KnowledgeNode.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_node(
        self,
        *,
        node_id: UUID,
        domain: str,
        name: str,
        course_id: UUID | None = None,
        description: str | None = None,
        node_type: str = "concept",
        level: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeNode:
        row = KnowledgeNode(
            id=node_id,
            domain=domain,
            course_id=course_id,
            name=name,
            description=description,
            node_type=node_type,
            level=level,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def bulk_create_nodes(
        self, rows: Iterable[KnowledgeNode]
    ) -> Sequence[KnowledgeNode]:
        materialised = list(rows)
        self.session.add_all(materialised)
        await self.session.flush()
        return materialised

    # ----- edges -----
    async def list_edges(
        self,
        *,
        source_id: UUID | None = None,
        edge_type: str | None = None,
    ) -> Sequence[KnowledgeEdge]:
        stmt = select(KnowledgeEdge)
        if source_id is not None:
            stmt = stmt.where(KnowledgeEdge.source_id == source_id)
        if edge_type is not None:
            stmt = stmt.where(KnowledgeEdge.edge_type == edge_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_edge(
        self,
        *,
        source_id: UUID,
        target_id: UUID,
        edge_type: str = "prerequisite",
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEdge:
        row = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def bulk_create_edges(
        self, rows: Iterable[KnowledgeEdge]
    ) -> Sequence[KnowledgeEdge]:
        materialised = list(rows)
        self.session.add_all(materialised)
        await self.session.flush()
        return materialised
