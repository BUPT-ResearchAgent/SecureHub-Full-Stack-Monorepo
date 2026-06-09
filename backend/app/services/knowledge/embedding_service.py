# Status: planned

"""Per task brief §6.1 — EmbeddingService walks pending chunks, calls the
embedding provider (BGE-M3 / bge-large-zh / Spark embedding) and updates
``chunks.embedding`` + ``embedding_status``.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class EmbeddingBatchResult:
    succeeded: int
    failed: int


class EmbeddingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def embed_pending(
        self,
        *,
        domain: str | None = None,
        batch_size: int = 64,
    ) -> EmbeddingBatchResult:
        raise NotImplementedError("planned: P1 — implements §6.1 embedding pipeline")
