from app.config import settings
from .base import LLMError, LLMProvider, LLMRetryable
from .groq import GroqProvider
from .ollama import OllamaProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            settings.ollama_url,
            settings.llm_model,
            settings.num_ctx,
        )

    if settings.llm_provider == "groq":
        return GroqProvider(
            settings.groq_api_key,
            settings.groq_model,
            settings.num_ctx,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


__all__ = [
    "get_provider",
    "LLMProvider",
    "LLMError",
    "LLMRetryable",
]