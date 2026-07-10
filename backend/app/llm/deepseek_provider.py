# Status: real

"""DeepSeekProvider — BaseLLMProvider 实现。

读取 DEEPSEEK_API_KEY，调用 OpenAI 兼容 API (api.deepseek.com)。
支持同步 generate() 和流式 stream_generate()。
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

_DEFAULT_BASE_URL = "https://api.deepseek.com"
_DEFAULT_MODEL = "deepseek-chat"


class DeepSeekProvider(BaseLLMProvider):
    """OpenAI-compatible DeepSeek provider."""

    provider_name = "deepseek"

    def __init__(self, settings: Any | None = None) -> None:
        from app.core.config import get_settings

        cfg = settings or get_settings()
        self.api_key: str = cfg.DEEPSEEK_API_KEY
        self.base_url: str = getattr(cfg, "DEEPSEEK_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.model_name = getattr(cfg, "DEEPSEEK_MODEL", _DEFAULT_MODEL)
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
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(
            messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
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
        response_format: dict[str, str] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        payload = self._build_payload(
            messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
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
                last_error="DEEPSEEK_API_KEY not set",
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
