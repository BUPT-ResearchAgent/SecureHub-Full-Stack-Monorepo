# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.resource.generated_resource import GeneratedResource
from app.repositories.base import UUIDPKRepository


class GeneratedResourceRepository(UUIDPKRepository[GeneratedResource]):
    """P0 methods per task brief §5.2."""

    model = GeneratedResource

    async def create(
        self,
        *,
        resource_id: UUID,
        resource_type: str,
        title: str,
        user_id: UUID | None = None,
        course_id: UUID | None = None,
        kp_id: UUID | None = None,
        agent_run_id: UUID | None = None,
        content: dict[str, Any] | None = None,
        object_key: str | None = None,
        evidence_chunk_ids: list[UUID] | None = None,
        quality_score: float | None = None,
        status: str = "ready",
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedResource:
        row = GeneratedResource(
            id=resource_id,
            user_id=user_id,
            course_id=course_id,
            kp_id=kp_id,
            agent_run_id=agent_run_id,
            resource_type=resource_type,
            title=title,
            content=content or {},
            object_key=object_key,
            evidence_chunk_ids=evidence_chunk_ids or [],
            quality_score=quality_score,
            status=status,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_user_course(
        self,
        *,
        user_id: UUID | None = None,
        course_id: UUID | None = None,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[GeneratedResource]:
        stmt = select(GeneratedResource)
        if user_id is not None:
            stmt = stmt.where(GeneratedResource.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(GeneratedResource.course_id == course_id)
        if resource_type is not None:
            stmt = stmt.where(GeneratedResource.resource_type == resource_type)
        stmt = (
            stmt.order_by(GeneratedResource.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self, resource_id: UUID, status: str
    ) -> GeneratedResource | None:
        row = await self.get_by_id(resource_id)
        if row is None:
            return None
        row.status = status
        await self.session.flush()
        return row
