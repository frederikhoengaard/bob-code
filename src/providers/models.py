from enum import StrEnum

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
    ClaudeOpus = ""
    ClaudeSonnet = "claude-sonnet-4-5-20250929"
    ClaudeHaiku = ""
    # Deepseek
    DeepSeekR1 = "deepseek-r1"


class Message(BaseModel):
    """Unified message format across providers"""

    role: str  # "user", "assistant", "system"
    content: str


class StreamChunk(BaseModel):
    """A chunk of streamed response"""

    content: str
    finish_reason: str | None = None
