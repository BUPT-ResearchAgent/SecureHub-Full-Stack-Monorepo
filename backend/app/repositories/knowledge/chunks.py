# Status: real

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.knowledge.chunk import Chunk
from app.repositories.base import UUIDPKRepository


class ChunkRepository(UUIDPKRepository[Chunk]):
    """P0 methods per task brief §5.2.

    ``search_vector`` is intentionally PG-only (depends on pgvector cosine
    distance). On non-PG dialects callers should fall back to
    ``search_by_domain`` plus client-side reranking.
    """

    model = Chunk

    async def bulk_create(self, rows: Iterable[Chunk]) -> Sequence[Chunk]:
        materialised = list(rows)
        self.session.add_all(materialised)
        await self.session.flush()
        return materialised

    async def list_by_document(self, document_id: UUID) -> Sequence[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_by_domain(
        self,
        domain: str,
        *,
        embedding_status: str | None = "ready",
        limit: int = 20,
    ) -> Sequence[Chunk]:
        stmt = select(Chunk).where(Chunk.domain == domain)
        if embedding_status is not None:
            stmt = stmt.where(Chunk.embedding_status == embedding_status)
        stmt = stmt.order_by(Chunk.chunk_index).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_vector(
        self,
        query_embedding: list[float],
        *,
        domain: str | None = None,
        top_k: int = 8,
    ) -> Sequence[Chunk]:
        """Approximate-nearest-neighbour search on ``chunks.embedding``.

        Implemented via pgvector cosine distance; on SQLite this raises
        :class:`NotImplementedError` because the BLOB-typed fallback column
        has no distance operator. The retrieval service is responsible for
        catching the error and degrading to ``search_by_domain``.
        """
        bind = await self.session.connection()
        if bind.dialect.name != "postgresql":
            raise NotImplementedError(
                "vector search requires PostgreSQL + pgvector; SQLite fallback "
                "should call search_by_domain instead"
            )
        from sqlalchemy import text

        params: dict[str, Any] = {"q": query_embedding, "k": top_k}
        where = ""
        if domain is not None:
            where = "WHERE domain = :domain AND embedding_status = 'ready'"
            params["domain"] = domain
        else:
            where = "WHERE embedding_status = 'ready'"
        stmt = text(
            f"SELECT id FROM chunks {where} "
            "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
        )
        ids = (await self.session.execute(stmt, params)).scalars().all()
        if not ids:
            return []
        result = await self.session.execute(select(Chunk).where(Chunk.id.in_(ids)))
        rows = {row.id: row for row in result.scalars().all()}
        return [rows[i] for i in ids if i in rows]

    async def update_embedding(
        self,
        chunk_id: UUID,
        *,
        embedding: list[float],
        status: str = "ready",
        token_count: int | None = None,
    ) -> Chunk | None:
        row = await self.get_by_id(chunk_id)
        if row is None:
            return None
        row.embedding = embedding
        row.embedding_status = status
        if token_count is not None:
            row.token_count = token_count
        await self.session.flush()
        return row
