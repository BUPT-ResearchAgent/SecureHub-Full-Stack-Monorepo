# Status: [planned]

from app.core.config import get_settings
from app.llm.base import BaseLLMClient
from app.llm.deepseek import DeepSeekClient
from app.llm.xfyun import XFYunClient


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    settings = get_settings()
    selected = provider or settings.LLM_PROVIDER
    if selected == "xfyun":
        return XFYunClient(settings=settings)
    if selected == "deepseek":
        return DeepSeekClient(settings=settings)
    raise ValueError(f"Unsupported LLM provider: {selected}")


__all__ = ["BaseLLMClient", "get_llm_client"]
