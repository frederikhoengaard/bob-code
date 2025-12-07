import asyncio
import json

from src.tools.base import ToolCall, ToolResult
from src.tools.registry import ToolRegistry
from src.workspace.config import ToolPermissions


class ToolExecutor:
    """Handles tool execution with permission checks"""

    def __init__(self, registry: ToolRegistry, permissions: ToolPermissions):
        self.registry = registry
        self.permissions = permissions

    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call with permission check"""
        tool_name = tool_call.function.name
        tool = self.registry.get(tool_name)

        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=f"Error: Unknown tool '{tool_name}'",
                is_error=True,
            )

        # Check permission
        if tool.required_permission:
            if not getattr(self.permissions, tool.required_permission, False):
                return ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=f"Error: Permission denied. This tool requires '{tool.required_permission}' to be enabled in workspace settings.",
                    is_error=True,
                )

        # Parse arguments
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=f"Error: Invalid JSON arguments: {str(e)}",
                is_error=True,
            )

        # Execute tool
        try:
            result = await tool.execute(**args)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name=tool_name, content=result, is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=f"Error executing tool: {str(e)}",
                is_error=True,
            )

    async def execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute multiple tool calls in parallel"""
        return await asyncio.gather(*[self.execute_tool_call(tc) for tc in tool_calls])
