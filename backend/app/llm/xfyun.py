# Status: real

"""讯飞星火 LLM 客户端。

设计原则：
- 真实模式（``XFYUN_API_KEY`` 已配置）：调用讯飞星火 v4 OpenAI 兼容 API；
- 兜底模式（未配置 / 失败）：返回固定 fixture，使整条 demo 链路在无外部依赖时仍可跑通；
- 流式：使用 SSE，单 token 输出回填给 harness 的 ``emit``。

讯飞星火兼容 OpenAI ``/v1/chat/completions``，使用 APIPassword 形式（``XFYUN_API_KEY``）。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.llm.base import BaseLLMClient, ChatMessage, EmbeddingResult, TokenChunk

logger = logging.getLogger(__name__)

_DEFAULT_XFYUN_BASE_URL = "https://spark-api-open.xf-yun.com/v1"


class XFYunClient(BaseLLMClient):
    """OpenAI-compatible client targeting 讯飞星火."""

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.XFYUN_MODEL or "general"
        self.api_key = self.settings.XFYUN_API_KEY
        self.base_url = getattr(self.settings, "XFYUN_BASE_URL", _DEFAULT_XFYUN_BASE_URL).rstrip("/")
        self.thinking_mode = str(getattr(self.settings, "XFYUN_THINKING_MODE", "") or "").strip().lower()
        self._timeout = httpx.Timeout(60.0, read=120.0)

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        temperature: float = 0.2,
    ) -> str | AsyncIterator[TokenChunk]:
        if not self.is_configured:
            raise RuntimeError("XFYun API key not configured; caller should fall back to mock")

        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
            "temperature": temperature,
        }
        if self.thinking_mode:
            payload["thinking"] = {"type": self.thinking_mode}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if stream:
            return self._stream(headers, payload)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self.chat_url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            choice = (body.get("choices") or [{}])[0]
            return (choice.get("message") or {}).get("content", "")

    async def _stream(self, headers: dict[str, str], payload: dict[str, Any]) -> AsyncIterator[TokenChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", self.chat_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                index = 0
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = ((chunk.get("choices") or [{}])[0]).get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield TokenChunk(content=content, index=index)
                        index += 1

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        # Spark 提供独立的 embedding API，但 P0 阶段优先复用 BGE-M3 / 兜底
        raise NotImplementedError("XFYun embedding 暂未接入；使用 app.llm.embedding 兜底")


async def xfyun_chat(prompt: str, *, stream: bool = False, system: str | None = None) -> str:
    """便捷函数：以单段 prompt 调用讯飞星火，返回字符串。

    - ``stream=False`` 时直接返回 ``str``；
    - ``stream=True`` 时返回拼接后的字符串（流由调用方在 harness 内分发）。
    """
    client = XFYunClient()
    if not client.is_configured:
        raise NotImplementedError("XFYUN_API_KEY not set; harness will fall back to fixtures")

    messages: list[ChatMessage] = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=prompt))

    if not stream:
        result = await client.chat(messages, stream=False)
        return result if isinstance(result, str) else ""

    stream_iter = await client.chat(messages, stream=True)
    pieces: list[str] = []
    async for token in stream_iter:  # type: ignore[union-attr]
        pieces.append(token.content)
    return "".join(pieces)
