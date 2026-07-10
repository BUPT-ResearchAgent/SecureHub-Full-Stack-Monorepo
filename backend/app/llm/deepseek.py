# Status: real

"""DeepSeek 兜底 LLM 客户端（OpenAI 兼容 API）。"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.llm.base import BaseLLMClient, ChatMessage, EmbeddingResult, TokenChunk

logger = logging.getLogger(__name__)

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat/completions"


class DeepSeekClient(BaseLLMClient):
    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.DEEPSEEK_MODEL or "deepseek-chat"
        self.api_key = self.settings.DEEPSEEK_API_KEY
        self._timeout = httpx.Timeout(60.0, read=120.0)

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
            raise RuntimeError("DeepSeek API key not configured; caller should fall back to mock")

        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if stream:
            return self._stream(headers, payload)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(DEEPSEEK_CHAT_URL, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            choice = (body.get("choices") or [{}])[0]
            return (choice.get("message") or {}).get("content", "")

    async def _stream(self, headers: dict[str, str], payload: dict[str, Any]) -> AsyncIterator[TokenChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", DEEPSEEK_CHAT_URL, headers=headers, json=payload) as response:
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
        raise NotImplementedError("DeepSeek embedding 暂未接入；使用 app.llm.embedding 兜底")
