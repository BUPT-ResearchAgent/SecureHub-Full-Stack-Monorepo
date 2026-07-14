# Status: partial-real

"""LLM provider health endpoint."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm import get_llm_health

router = APIRouter()
logger = logging.getLogger(__name__)


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
    settings = get_settings()
    if not settings.AGENT_RUN_REAL_ENABLED and settings.LLM_PROVIDER != "fixture":
        return _disabled_response(settings.LLM_PROVIDER, _configured_model(settings))

    try:
        health = await get_llm_health()
    except Exception as exc:  # Health endpoints must not expose upstream provider details.
        logger.warning(
            "LLM health check failed for provider %s: %s",
            settings.LLM_PROVIDER,
            type(exc).__name__,
        )
        return LLMHealthResponse(
            provider=settings.LLM_PROVIDER,
            model=_configured_model(settings),
            mode="real" if settings.LLM_PROVIDER != "fixture" else "fixture",
            live_enabled=settings.AGENT_RUN_REAL_ENABLED,
            status="error",
            last_error="configured provider is unavailable",
            rate_limit_state=RateLimitState(),
        )

    return LLMHealthResponse(
        provider=health.provider,
        model=health.model,
        mode=health.mode,
        live_enabled=health.live_enabled,
        status=health.status,
        last_error="provider health check failed" if health.last_error else None,
        rate_limit_state=RateLimitState.model_validate(health.rate_limit_state or {}),
    )


def _disabled_response(provider: str, model: str) -> LLMHealthResponse:
    return LLMHealthResponse(
        provider=provider,
        model=model,
        mode="real",
        live_enabled=False,
        status="unknown",
        last_error="real execution is disabled",
        rate_limit_state=RateLimitState(),
    )


def _configured_model(settings: object) -> str:
    if getattr(settings, "LLM_PROVIDER") == "deepseek":
        return str(getattr(settings, "DEEPSEEK_MODEL"))
    if getattr(settings, "LLM_PROVIDER") == "xfyun":
        return str(getattr(settings, "XFYUN_MODEL"))
    return "fixture-v1"
