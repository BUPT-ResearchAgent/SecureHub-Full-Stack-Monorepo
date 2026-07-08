# Status: real

from __future__ import annotations

from typing import Any

from app.llm.embeddings.base import EmbeddingProvider
from app.llm.embeddings.errors import EmbeddingConfigurationError
from app.llm.embeddings.fixture import DeterministicFixtureEmbeddingProvider
from app.llm.embeddings.qwen_openai_compatible import QwenOpenAICompatibleEmbeddingProvider


def create_embedding_provider(
    provider: str | None = None,
    *,
    settings: Any | None = None,
    **kwargs: Any,
) -> EmbeddingProvider:
    from app.core.config import get_settings

    cfg = settings or get_settings()
    selected = _normalise_provider(provider or getattr(cfg, "EMBEDDING_PROVIDER", ""))
    if selected == "fixture":
        return DeterministicFixtureEmbeddingProvider(
            dimension=int(getattr(cfg, "EMBEDDING_DIM", 1024)),
        )
    if selected == "qwen_openai_compatible":
        return QwenOpenAICompatibleEmbeddingProvider(settings=cfg, **kwargs)
    raise EmbeddingConfigurationError(
        "Unknown EMBEDDING_PROVIDER: "
        f"{provider or getattr(cfg, 'EMBEDDING_PROVIDER', '')!r}. "
        "Valid values: qwen_openai_compatible, fixture"
    )


def _normalise_provider(value: str) -> str:
    normalized = (value or "").strip().lower().replace("-", "_")
    aliases = {
        "qwen": "qwen_openai_compatible",
        "qwen_openai": "qwen_openai_compatible",
        "qwen_openai_compatible": "qwen_openai_compatible",
        "fixture": "fixture",
    }
    return aliases.get(normalized, normalized)
