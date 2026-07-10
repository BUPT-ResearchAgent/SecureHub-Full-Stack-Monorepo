# Status: real

from __future__ import annotations

import json
import math
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.llm.embeddings.errors import (
    EmbeddingAuthenticationError,
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingInputError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingResponseError,
)
from app.llm.embeddings.factory import create_embedding_provider
from app.llm.embeddings.qwen_openai_compatible import QwenOpenAICompatibleEmbeddingProvider


def _settings(**overrides: Any) -> Settings:
    data = {
        "DASHSCOPE_API_KEY": "test-key",
        "DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL": "https://dashscope.test/compatible-mode/v1",
        "EMBEDDING_PROVIDER": "qwen_openai_compatible",
        "EMBEDDING_MODEL": "text-embedding-v4",
        "EMBEDDING_DIM": 1024,
        "EMBEDDING_PROFILE": "qwen-openai-compatible:text-embedding-v4:1024:dense:v1",
        "EMBEDDING_BATCH_SIZE": 10,
        "EMBEDDING_MAX_RETRIES": 0,
        "EMBEDDING_MAX_CONCURRENCY": 1,
    }
    data.update(overrides)
    return Settings(**data)


def _vector(dimension: int = 1024) -> list[float]:
    return [0.001] * dimension


def _response_for_request(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    data = [
        {"object": "embedding", "index": index, "embedding": _vector()}
        for index, _ in enumerate(payload["input"])
    ]
    return httpx.Response(
        200,
        json={
            "object": "list",
            "model": payload["model"],
            "data": data,
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        },
        headers={"x-request-id": "req-test"},
    )


@pytest.mark.anyio
async def test_qwen_provider_sends_openai_compatible_payload() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://dashscope.test/compatible-mode/v1/embeddings"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = json.loads(request.content.decode("utf-8"))
        seen.append(payload)
        return _response_for_request(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = QwenOpenAICompatibleEmbeddingProvider(
        settings=_settings(),
        client=client,
        retry_sleep_base=0,
    )

    result = await provider.embed_documents(["a", "b"])
    await provider.aclose()
    await client.aclose()

    assert seen == [
        {
            "model": "text-embedding-v4",
            "input": ["a", "b"],
            "dimensions": 1024,
            "encoding_format": "float",
        }
    ]
    assert result.provider == "qwen_openai_compatible"
    assert result.model == "text-embedding-v4"
    assert result.dimension == 1024
    assert result.usage.request_count == 1
    assert result.request_id == "req-test"


@pytest.mark.anyio
async def test_qwen_provider_splits_batches_and_preserves_order() -> None:
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        batch_sizes.append(len(payload["input"]))
        data = [
            {"object": "embedding", "index": index, "embedding": [float(index)] * 1024}
            for index, _ in enumerate(payload["input"])
        ][::-1]
        return httpx.Response(200, json={"model": payload["model"], "data": data, "usage": {}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = QwenOpenAICompatibleEmbeddingProvider(
        settings=_settings(EMBEDDING_BATCH_SIZE=10),
        client=client,
        retry_sleep_base=0,
    )

    result = await provider.embed_documents([f"text-{index}" for index in range(25)])
    await client.aclose()

    assert batch_sizes == [10, 10, 5]
    assert result.vectors[0] == [0.0] * 1024
    assert result.vectors[9] == [9.0] * 1024
    assert result.vectors[24] == [4.0] * 1024


@pytest.mark.anyio
async def test_qwen_provider_rejects_invalid_input() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_response_for_request))
    provider = QwenOpenAICompatibleEmbeddingProvider(settings=_settings(), client=client)

    with pytest.raises(EmbeddingInputError):
        await provider.embed_documents([])
    with pytest.raises(EmbeddingInputError):
        await provider.embed_documents([" "])
    with pytest.raises(EmbeddingInputError):
        await provider.embed_documents([None])  # type: ignore[list-item]

    await client.aclose()


@pytest.mark.anyio
async def test_qwen_provider_fail_fast_on_missing_config() -> None:
    with pytest.raises(EmbeddingConfigurationError):
        QwenOpenAICompatibleEmbeddingProvider(settings=_settings(DASHSCOPE_API_KEY=""))
    with pytest.raises(EmbeddingConfigurationError):
        QwenOpenAICompatibleEmbeddingProvider(
            settings=_settings(DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL="")
        )
    with pytest.raises(EmbeddingConfigurationError):
        QwenOpenAICompatibleEmbeddingProvider(
            settings=_settings(
                EMBEDDING_MODEL="text-embedding-v4",
                EMBEDDING_PROFILE="qwen-openai-compatible:other-model:1024:dense:v1",
            )
        )


@pytest.mark.anyio
async def test_qwen_provider_maps_auth_and_rate_limit_without_fallback() -> None:
    auth_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(401, json={"error": "bad"}))
    )
    auth_provider = QwenOpenAICompatibleEmbeddingProvider(settings=_settings(), client=auth_client)
    with pytest.raises(EmbeddingAuthenticationError):
        await auth_provider.embed_query("SQL")
    await auth_client.aclose()

    rate_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(429, json={"error": "limit"}))
    )
    rate_provider = QwenOpenAICompatibleEmbeddingProvider(settings=_settings(), client=rate_client)
    with pytest.raises(EmbeddingRateLimitError):
        await rate_provider.embed_query("SQL")
    await rate_client.aclose()


