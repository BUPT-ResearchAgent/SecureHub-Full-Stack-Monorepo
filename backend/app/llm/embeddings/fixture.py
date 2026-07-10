# Status: real

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import math

from app.llm.embeddings.base import EmbeddingResult, EmbeddingUsage
from app.llm.embeddings.errors import EmbeddingInputError


class DeterministicFixtureEmbeddingProvider:
    """Network-free deterministic embeddings for tests and local fixtures."""

    provider_name = "fixture"
    model_name = "fixture-embedding-v1"
    output_type = "dense"

    def __init__(self, *, dimension: int = 1024, profile: str | None = None) -> None:
        self.dimension = dimension
        self.profile = profile or f"fixture:{self.model_name}:{dimension}:dense:v1"

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        validated = _validate_texts(texts)
        return self._result(validated)

    async def embed_query(self, text: str) -> EmbeddingResult:
        validated = _validate_texts([text])
        return self._result(validated)

    async def aclose(self) -> None:
        return None

    def _result(self, texts: Sequence[str]) -> EmbeddingResult:
        vectors = [_fixture_vector(text, self.dimension) for text in texts]
        token_count = sum(max(1, len(text) // 4) for text in texts)
        return EmbeddingResult(
            vectors=vectors,
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            profile=self.profile,
            output_type=self.output_type,
            usage=EmbeddingUsage(
                prompt_tokens=token_count,
                total_tokens=token_count,
                request_count=0,
            ),
        )


def _validate_texts(texts: Sequence[str]) -> list[str]:
    if not texts:
        raise EmbeddingInputError("embedding input must not be empty")
    validated: list[str] = []
    for item in texts:
        if not isinstance(item, str):
            raise EmbeddingInputError("embedding input items must be strings")
        if not item.strip():
            raise EmbeddingInputError("embedding input items must not be blank")
        validated.append(item)
    return validated


def _fixture_vector(text: str, dimension: int) -> list[float]:
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{text}\0{counter}".encode("utf-8")).digest()
        for offset in range(0, len(digest), 4):
            if len(values) >= dimension:
                break
            raw = int.from_bytes(digest[offset : offset + 4], "big", signed=False)
            values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
