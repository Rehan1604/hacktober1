from app.config import settings

from .ollama import OllamaProvider
from .base import LLMError, LLMProvider, LLMRetryable

def get_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings.ollama_url, settings.llm_model, settings.num_ctx)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


__all__ = ["get_provider", "LLMProvider", "LLMError", "LLMRetryable"]