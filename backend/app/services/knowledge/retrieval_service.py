# Status: planned

"""Per task brief §6.1 — RetrievalService is the single entry point every
generative skill must call before composing a prompt (rule §3.6). It owns the
BM25 + vector + RRF + rerank chain.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ChunkHit:
    chunk_id: UUID
    document_id: UUID
    title: str
    snippet: str
    score: float
    metadata: dict[str, Any]


class RetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def retrieve(
        self,
        query: str,
        *,
        domain: str,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> Sequence[ChunkHit]:
        raise NotImplementedError("planned: P0 — implements §6.1 hybrid retrieval")
