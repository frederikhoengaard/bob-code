import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .base import LLMProvider
from .models import LLM, Message, StreamChunk


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = LLM.GPT_4o_mini, api_key: str | None = None):
        super().__init__(model, api_key or os.getenv("OPENAI_API_KEY"))
        self.client = AsyncOpenAI(api_key=self.api_key)

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
            if chunk.choices[0].delta.content is not None:
                yield StreamChunk(
                    content=chunk.choices[0].delta.content,
                    finish_reason=chunk.choices[0].finish_reason,
                )
