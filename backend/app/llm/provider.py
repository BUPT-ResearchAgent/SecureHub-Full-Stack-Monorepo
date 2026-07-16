# Status: real

"""BaseLLMProvider 抽象 + FixtureProvider + 工厂函数。

设计：
- BaseLLMProvider 统一接口：generate / stream_generate / health_check / estimate_tokens
- FixtureProvider：无需 Key，返回确定性 fixture（CI / 开发默认）
- get_llm_provider(provider?) 按 LLM_PROVIDER 环境变量路由
- API Key 缺失时不静默 fallback；fixture 只能由 fixture mode 显式选择
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

# ── Data types ──────────────────────────────────────────────────────────────


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMChunk(BaseModel):
    content: str
    index: int = 0
    finish_reason: str | None = None


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    finish_reason: str = "stop"


@dataclass
class HealthStatus:
    provider: str
    model: str
    mode: Literal["real", "fixture"]
    live_enabled: bool
    status: Literal["available", "degraded", "error"]
    last_error: str | None = None
    rate_limit_state: dict[str, Any] | None = None


# ── Abstract base ────────────────────────────────────────────────────────────


class BaseLLMProvider(abc.ABC):
    """统一 LLM Provider 接口。所有 Provider 必须实现此接口。"""

    provider_name: str = "base"
    model_name: str = "unknown"
    timeout: float = 60.0
    retry: int = 1

    @abc.abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """同步生成，返回完整响应。"""

    @abc.abstractmethod
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """流式生成，每次 yield 一个 LLMChunk。"""

    @abc.abstractmethod
    async def health_check(self) -> HealthStatus:
        """返回 Provider 健康状态。"""

    def estimate_tokens(self, text: str) -> int:
        """粗估 token 数（4 字符 ≈ 1 token）。"""
        return max(1, len(text) // 4)

    def map_error(self, exc: Exception, status_code: int | None = None) -> Exception:
        """将 Provider 特定错误映射为统一错误类型。"""
        from app.runtime.exceptions import LLMProviderError, ProviderUnavailable

        if status_code == 401:
            return ProviderUnavailable(f"[{self.provider_name}] 认证失败: {exc}")
        if status_code == 429:
            return LLMProviderError(f"[{self.provider_name}] 请求限流: {exc}")
        if status_code and status_code >= 500:
            return LLMProviderError(f"[{self.provider_name}] 服务端错误 {status_code}: {exc}")
        return LLMProviderError(f"[{self.provider_name}] 调用失败: {exc}")


# ── FixtureProvider ──────────────────────────────────────────────────────────


class FixtureProvider(BaseLLMProvider):
    """确定性 Fixture Provider，用于 CI / 开发环境。不消耗真实 API 额度。"""

    provider_name = "fixture"
    model_name = "fixture-v1"

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        prompt = messages[-1].content if messages else ""
        content = self._fixture_content(prompt)
        tokens = self.estimate_tokens(prompt + content)
        return LLMResponse(
            content=content,
            usage=TokenUsage(prompt_tokens=tokens, completion_tokens=len(content) // 4, total_tokens=tokens),
            provider=self.provider_name,
            model=self.model_name,
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        response = await self.generate(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            response_schema=response_schema,
        )
        words = response.content.split()
        for i, word in enumerate(words):
            yield LLMChunk(content=word + (" " if i < len(words) - 1 else ""), index=i)

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            provider=self.provider_name,
            model=self.model_name,
            mode="fixture",
            live_enabled=False,
            status="available",
        )

    def _fixture_content(self, prompt: str) -> str:
        from app.runtime.harness.fixtures import default_llm_output

        # 从 prompt 中识别 skill 名并返回对应 fixture
        for skill_name in [
            "BuildLearningPersona", "GenerateLearningPath", "GenerateCourseDoc",
            "GenerateQuiz", "QualityCheck", "GenerateHandsOnLab", "GenerateMindmap",
            "GenerateCoursePPT", "GenerateVideoStoryboard", "RecommendReadings",
            "RunAssessment", "UpdateCapability",
        ]:
            if skill_name.lower() in prompt.lower():
                import json
                return json.dumps(default_llm_output(skill_name), ensure_ascii=False)
        import json
        return json.dumps({"content": f"[fixture] {prompt[:80]}...", "quality_score": 0.75}, ensure_ascii=False)


# ── Factory ──────────────────────────────────────────────────────────────────


def get_llm_provider(
    provider: str | None = None,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> BaseLLMProvider:
    """根据 LLM_PROVIDER 环境变量（或参数）返回对应 Provider。

    - fixture  → FixtureProvider（无需 Key，CI 默认）
    - deepseek → DeepSeekProvider（需 DEEPSEEK_API_KEY）
    - xfyun    → XunfeiSparkProvider（需 XFYUN_API_KEY）
    - Key 缺失时始终抛 ProviderUnavailable；不能把 real 根降级为 fixture。
    """
    from app.core.config import get_settings

    settings = get_settings()
    selected = provider or settings.LLM_PROVIDER

    if selected == "fixture":
        return FixtureProvider()

    if selected == "deepseek":
        from app.llm.deepseek_provider import DeepSeekProvider
        effective_key = settings.DEEPSEEK_API_KEY if api_key is None else api_key
        if not effective_key:
            return _key_missing_fallback("deepseek", "DEEPSEEK_API_KEY", settings)
        return DeepSeekProvider(settings=settings, api_key=effective_key, model=model)

    if selected == "xfyun":
        from app.llm.xfyun_provider import XunfeiSparkProvider
        effective_key = settings.XFYUN_API_KEY if api_key is None else api_key
        if not effective_key:
            return _key_missing_fallback("xfyun", "XFYUN_API_KEY", settings)
        return XunfeiSparkProvider(settings=settings, api_key=effective_key, model=model)

    raise ValueError(f"Unknown LLM_PROVIDER: {selected!r}. Valid: fixture, deepseek, xfyun")


def _key_missing_fallback(provider_name: str, key_name: str, settings: Any) -> BaseLLMProvider:
    from app.runtime.exceptions import ProviderUnavailable

    msg = f"{key_name} not set; {provider_name} provider unavailable"
    raise ProviderUnavailable(msg)


__all__ = [
    "BaseLLMProvider",
    "FixtureProvider",
    "LLMMessage",
    "LLMChunk",
    "LLMResponse",
    "TokenUsage",
    "HealthStatus",
    "get_llm_provider",
]
