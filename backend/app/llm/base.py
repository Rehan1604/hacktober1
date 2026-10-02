from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMError(Exception):
    """Anything that went wrong talking to the model."""

class LLMRetryable(LLMError):
    """Transient model failure (e.g. a repetition loop). Safe to retry."""
    
class LLMProvider(ABC):
    model: str

    @abstractmethod
    async def generate(self, system: str, user: str, json_mode: bool = False) -> str:
        """Return the full response text."""

    @abstractmethod
    def stream(self, system: str, user: str) -> AsyncIterator[str]:
        """Yield response text chunks as they are produced."""

    @abstractmethod
    async def health(self) -> dict:
        """Return {'ok': bool, 'model_installed': bool}."""