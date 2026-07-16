# Status: real

"""Server-owned chat model catalog used by credentials and durable roots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_SUPPORTED_PROVIDERS = frozenset({"deepseek", "xfyun"})
_KNOWN_MODELS: dict[str, tuple[str, ...]] = {
    "deepseek": ("deepseek-chat", "deepseek-reasoner", "deepseek-v4-pro"),
    "xfyun": ("spark-x", "spark-v4"),
}
_PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "xfyun": "讯飞星火",
}
_MODEL_LABELS = {
    "deepseek-chat": "DeepSeek Chat",
    "deepseek-reasoner": "DeepSeek Reasoner",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "spark-x": "Spark X2 Flash",
    "spark-v4": "Spark v4",
}


class ModelSourceError(ValueError):
    """A requested provider/model pair is outside the server-owned catalog."""


@dataclass(frozen=True)
class ProviderModelSource:
    provider: str
    model: str
    label: str
    model_label: str


def configured_model(settings: Any, provider: str) -> str:
    if provider == "deepseek":
        return str(getattr(settings, "DEEPSEEK_MODEL", "") or "deepseek-chat").strip()
    if provider == "xfyun":
        return str(getattr(settings, "XFYUN_MODEL", "") or "spark-v4").strip()
    raise ModelSourceError("unsupported provider")


def model_sources(settings: Any) -> tuple[ProviderModelSource, ...]:
    """Return one selectable, configured model per supported provider."""
    return tuple(
        _source(provider, configured_model(settings, provider))
        for provider in ("deepseek", "xfyun")
    )


def default_model_source(settings: Any) -> ProviderModelSource:
    provider = _normalise_provider(getattr(settings, "LLM_PROVIDER", ""))
    return _source(provider, configured_model(settings, provider))


def resolve_model_source(
    settings: Any,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> ProviderModelSource:
    """Resolve an explicit pair or a configured source without accepting arbitrary IDs."""
    selected_provider = _normalise_provider(provider) if provider is not None else default_model_source(settings).provider
    selected_model = str(model).strip() if model is not None else configured_model(settings, selected_provider)
    if not selected_model or selected_model not in supported_models(settings, selected_provider):
        raise ModelSourceError("unsupported model")
    return _source(selected_provider, selected_model)


def supported_models(settings: Any, provider: str) -> frozenset[str]:
    selected_provider = _normalise_provider(provider)
    configured = configured_model(settings, selected_provider)
    return frozenset((*_KNOWN_MODELS[selected_provider], configured))


def _source(provider: str, model: str) -> ProviderModelSource:
    return ProviderModelSource(
        provider=provider,
        model=model,
        label=_PROVIDER_LABELS[provider],
        model_label=_MODEL_LABELS.get(model, model),
    )


def _normalise_provider(value: object) -> str:
    provider = str(value or "").strip().lower()
    if provider not in _SUPPORTED_PROVIDERS:
        raise ModelSourceError("unsupported provider")
    return provider


__all__ = [
    "ModelSourceError",
    "ProviderModelSource",
    "configured_model",
    "default_model_source",
    "model_sources",
    "resolve_model_source",
    "supported_models",
]
