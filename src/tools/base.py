from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel


class FunctionDefinition(BaseModel):
    """Function schema for OpenAI format"""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters


class ToolDefinition(BaseModel):
    """Schema for a tool that can be called by the LLM"""

    type: Literal["function"] = "function"
    function: FunctionDefinition


class ToolResult(BaseModel):
    """Result of executing a tool"""

    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False


class BaseTool(ABC):
    """Base class for all tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters"""
        pass

    @property
    @abstractmethod
    def required_permission(self) -> str | None:
        """Permission required to use this tool (maps to ToolPermissions field)"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass

    def to_definition(self) -> ToolDefinition:
        """Convert to OpenAI tool definition format"""
        return ToolDefinition(
            type="function",
            function=FunctionDefinition(
                name=self.name, description=self.description, parameters=self.parameters_schema
            ),
        )
