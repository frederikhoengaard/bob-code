from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class LLM(StrEnum):
    # OpenAI
    GPT_5_1 = "gpt-5.1-2025-11-13"
    GPT_5 = "gpt-5-2025-08-07"
    GPT_5_mini = "gpt-5-mini-2025-08-07"
    GPT_5_nano = "gpt-5-nano-2025-08-07"
    GPT_4o = "gpt-4o-2024-08-06"
    GPT_4o_mini = "gpt-4o-mini-2024-07-18"
    # Anthropic
    ClaudeOpus = "claude-opus-4-5-20251101"
    ClaudeSonnet = "claude-sonnet-4-5-20250929"
    ClaudeHaiku = "claude-haiku-4-5-20251001"
    # Deepseek
    DeepSeekR1 = "deepseek-r1"


class FunctionCall(BaseModel):
    """Function call details"""

    name: str
    arguments: str  # JSON string of arguments


class ToolCall(BaseModel):
    """A tool call from the LLM"""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class Message(BaseModel):
    """Unified message format across providers - backward compatible"""

    role: str  # "user", "assistant", "system", "tool"
    content: str | None = None

    # Tool-related fields (optional for backward compatibility)
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None  # For tool response messages
    name: str | None = None  # Tool name for tool response messages


class StreamChunk(BaseModel):
    """A chunk of streamed response"""

    content: str | None = None
    finish_reason: str | None = None
