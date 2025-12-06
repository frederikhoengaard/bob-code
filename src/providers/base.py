from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .models import LLM, Message, StreamChunk


class LLMProvider(ABC):
    """Base class for all LLM providers"""

    def __init__(self, model: LLM, api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    async def generate(
        self, messages: list[Message], temperature: float = 0.7, max_tokens: int = 4096, **kwargs
    ) -> str:
        """Generate a complete response"""
        pass

    @abstractmethod
    async def stream(
        self, messages: list[Message], temperature: float = 0.7, max_tokens: int = 4096, **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks as they are generated"""
        pass
