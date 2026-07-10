# Status: real

import pytest

from app.llm.embeddings.fixture import DeterministicFixtureEmbeddingProvider


@pytest.mark.anyio
async def test_fixture_same_text_is_stable() -> None:
    provider = DeterministicFixtureEmbeddingProvider()

    first = await provider.embed_query("SQL injection")
    second = await provider.embed_query("SQL injection")

    assert first.vectors[0] == second.vectors[0]
    assert len(first.vectors[0]) == 1024


@pytest.mark.anyio
async def test_fixture_different_texts_are_different() -> None:
    provider = DeterministicFixtureEmbeddingProvider()

    result = await provider.embed_documents(["SQL injection", "XSS"])

    assert result.vectors[0] != result.vectors[1]
    assert len(result.vectors[0]) == 1024
    assert len(result.vectors[1]) == 1024
