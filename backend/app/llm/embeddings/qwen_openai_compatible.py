# Status: real

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import json
import logging
import math
import random
import time
from typing import Any

import httpx

from app.llm.embeddings.base import EmbeddingResult, EmbeddingUsage
from app.llm.embeddings.errors import (
    EmbeddingAuthenticationError,
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingInputError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingResponseError,
)

logger = logging.getLogger(__name__)


class QwenOpenAICompatibleEmbeddingProvider:
    """Alibaba Model Studio OpenAI-compatible embedding provider."""

    provider_name = "qwen_openai_compatible"
    output_type = "dense"

    def __init__(
        self,
        settings: Any | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        retry_sleep_base: float = 0.25,
    ) -> None:
        from app.core.config import get_settings

        cfg = settings or get_settings()
        self.api_key = str(getattr(cfg, "DASHSCOPE_API_KEY", "") or "")
        self.base_url = str(
            getattr(cfg, "DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL", "") or ""
        ).rstrip("/")
        self.model_name = str(getattr(cfg, "EMBEDDING_MODEL", "text-embedding-v4"))
        self.dimension = int(getattr(cfg, "EMBEDDING_DIM", 1024))
        self.profile = str(
            getattr(
                cfg,
                "EMBEDDING_PROFILE",
                "qwen-openai-compatible:text-embedding-v4:1024:dense:v1",
            )
        )
        self.batch_size = int(getattr(cfg, "EMBEDDING_BATCH_SIZE", 10))
        self.max_concurrency = int(getattr(cfg, "EMBEDDING_MAX_CONCURRENCY", 1))
        self.max_retries = int(getattr(cfg, "EMBEDDING_MAX_RETRIES", 2))
        self.timeout_seconds = float(getattr(cfg, "EMBEDDING_TIMEOUT_SECONDS", 30.0))
        self.retry_sleep_base = retry_sleep_base

        if not self.api_key:
            raise EmbeddingConfigurationError(
                "DASHSCOPE_API_KEY is not set; please check backend/.env.local"
            )
        if not self.base_url:
            raise EmbeddingConfigurationError(
                "DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL is not set; "
                "please check backend/.env.local"
            )
        if self.dimension != 1024:
            raise EmbeddingConfigurationError("EMBEDDING_DIM must be 1024 for this migration")
        expected_profile = (
            f"qwen-openai-compatible:{self.model_name}:{self.dimension}:"
            f"{self.output_type}:v1"
        )
        if self.profile != expected_profile:
            raise EmbeddingConfigurationError(
                "EMBEDDING_PROFILE must match provider/model/dimension/output contract: "
                f"{expected_profile}"
            )
        if not 1 <= self.batch_size <= 10:
            raise EmbeddingConfigurationError("EMBEDDING_BATCH_SIZE must be in 1..10")
        if self.max_concurrency < 1:
            raise EmbeddingConfigurationError("EMBEDDING_MAX_CONCURRENCY must be >= 1")
        if self.max_retries < 0:
            raise EmbeddingConfigurationError("EMBEDDING_MAX_RETRIES must be >= 0")

        timeout = httpx.Timeout(self.timeout_seconds)
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        return await self._embed(texts)

    async def embed_query(self, text: str) -> EmbeddingResult:
        return await self._embed([text])

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _embed(self, texts: Sequence[str]) -> EmbeddingResult:
        validated = _validate_texts(texts)
        batches = [
            (offset, validated[offset : offset + self.batch_size])
            for offset in range(0, len(validated), self.batch_size)
        ]
        vectors: list[list[float] | None] = [None] * len(validated)
        usage = EmbeddingUsage()
        request_ids: list[str] = []

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_batch(offset: int, batch: list[str]) -> tuple[int, EmbeddingResult]:
            async with semaphore:
                return offset, await self._post_batch(batch)

        tasks = [run_batch(offset, batch) for offset, batch in batches]
        for offset, batch_result in await asyncio.gather(*tasks):
            for index, vector in enumerate(batch_result.vectors):
                vectors[offset + index] = vector
            usage.prompt_tokens += batch_result.usage.prompt_tokens
            usage.total_tokens += batch_result.usage.total_tokens
            usage.request_count += batch_result.usage.request_count
            if batch_result.request_id:
                request_ids.append(batch_result.request_id)

        final_vectors = [vector for vector in vectors if vector is not None]
        if len(final_vectors) != len(validated):
            raise EmbeddingResponseError("embedding response did not cover every input")

        return EmbeddingResult(
            vectors=final_vectors,
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
            profile=self.profile,
            output_type=self.output_type,
            usage=usage,
            request_id=",".join(request_ids) if request_ids else None,
        )

    async def _post_batch(self, texts: list[str]) -> EmbeddingResult:
        payload = {
            "model": self.model_name,
            "input": texts,
            "dimensions": self.dimension,
            "encoding_format": "float",
        }
        endpoint = f"{self.base_url}/embeddings"
        last_error: Exception | None = None
        started = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    endpoint,
                    headers=self._headers,
                    json=payload,
                )
                if response.status_code in {401, 403}:
                    raise EmbeddingAuthenticationError(
                        f"embedding provider authentication failed with HTTP {response.status_code}"
                    )
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise EmbeddingRateLimitError("embedding provider rate limit exceeded")
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        await self._sleep_before_retry(attempt)
                        continue
                    raise EmbeddingProviderError(
                        f"embedding provider returned HTTP {response.status_code}"
                    )
                if response.status_code >= 400:
                    raise EmbeddingProviderError(
                        f"embedding provider returned HTTP {response.status_code}"
                    )
                body = response.json()
                result = self._parse_response(body, len(texts), response.headers)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "embedding batch ok provider=%s model=%s profile=%s input_count=%s "
                    "dimension=%s prompt_tokens=%s latency_ms=%s request_id=%s",
                    self.provider_name,
                    self.model_name,
                    self.profile,
                    len(texts),
                    self.dimension,
                    result.usage.prompt_tokens,
                    elapsed_ms,
                    result.request_id or "",
                )
                return result
            except (EmbeddingAuthenticationError, EmbeddingProviderError, EmbeddingRateLimitError):
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await self._sleep_before_retry(attempt)
                    continue
                raise EmbeddingProviderError("embedding provider request timed out") from exc
            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await self._sleep_before_retry(attempt)
                    continue
                raise EmbeddingProviderError("embedding provider network error") from exc
            except json.JSONDecodeError as exc:
                raise EmbeddingResponseError("embedding provider returned invalid JSON") from exc

        raise EmbeddingProviderError("embedding provider request failed") from last_error

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_sleep_base <= 0:
            return
        delay = min(self.retry_sleep_base * (2**attempt), 2.0)
        delay += random.uniform(0.0, min(delay * 0.2, 0.2))
        await asyncio.sleep(delay)

    def _parse_response(
        self,
        body: dict[str, Any],
        expected_count: int,
        headers: httpx.Headers,
    ) -> EmbeddingResult:
        raw_data = body.get("data")
        if not isinstance(raw_data, list):
            raise EmbeddingResponseError("embedding response missing data list")
        if len(raw_data) != expected_count:
            raise EmbeddingResponseError(
                f"embedding response count mismatch: expected {expected_count}, got {len(raw_data)}"
            )

        ordered: list[list[float] | None] = [None] * expected_count
        for item in raw_data:
            if not isinstance(item, dict):
                raise EmbeddingResponseError("embedding response data item must be an object")
            index = item.get("index")
            if not isinstance(index, int) or not 0 <= index < expected_count:
                raise EmbeddingResponseError("embedding response item has invalid index")
            vector = item.get("embedding")
            ordered[index] = _validate_vector(vector, self.dimension)

        vectors = [vector for vector in ordered if vector is not None]
        if len(vectors) != expected_count:
            raise EmbeddingResponseError("embedding response missing one or more indexes")

        usage_raw = body.get("usage") or {}
        prompt_tokens = _safe_int(usage_raw.get("prompt_tokens"))
        total_tokens = _safe_int(usage_raw.get("total_tokens")) or prompt_tokens
        request_id = (
            headers.get("x-request-id")
            or headers.get("x-acs-request-id")
            or headers.get("request-id")
            or body.get("id")
        )
        return EmbeddingResult(
            vectors=vectors,
            provider=self.provider_name,
            model=str(body.get("model") or self.model_name),
            dimension=self.dimension,
            profile=self.profile,
            output_type=self.output_type,
            usage=EmbeddingUsage(
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                request_count=1,
            ),
            request_id=str(request_id) if request_id else None,
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


def _validate_vector(raw: Any, dimension: int) -> list[float]:
    if not isinstance(raw, list):
        raise EmbeddingResponseError("embedding vector must be a list")
    if len(raw) != dimension:
        raise EmbeddingDimensionError(
            f"embedding dimension mismatch: expected {dimension}, got {len(raw)}"
        )
    vector: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EmbeddingResponseError("embedding vector values must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise EmbeddingResponseError("embedding vector values must be finite")
        vector.append(numeric)
    return vector


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0
