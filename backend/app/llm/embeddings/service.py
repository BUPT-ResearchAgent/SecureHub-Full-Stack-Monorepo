# Status: real

from __future__ import annotations

from collections.abc import Sequence

from app.llm.embeddings.base import EmbeddingProvider, EmbeddingResult
from app.llm.embeddings.factory import create_embedding_provider


class EmbeddingService:
    """Semantic embedding service used by RAG and ingestion."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self.provider = provider or create_embedding_provider()

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        return await self.provider.embed_documents(texts)

    async def embed_query(self, text: str) -> EmbeddingResult:
        return await self.provider.embed_query(text)

    async def aclose(self) -> None:
        await self.provider.aclose()
