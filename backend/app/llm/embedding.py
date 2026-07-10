# Status: real

"""Backward-compatible embedding facade.

New code should use ``app.llm.embeddings.EmbeddingService``. The legacy
``embed_one`` / ``embed_texts`` helpers remain only for old call sites.
They never fall back to hash vectors in production.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.llm.embeddings.service import EmbeddingService


class EmbeddingInput(BaseModel):
    text: str = Field(min_length=1)
    domain: str = "course_websec"


class EmbeddingBatch(BaseModel):
    items: list[EmbeddingInput]
    model: str = "text-embedding-v4"
    dimension: int = 1024


_SERVICE: EmbeddingService | None = None


async def embed_texts(batch: EmbeddingBatch) -> list[list[float]]:
    """生成 ``batch.items`` 对应的向量列表。"""
    settings = get_settings()
    target_dim = batch.dimension or settings.EMBEDDING_DIM or 1024
    if target_dim != settings.EMBEDDING_DIM:
        raise ValueError(
            f"requested embedding dimension {target_dim} does not match "
            f"settings.EMBEDDING_DIM={settings.EMBEDDING_DIM}"
        )
    result = await get_embedding_service().embed_documents([item.text for item in batch.items])
    return result.vectors


def get_embedding_service() -> EmbeddingService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = EmbeddingService()
    return _SERVICE


def reset_embedding_service() -> None:
    global _SERVICE
    _SERVICE = None


async def embed_one(text: str, *, dimension: int = 1024) -> list[float]:
    batch = EmbeddingBatch(items=[EmbeddingInput(text=text)], dimension=dimension)
    result = await embed_texts(batch)
    return result[0]
