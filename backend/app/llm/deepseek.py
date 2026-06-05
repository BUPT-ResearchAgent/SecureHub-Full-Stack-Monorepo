# Status: [planned]

from collections.abc import AsyncIterator
from typing import Any

from app.llm.base import BaseLLMClient, ChatMessage, EmbeddingResult, TokenChunk


class DeepSeekClient(BaseLLMClient):
    def __init__(self, settings: Any) -> None:
        self.settings = settings

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        temperature: float = 0.2,
    ) -> str | AsyncIterator[TokenChunk]:
        raise NotImplementedError("TODO: call DeepSeek fallback API")

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise NotImplementedError("TODO: delegate embeddings to configured embedding provider")
