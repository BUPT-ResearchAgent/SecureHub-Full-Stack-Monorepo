# Status: real

import pytest

from app.llm.embeddings.errors import EmbeddingProviderError
from app.runtime.harness.base import _default_rag_retrieve


@pytest.mark.anyio
async def test_default_rag_retrieve_does_not_mask_embedding_errors(monkeypatch) -> None:
    async def broken_retrieve(*_args, **_kwargs):
        raise EmbeddingProviderError("provider unavailable")

    import app.rag.retriever as retriever

    monkeypatch.setattr(retriever, "retrieve", broken_retrieve)

    with pytest.raises(EmbeddingProviderError):
        await _default_rag_retrieve("SQL injection", domain="course_websec", top_k=3)
