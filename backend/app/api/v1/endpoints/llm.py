# Status: partial-real

"""LLM provider health endpoint.

This round reports explicit fixture mode only. Real provider checks can replace
the internals after DeepSeek or Xunfei Spark is wired through the LLM layer.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RateLimitState(BaseModel):
    used: int = 0
    limit: int = 0


class LLMHealthResponse(BaseModel):
    provider: str
    model: str
    mode: Literal["real", "fixture", "fallback"]
    live_enabled: bool
    status: Literal["available", "degraded", "error", "unknown"]
    last_error: str | None
    rate_limit_state: RateLimitState


@router.get("/llm/health", response_model=LLMHealthResponse)
async def llm_health() -> LLMHealthResponse:
    return LLMHealthResponse(
        provider="fixture",
        model="fixture-canned",
        mode="fixture",
        live_enabled=False,
        status="available",
        last_error=None,
        rate_limit_state=RateLimitState(used=0, limit=0),
    )
