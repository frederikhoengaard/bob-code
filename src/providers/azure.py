import os
from collections.abc import AsyncIterator

from openai import AsyncAzureOpenAI

from .base import LLMProvider
from .models import LLM, Message, StreamChunk


class AzureOpenAIProvider(LLMProvider):
    def __init__(self, model: str = LLM.GPT_4o_mini, api_key: str | None = None):
        super().__init__(model, api_key or os.getenv("AZURE_OPENAI_API_KEY"))
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version="2025-04-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

    async def generate(self, messages: list[Message], **kwargs) -> str:
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )

        return response.choices[0].message.content

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[StreamChunk]:
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            stream=True,
        )

        async for chunk in stream:
            if chunk is None:
                continue
            choices = chunk.choices
            if isinstance(choices, list):
                if choices:
                    if choices[0].delta.content is not None:
                        yield StreamChunk(
                            content=choices[0].delta.content,
                            finish_reason=choices[0].finish_reason,
                        )
