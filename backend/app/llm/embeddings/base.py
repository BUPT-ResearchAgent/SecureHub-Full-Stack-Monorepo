# Status: real

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class EmbeddingUsage:
    prompt_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0


@dataclass(slots=True)
class EmbeddingResult:
    vectors: list[list[float]]
    provider: str
    model: str
    dimension: int
    profile: str
    output_type: str = "dense"
    usage: EmbeddingUsage = field(default_factory=EmbeddingUsage)
    request_id: str | None = None


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int
    profile: str
    output_type: str

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        """Embed document texts for storage."""

    async def embed_query(self, text: str) -> EmbeddingResult:
        """Embed a query text for retrieval."""

    async def aclose(self) -> None:
        """Close any owned network resources."""
