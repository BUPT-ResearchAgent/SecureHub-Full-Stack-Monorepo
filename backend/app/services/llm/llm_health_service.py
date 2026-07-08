# Status: real

"""LLM Health Service — 供 B 的 /api/v1/llm/health endpoint 调用。"""

from __future__ import annotations

from app.llm.provider import HealthStatus, get_llm_provider


async def get_llm_health(provider: str | None = None) -> HealthStatus:
    """检查当前 LLM Provider 健康状态。

    返回 HealthStatus，包含：provider, model, mode, live_enabled, status, last_error。
    B 直接将此返回值序列化为 JSON 响应。
    """
    p = get_llm_provider(provider)
    return await p.health_check()
