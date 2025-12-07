from src.tools.base import BaseTool, ToolDefinition


class ToolRegistry:
    """Manages available tools"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get tool by name"""
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        """Get all registered tools"""
        return list(self._tools.values())

    def get_definitions(self) -> list[ToolDefinition]:
        """Get tool definitions for LLM"""
        return [tool.to_definition() for tool in self._tools.values()]
