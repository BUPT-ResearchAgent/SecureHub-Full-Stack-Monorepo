# Status: planned

"""Per task brief §6.1 — ChunkingService splits a document into ``chunks``
rows with ``embedding_status='pending'``. EmbeddingService later fills the
vectors.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ChunkingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def chunk_document(
        self,
        document_id: UUID,
        *,
        size: int = 600,
        overlap: int = 100,
    ) -> Sequence[UUID]:
        """Return the freshly inserted chunk ids in chunk-index order."""
        raise NotImplementedError("planned: P1 — implements §6.1 chunking pipeline")
