# Status: real

import math
import os

import pytest

from app.core.config import get_settings
from app.llm.embeddings.service import EmbeddingService


pytestmark = pytest.mark.embedding_live


def _live_enabled() -> bool:
    settings = get_settings()
    return (
        os.getenv("ENABLE_EMBEDDING_LIVE_TESTS", "").lower() in {"1", "true", "yes", "on"}
        or settings.ENABLE_EMBEDDING_LIVE_TESTS
    ) and bool(settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL)


@pytest.mark.anyio
async def test_qwen_embedding_live_returns_1024_dimensions() -> None:
    if not _live_enabled():
        pytest.skip("set ENABLE_EMBEDDING_LIVE_TESTS=true and configure DashScope embedding env")

    service = EmbeddingService()
    docs = await service.embed_documents(["SQL injection defense", "XSS output encoding"])
    query = await service.embed_query("How do parameterized queries prevent SQL injection?")
    await service.aclose()

    assert docs.provider == "qwen_openai_compatible"
    assert docs.model
    assert len(docs.vectors) == 2
    assert all(len(vector) == 1024 for vector in docs.vectors)
    assert len(query.vectors[0]) == 1024
    assert all(math.isfinite(value) for value in docs.vectors[0])
