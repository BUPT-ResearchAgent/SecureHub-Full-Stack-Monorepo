# Status: real

"""Read models for the product course surface.

The repository deliberately composes the durable knowledge, resource, and
profile tables instead of creating course-specific mirrors of those records.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.resource.generated_resource import GeneratedResource


class CourseLearningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_courses(self, *, domain: str | None = None) -> Sequence[Course]:
        statement = select(Course).order_by(Course.code)
        if domain is not None:
            statement = statement.where(Course.domain == domain)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_course(self, course_id: UUID) -> Course | None:
        return await self.session.get(Course, course_id)

    async def list_nodes(self, course_id: UUID) -> Sequence[KnowledgeNode]:
        result = await self.session.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(KnowledgeNode.level.asc().nulls_last(), KnowledgeNode.name)
        )
        return result.scalars().all()

    async def list_edges(self, node_ids: Sequence[UUID]) -> Sequence[KnowledgeEdge]:
        if not node_ids:
            return []
        result = await self.session.execute(
            select(KnowledgeEdge)
            .where(
                KnowledgeEdge.source_id.in_(node_ids),
                KnowledgeEdge.target_id.in_(node_ids),
                KnowledgeEdge.edge_type == "prerequisite",
            )
            .order_by(KnowledgeEdge.source_id, KnowledgeEdge.target_id)
        )
        return result.scalars().all()

    async def list_evidence_documents(self, domain: str) -> Sequence[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.domain == domain, Document.status == "ready")
            .order_by(Document.title)
        )
        return result.scalars().all()

    async def resource_counts(
        self,
        *,
        course_ids: Sequence[UUID],
        user_id: UUID | None = None,
    ) -> dict[UUID, int]:
        if not course_ids:
            return {}
        statement = (
            select(GeneratedResource.kp_id, func.count(GeneratedResource.id))
            .where(
                GeneratedResource.course_id.in_(course_ids),
                GeneratedResource.kp_id.is_not(None),
                # ArtifactSaga marks accepted production artifacts ``active``.
                # ``ready`` remains for legacy resource rows created before
                # that lifecycle naming was frozen.
                GeneratedResource.status.in_(("active", "ready")),
            )
            .group_by(GeneratedResource.kp_id)
        )
        if user_id is not None:
            statement = statement.where(GeneratedResource.user_id == user_id)
        result = await self.session.execute(statement)
        return {kp_id: int(count) for kp_id, count in result.all() if kp_id is not None}
