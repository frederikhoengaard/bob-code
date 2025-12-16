from src.agent.core import CodeAgent
from src.prompts.system import SYSTEM_PROMPT_EXPLORE, SYSTEM_PROMPT_PLAN
from src.providers import LLMProvider
from src.tools.registry import ToolRegistry
from src.workspace.config import ToolPermissions


class SubagentFactory:
    """Factory for creating specialized subagent configurations"""

    def create_subagent(
        self, provider: LLMProvider, subagent_type: str, on_tool_call=None
    ) -> tuple[CodeAgent, int]:
        """
        Create a specialized subagent with appropriate tools and configuration.

        Returns:
            (agent, max_iterations): Configured agent and iteration limit
        """
        if subagent_type == "explore":
            return self._create_explore_agent(provider, on_tool_call)
        elif subagent_type == "plan":
            return self._create_plan_agent(provider, on_tool_call)
        else:
            raise ValueError(f"Unknown subagent type: {subagent_type}")

    def _create_explore_agent(self, provider: LLMProvider, on_tool_call) -> tuple[CodeAgent, int]:
        """Create Explore agent: fast, read-only codebase exploration"""

        # Lazy import to avoid circular dependency
        from src.tools.implementations import BashTool, ReadTool

        # Read-only tools (no EditTool - explore is read-only)
        tool_registry = ToolRegistry()
        tool_registry.register(ReadTool())
        tool_registry.register(BashTool(timeout=10))  # Shorter timeout

        # Read-only permissions
        permissions = ToolPermissions(
            allow_file_operations=True, allow_shell_commands=True, allow_network_access=False
        )

        agent = CodeAgent(
            provider=provider,
            system_prompt=SYSTEM_PROMPT_EXPLORE,
            tool_registry=tool_registry,
            tool_permissions=permissions,
            on_tool_call=on_tool_call,
            is_subagent=True,  # Prevent recursion
        )

        # Lower iteration limit for fast exploration
        max_iterations = 5

        return agent, max_iterations

    def _create_plan_agent(self, provider: LLMProvider, on_tool_call) -> tuple[CodeAgent, int]:
        """Create Plan agent: architecture and implementation planning"""

        # Lazy import to avoid circular dependency
        from src.tools.implementations import BashTool, EditTool, ReadTool, WriteTool

        # Full tool access
        tool_registry = ToolRegistry()
        read_tool = ReadTool()
        tool_registry.register(read_tool)
        tool_registry.register(WriteTool())
        tool_registry.register(BashTool())
        tool_registry.register(EditTool(read_tool=read_tool))

        # Full permissions (but NO Task tool - no recursion)
        permissions = ToolPermissions(
            allow_file_operations=True, allow_shell_commands=True, allow_network_access=False
        )

        agent = CodeAgent(
            provider=provider,
            system_prompt=SYSTEM_PROMPT_PLAN,
            tool_registry=tool_registry,
            tool_permissions=permissions,
            on_tool_call=on_tool_call,
            is_subagent=True,  # Prevent recursion
        )

        # Higher iteration limit for thorough planning
        max_iterations = 15

        return agent, max_iterations
