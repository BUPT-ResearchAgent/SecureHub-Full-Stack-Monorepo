# Status: real

"""Repository base classes for data-layer v2.

Per task brief §5.1 a repository **only** owns SQL — no prompt composition,
no LLM call, no orchestration. Services orchestrate; repositories read and
write. The base class therefore exposes nothing more than an :class:`AsyncSession`
binding.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository:
    """Hold the session every concrete repository needs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session


class UUIDPKRepository(BaseRepository, Generic[ModelT]):
    """Mixin: trivial ``get_by_id`` for tables with a single UUID PK column ``id``."""

    model: type[ModelT]

    async def get_by_id(self, row_id: UUID) -> ModelT | None:
        result = await self.session.execute(select(self.model).where(self.model.id == row_id))
        return result.scalar_one_or_none()
