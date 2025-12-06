from src.providers import LLMProvider
from src.providers.models import Message


class CodeAgent:
    """Main agent that coordinates LLM and tools"""

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str | None = None,
        on_conversation_update: callable | None = None,
    ):
        self.provider = provider
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.conversation_history: list[Message] = []
        self.on_conversation_update = on_conversation_update

    def _default_system_prompt(self) -> str:
        return """You are a helpful coding assistant whose name is Bob. You help the user with:
- Writing code
- Debugging issues
- Explaining concepts
- Suggesting best practices

Be concise and practical in your responses."""

    async def chat(self, user_input: str) -> str:
        """
        Send a message and get a response.

        Args:
            user_input: The user's message

        Returns:
            The agent's response
        """
        # Add user message to history
        self.conversation_history.append(Message(role="user", content=user_input))

        # Build messages with system prompt
        messages = [Message(role="system", content=self.system_prompt), *self.conversation_history]

        # Get response
        response = await self.provider.generate(messages)

        # Add to history
        self.conversation_history.append(Message(role="assistant", content=response))

        # Trigger save callback
        if self.on_conversation_update:
            self.on_conversation_update(self.conversation_history)

        return response

    async def stream_chat(self, user_input: str):
        """Stream a response chunk by chunk"""
        # Add user message
        self.conversation_history.append(Message(role="user", content=user_input))

        # Build messages
        messages = [Message(role="system", content=self.system_prompt), *self.conversation_history]

        # Stream response
        full_response = ""
        async for chunk in self.provider.stream(messages):
            full_response += chunk.content
            yield chunk

        # Add complete response to history
        self.conversation_history.append(Message(role="assistant", content=full_response))

        # Trigger save callback
        if self.on_conversation_update:
            self.on_conversation_update(self.conversation_history)

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