@pytest.mark.anyio
async def test_qwen_provider_retries_500_and_timeout() -> None:
    calls = 0

    def flaky(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return _response_for_request(_request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(flaky))
    provider = QwenOpenAICompatibleEmbeddingProvider(
        settings=_settings(EMBEDDING_MAX_RETRIES=1),
        client=client,
        retry_sleep_base=0,
    )

    result = await provider.embed_query("SQL")
    await client.aclose()

    assert calls == 2
    assert len(result.vectors[0]) == 1024

    def always_timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    timeout_client = httpx.AsyncClient(transport=httpx.MockTransport(always_timeout))
    timeout_provider = QwenOpenAICompatibleEmbeddingProvider(
        settings=_settings(EMBEDDING_MAX_RETRIES=1),
        client=timeout_client,
        retry_sleep_base=0,
    )
    with pytest.raises(EmbeddingProviderError):
        await timeout_provider.embed_query("SQL")
    await timeout_client.aclose()


@pytest.mark.anyio
async def test_qwen_provider_validates_response_shape_dimension_and_finite_values() -> None:
    cases = [
        httpx.Response(200, json={"model": "text-embedding-v4", "data": []}),
        httpx.Response(
            200,
            json={
                "model": "text-embedding-v4",
                "data": [{"index": 0, "embedding": _vector(3)}],
            },
        ),
        httpx.Response(
            200,
            content=json.dumps(
                {
                    "model": "text-embedding-v4",
                    "data": [{"index": 0, "embedding": [math.inf] * 1024}],
                },
                allow_nan=True,
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
        ),
    ]

    expected = [EmbeddingResponseError, EmbeddingDimensionError, EmbeddingResponseError]
    for response, error_type in zip(cases, expected, strict=True):
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request, r=response: r))
        provider = QwenOpenAICompatibleEmbeddingProvider(settings=_settings(), client=client)
        with pytest.raises(error_type):
            await provider.embed_query("SQL")
        await client.aclose()


def test_embedding_factory_fixture_only_when_explicit() -> None:
    fixture = create_embedding_provider(settings=_settings(EMBEDDING_PROVIDER="fixture"))
    assert fixture.provider_name == "fixture"

    with pytest.raises(EmbeddingConfigurationError):
        create_embedding_provider(settings=_settings(EMBEDDING_PROVIDER="bge_m3"))

    with pytest.raises(EmbeddingConfigurationError):
        create_embedding_provider(
            settings=_settings(EMBEDDING_PROVIDER="fixture", APP_ENV="production")
        )
