# Status: [planned]

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class TokenChunk(BaseModel):
    content: str
    index: int = 0
    finish_reason: str | None = None


class EmbeddingResult(BaseModel):
    vector: list[float]
    model: str
    dimension: int


class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        temperature: float = 0.2,
    ) -> str | AsyncIterator[TokenChunk]:
        raise NotImplementedError("TODO: implement provider chat call")

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        raise NotImplementedError("TODO: implement provider embedding call")


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
