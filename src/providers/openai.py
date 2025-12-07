import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .base import LLMProvider
from .models import LLM, FunctionCall, Message, StreamChunk, ToolCall


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = LLM.GPT_4o_mini, api_key: str | None = None):
        super().__init__(model, api_key or os.getenv("OPENAI_API_KEY"))
        self.client = AsyncOpenAI(api_key=self.api_key)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert unified Message format to OpenAI format including tool fields"""
        result = []
        for msg in messages:
            openai_msg = {"role": msg.role}

            if msg.content:
                openai_msg["content"] = msg.content

            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]

            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id

            if msg.name:
                openai_msg["name"] = msg.name

            result.append(openai_msg)

        return result

    async def generate(self, messages: list[Message], tools: list = None, **kwargs) -> Message:
        """Generate a complete response, optionally with tool calling support"""
        openai_messages = self._convert_messages(messages)

        params = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Add tools if provided
        if tools:
            params["tools"] = [t.model_dump() for t in tools]

        response = await self.client.chat.completions.create(**params)

        choice = response.choices[0]
        message = choice.message

        # Convert to unified Message format
        result = Message(role="assistant", content=message.content)

        # Parse tool calls if present
        if message.tool_calls:
            result.tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function=FunctionCall(name=tc.function.name, arguments=tc.function.arguments),
                )
                for tc in message.tool_calls
            ]

        return result

    async def stream(
        self, messages: list[Message], tools: list = None, **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks. Note: Tool calling is not supported in streaming mode."""
        openai_messages = self._convert_messages(messages)

        # Note: We don't pass tools in streaming mode as it complicates handling
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
