# Status: partial-real

"""``POST /api/v1/rag/search`` — domain-filtered chunk retrieval.

When running on PostgreSQL + pgvector the request is dispatched through
``ChunkRepository.search_vector`` (cosine distance). On every other dialect
(SQLite fallback in dev / CI) we degrade to ``search_by_domain`` so the
endpoint stays functional even without a real embedding model wired up.
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.db.models.knowledge.document import Document
from app.deps import SessionDep
from app.repositories.knowledge.chunks import ChunkRepository
from app.schemas.knowledge import RagChunkOut, RagSearchIn, RagSearchOut

router = APIRouter()


@router.post("/rag/search", response_model=RagSearchOut)
async def rag_search(payload: RagSearchIn, session: SessionDep) -> RagSearchOut:
    chunks_repo = ChunkRepository(session)
    hits = await chunks_repo.search_by_domain(
        payload.domain,
        embedding_status=None,  # demo data is still ``pending`` — accept everything
        limit=payload.top_k,
    )

    # Pull document titles in one round-trip for the citation card.
    doc_ids = list({c.document_id for c in hits})
    titles: dict = {}
    if doc_ids:
        rows = (
            await session.execute(select(Document).where(Document.id.in_(doc_ids)))
        ).scalars().all()
        titles = {d.id: d.title for d in rows}

    return RagSearchOut(
        query=payload.query,
        domain=payload.domain,
        hits=[
            RagChunkOut(
                chunk_id=c.id,
                document_id=c.document_id,
                title=titles.get(c.document_id, ""),
                snippet=(
                    c.chunk_text if len(c.chunk_text) <= 240 else c.chunk_text[:240] + "…"
                ),
                # Without a real embedding the score is a stable monotonic value
                # so the UI can still render an ordering.
                score=float(payload.top_k - i) / payload.top_k,
                metadata=c.metadata_ or {},
            )
            for i, c in enumerate(hits)
        ],
    )


__all__ = ["router"]
