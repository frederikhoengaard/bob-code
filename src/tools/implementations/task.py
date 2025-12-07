from typing import Literal

from src.agent.subagent import SubagentFactory
from src.tools.base import BaseTool


class TaskTool(BaseTool):
    """Tool for spawning specialized subagents to handle complex tasks"""

    def __init__(self, provider_factory, is_subagent: bool = False, on_subagent_event=None):
        """
        Args:
            provider_factory: Callable that creates a new LLMProvider instance
            is_subagent: Whether this tool is running in a subagent (prevents recursion)
            on_subagent_event: Callback for subagent lifecycle events
        """
        self.provider_factory = provider_factory
        self.is_subagent = is_subagent
        self.on_subagent_event = on_subagent_event
        self.subagent_factory = SubagentFactory()

    @property
    def name(self) -> str:
        return "task"

    @property
    def description(self) -> str:
        return """Spawn a specialized subagent to handle complex tasks requiring focused expertise.

Available subagent types:
- 'explore': Fast codebase exploration with read-only tools (read, bash ls/find/git)
- 'plan': Architecture and implementation planning with full tool access

The subagent receives ONLY the task_prompt - no conversation history is shared.
You control what context to provide via the prompt."""

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task_prompt": {
                    "type": "string",
                    "description": "The task description and any context needed. Be explicit - no conversation history is shared.",
                },
                "subagent_type": {
                    "type": "string",
                    "enum": ["explore", "plan"],
                    "description": "Type of subagent: 'explore' for read-only exploration, 'plan' for planning",
                },
                "model": {
                    "type": "string",
                    "description": "Optional: Override model for subagent (uses parent's model by default)",
                    "default": None,
                },
            },
            "required": ["task_prompt", "subagent_type"],
        }

    @property
    def required_permission(self) -> str | None:
        # Task tool itself doesn't require permission
        return None

    async def execute(
        self, task_prompt: str, subagent_type: Literal["explore", "plan"], model: str | None = None
    ) -> str:
        """Execute task by spawning a specialized subagent"""

        # Prevent recursion
        if self.is_subagent:
            return "Error: Subagents cannot spawn additional subagents. Please complete this task directly."

        # Validate subagent type
        if subagent_type not in ["explore", "plan"]:
            return f"Error: Invalid subagent_type '{subagent_type}'. Must be 'explore' or 'plan'."

        try:
            # Notify start
            if self.on_subagent_event:
                await self.on_subagent_event("start", subagent_type, task_prompt)

            # Create provider
            provider = self.provider_factory(model) if model else self.provider_factory()

            # Create specialized subagent
            subagent, max_iterations = self.subagent_factory.create_subagent(
                provider=provider,
                subagent_type=subagent_type,
                on_tool_call=self._wrap_on_tool_call,
            )

            # Execute subagent task
            result = await subagent.chat(task_prompt, max_iterations=max_iterations)

            # Notify completion
            if self.on_subagent_event:
                await self.on_subagent_event("complete", subagent_type, result)

            return result

        except Exception as e:
            error_msg = f"Error executing {subagent_type} subagent: {str(e)}"
            if self.on_subagent_event:
                await self.on_subagent_event("error", subagent_type, error_msg)
            return error_msg

    async def _wrap_on_tool_call(self, tool_calls, tool_results):
        """Relay subagent tool calls to parent's callback"""
        if self.on_subagent_event:
            await self.on_subagent_event("tool_call", tool_calls, tool_results)
