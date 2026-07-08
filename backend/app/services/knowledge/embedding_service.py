# Status: real

"""Knowledge-layer wrapper around the recoverable embedding job."""

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
        batch_size: int = 10,
    ) -> EmbeddingBatchResult:
        from app.knowledge.loaders.embed_chunks import embed_pending_chunks

        result = await embed_pending_chunks(domain=domain, batch_size=batch_size)
        return EmbeddingBatchResult(succeeded=result.embedded, failed=result.failed)
