# Status: [planned]

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceHit(BaseModel):
    chunk_id: UUID | str
    document_id: UUID | str | None = None
    domain: str
    chunk_text: str
    source: str | None = None
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


async def retrieve(
    query: str,
    *,
    domain: str = "course_websec",
    top_k: int = 8,
    filter: dict[str, Any] | None = None,
) -> list[EvidenceHit]:
    try:
        from sqlalchemy import select
        from app.db.models.knowledge.chunk import Chunk
        from app.db.session import get_sessionmaker
        from app.llm.embedding import embed_one

        embedding = await embed_one(query)
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            stmt = (
                select(Chunk)
                .where(Chunk.domain == domain)
                .order_by(Chunk.embedding.cosine_distance(embedding))
                .limit(top_k)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                EvidenceHit(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    domain=row.domain,
                    chunk_text=row.chunk_text,
                    source=row.metadata_.get("source") if row.metadata_ else None,
                    reliability=row.metadata_.get("reliability", 0.8) if row.metadata_ else 0.8,
                    score=0.0,
                    metadata=row.metadata_ or {},
                )
                for row in rows
            ]
    except Exception:
        import logging
        logging.getLogger(__name__).debug("RAG retrieve: DB not ready, returning empty list")
        return []
