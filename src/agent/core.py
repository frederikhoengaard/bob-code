from collections.abc import Callable

from src.prompts import SYSTEM_PROMPT_BASIC
from src.providers import LLMProvider
from src.providers.models import Message


class CodeAgent:
    """Main agent that coordinates LLM and tools"""

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str | None = None,
        on_conversation_update: Callable | None = None,
        tool_registry=None,
        tool_permissions=None,
        on_tool_call: Callable | None = None,
        is_subagent: bool = False,
    ):
        self.provider = provider
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.conversation_history: list[Message] = []
        self.on_conversation_update = on_conversation_update
        self.on_tool_call = on_tool_call
        self.is_subagent = is_subagent

        # Tool support
        self.tool_registry = tool_registry
        self.tool_executor = None
        if tool_registry and tool_permissions:
            from src.tools.executor import ToolExecutor

            self.tool_executor = ToolExecutor(tool_registry, tool_permissions)

    def _default_system_prompt(self) -> str:
        return SYSTEM_PROMPT_BASIC

    async def chat(self, user_input: str, max_iterations: int = 10) -> str:
        """
        Send a message and get a response, with agentic tool calling loop.

        Args:
            user_input: The user's message
            max_iterations: Maximum number of LLM calls (to prevent infinite loops)

        Returns:
            The agent's final response
        """
        # Add user message to history
        self.conversation_history.append(Message(role="user", content=user_input))

        # Agentic loop
        iteration = 0
        final_response = None

        while iteration < max_iterations:
            iteration += 1

            # Build messages with system prompt
            messages = [
                Message(role="system", content=self.system_prompt),
                *self.conversation_history,
            ]

            # Get tool definitions if tools are available
            tools = None
            if self.tool_registry:
                tools = self.tool_registry.get_definitions()

            # Call LLM (returns Message object now, not string)
            response = await self.provider.generate(messages, tools=tools)

            # Add response to history
            self.conversation_history.append(response)

            # Check if LLM wants to call tools
            if response.tool_calls and self.tool_executor:
                # Notify about tool calls
                if self.on_tool_call:
                    await self.on_tool_call(response.tool_calls, None)

                # Execute tools
                tool_results = await self.tool_executor.execute_tool_calls(response.tool_calls)

                # Notify about tool results
                if self.on_tool_call:
                    await self.on_tool_call(response.tool_calls, tool_results)

                # Add tool results to history as tool messages
                for result in tool_results:
                    self.conversation_history.append(
                        Message(
                            role="tool",
                            content=result.content,
                            tool_call_id=result.tool_call_id,
                            name=result.tool_name,
                        )
                    )

                # Continue loop - LLM will see tool results and continue
                continue

            # No tool calls - we're done
            final_response = response.content or ""
            break

        # If we hit max iterations without a final response, use the last response
        if final_response is None:
            final_response = (
                self.conversation_history[-1].content
                if self.conversation_history
                else "Error: Max iterations reached without response"
            )

        # Trigger save callback
        if self.on_conversation_update:
            self.on_conversation_update(self.conversation_history)

        return final_response

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
