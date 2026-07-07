# Status: real

"""统一异常类型 — 供 service 层、endpoint、Harness 共用。

rule §3.7: 所有 skill 运行通过 AgentRunService，所有错误通过此模块抛出。
B 的 endpoint 只需 except 这些类型并转换为 HTTP 错误响应。
"""

from app.runtime.harness.errors import (
    GuardrailBlocked,
    GuardrailViolation,
    HarnessError,
    InsufficientEvidence,
    QualityCheckFailed,
    QualityRejected,
    SafetyBlocked,
    SkillTimeout,
    ToolUnavailable,
)


class LLMProviderError(HarnessError):
    """LLM Provider 调用失败（网络、限流、认证等）。"""

    code = "llm_provider_error"


class ArtifactPersistError(HarnessError):
    """生成资源写入 storage / generated_resources 失败。"""

    code = "artifact_persist_error"


class ProviderUnavailable(LLMProviderError):
    """Provider 当前不可用（健康检查失败 / Key 缺失）。"""

    code = "provider_unavailable"


class BudgetExceeded(HarnessError):
    """超过每日 LLM 调用预算限制。"""

    code = "budget_exceeded"


__all__ = [
    "HarnessError",
    "InsufficientEvidence",
    "ToolUnavailable",
    "SafetyBlocked",
    "GuardrailViolation",
    "GuardrailBlocked",
    "QualityCheckFailed",
    "QualityRejected",
    "SkillTimeout",
    "LLMProviderError",
    "ArtifactPersistError",
    "ProviderUnavailable",
    "BudgetExceeded",
]
