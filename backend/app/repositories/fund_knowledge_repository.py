# Status: real

"""Read-only queries for the shared fund knowledge domain."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document


FUND_DOMAIN = "fund"


class FundKnowledgeRepository:
    """Uses the existing documents/chunks tables; no fund shadow store exists."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ready_chunk_count(self) -> int:
        rows = await self.session.scalars(
            select(Chunk.id).where(Chunk.domain == FUND_DOMAIN, Chunk.embedding_status == "ready")
        )
        return len(list(rows))

    async def candidate_documents(self, *, limit: int = 20) -> Sequence[Document]:
        rows = await self.session.scalars(
            select(Document)
            .where(Document.domain == FUND_DOMAIN, Document.status == "ready")
            .order_by(Document.fetched_at.desc().nulls_last())
            .limit(limit)
        )
        return list(rows)


__all__ = ["FUND_DOMAIN", "FundKnowledgeRepository"]
