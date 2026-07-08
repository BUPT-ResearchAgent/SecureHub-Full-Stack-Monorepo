# Status: real

"""Embedding provider package."""

from app.llm.embeddings.base import EmbeddingProvider, EmbeddingResult, EmbeddingUsage
from app.llm.embeddings.factory import create_embedding_provider
from app.llm.embeddings.service import EmbeddingService

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "EmbeddingService",
    "EmbeddingUsage",
    "create_embedding_provider",
]
