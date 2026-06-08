# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_task import LearningTask
from app.repositories.base import UUIDPKRepository


class LearningPathRepository(UUIDPKRepository[LearningPath]):
    """Owns ``learning_paths`` + ``learning_tasks`` (P1 extension)."""

    model = LearningPath

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> Sequence[LearningPath]:
        stmt = select(LearningPath).where(LearningPath.user_id == user_id)
        if status is not None:
            stmt = stmt.where(LearningPath.status == status)
        stmt = stmt.order_by(LearningPath.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_tasks(self, path_id: UUID) -> Sequence[LearningTask]:
        stmt = (
            select(LearningTask)
            .where(LearningTask.path_id == path_id)
            .order_by(LearningTask.order_index)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_path(
        self,
        *,
        path_id: UUID,
        user_id: UUID,
        course_id: UUID,
        title: str,
        objective: str | None = None,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> LearningPath:
        row = LearningPath(
            id=path_id,
            user_id=user_id,
            course_id=course_id,
            title=title,
            objective=objective,
            status=status,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_task(
        self,
        *,
        task_id: UUID,
        path_id: UUID,
        title: str,
        task_type: str,
        order_index: int,
        kp_id: UUID | None = None,
        status: str = "todo",
        metadata: dict[str, Any] | None = None,
    ) -> LearningTask:
        row = LearningTask(
            id=task_id,
            path_id=path_id,
            kp_id=kp_id,
            title=title,
            task_type=task_type,
            order_index=order_index,
            status=status,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
