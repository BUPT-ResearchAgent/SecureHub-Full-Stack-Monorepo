# Status: real

"""XunfeiSparkProvider — BaseLLMProvider 实现。

读取 XFYUN_API_KEY，调用讯飞星火 OpenAI 兼容 API。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.provider import (
    BaseLLMProvider,
    HealthStatus,
    LLMChunk,
    LLMMessage,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_XFYUN_BASE_URL = "https://spark-api-open.xf-yun.com"
_DEFAULT_MODEL = "spark-v4"


class XunfeiSparkProvider(BaseLLMProvider):
    """讯飞星火 OpenAI-compatible provider (spark-api-open)."""

    provider_name = "xfyun"

    def __init__(self, settings: Any | None = None, *, api_key: str | None = None) -> None:
        from app.core.config import get_settings

        cfg = settings or get_settings()
        # The value can be a user credential resolved for one durable root;
        # never write it back to Settings.
        self.api_key: str = cfg.XFYUN_API_KEY if api_key is None else api_key
        self.model_name = getattr(cfg, "XFYUN_MODEL", _DEFAULT_MODEL)
        self.timeout = httpx.Timeout(60.0, read=120.0)
        self.retry = 1

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[LLMMessage],
        *,
        stream: bool,
        temperature: float,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return payload

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(messages, stream=False, temperature=temperature, max_tokens=max_tokens)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{_XFYUN_BASE_URL}/v1/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPStatusError as exc:
            raise self.map_error(exc, exc.response.status_code) from exc
        except httpx.TimeoutException as exc:
            raise self.map_error(exc) from exc

        choice = (body.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content", "")
        usage_raw = body.get("usage", {})
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage_raw.get("prompt_tokens", 0),
                completion_tokens=usage_raw.get("completion_tokens", 0),
                total_tokens=usage_raw.get("total_tokens", 0),
            ),
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMChunk]:
        payload = self._build_payload(messages, stream=True, temperature=temperature, max_tokens=max_tokens)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{_XFYUN_BASE_URL}/v1/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    index = 0
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: "):].strip()
                        if data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        delta = ((chunk.get("choices") or [{}])[0]).get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield LLMChunk(content=content, index=index)
                            index += 1
        except httpx.HTTPStatusError as exc:
            raise self.map_error(exc, exc.response.status_code) from exc

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="fixture",
                live_enabled=False,
                status="error",
                last_error="XFYUN_API_KEY not set",
            )
        try:
            await self.generate(
                [LLMMessage(role="user", content="ping")],
                max_tokens=1,
            )
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="real",
                live_enabled=True,
                status="available",
            )
        except Exception as exc:
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="real",
                live_enabled=True,
                status="error",
                last_error=str(exc),
            )
