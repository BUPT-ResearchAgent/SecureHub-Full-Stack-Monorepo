# Status: real

"""ResourceGenerationService — generated_resources 表的写入者。

每次 skill 生成学习资源（doc/ppt/mindmap/quiz/lab/video/readings）后，
由 Harness 或 service 层调用 register()，将资源内容、引用链路落库。
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ResourceGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self,
        *,
        resource_type: str,
        title: str,
        user_id: UUID | None,
        course_id: UUID | None,
        kp_id: UUID | None,
        agent_run_id: UUID | None,
        content: dict[str, Any] | None,
        object_key: str | None,
        evidence_chunk_ids: list[UUID],
        quality_score: float | None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """写入 generated_resources，返回 resource_id。"""
        from app.db.models.resource.generated_resource import GeneratedResource

        resource = GeneratedResource(
            id=uuid4(),
            user_id=user_id,
            course_id=course_id,
            kp_id=kp_id,
            agent_run_id=agent_run_id,
            resource_type=resource_type,
            title=title,
            content=content or {},
            object_key=object_key,
            evidence_chunk_ids=evidence_chunk_ids,
            quality_score=quality_score,
            status="ready",
            metadata_=metadata or {},
        )
        self.session.add(resource)
        await self.session.flush()
        return resource.id

    async def mark_status(self, resource_id: UUID, status: str) -> None:
        """更新资源状态（ready / processing / failed）。"""
        from app.db.models.resource.generated_resource import GeneratedResource

        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None:
            logger.warning("mark_status: resource_id %s not found", resource_id)
            return
        resource.status = status
        await self.session.flush()
