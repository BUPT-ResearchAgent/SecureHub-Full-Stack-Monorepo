# Status: [planned]

from collections.abc import AsyncIterator
from typing import Any

from app.llm.base import BaseLLMClient, ChatMessage, EmbeddingResult, TokenChunk


class XFYunClient(BaseLLMClient):
    def __init__(self, settings: Any) -> None:
        self.settings = settings

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        temperature: float = 0.2,
    ) -> str | AsyncIterator[TokenChunk]:
        raise NotImplementedError("TODO: call XFYun Spark API over websocket/http")

    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise NotImplementedError("TODO: call configured XFYun embedding API")


async def xfyun_chat(prompt: str, *, stream: bool = False) -> str:
    raise NotImplementedError("TODO: call XFYun Spark with prompt")
