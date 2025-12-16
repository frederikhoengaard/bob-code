from src.tools.base import BaseTool


class SlashCommandTool(BaseTool):
    """Tool for executing slash commands programmatically"""

    def __init__(self, command_handler=None):
        """
        Initialize SlashCommandTool.

        Args:
            command_handler: Async callback function(command: str) -> str
                           Should execute the slash command and return the result
        """
        self.command_handler = command_handler

    @property
    def name(self) -> str:
        return "slash_command"

    @property
    def description(self) -> str:
        return """Execute a slash command within the main conversation

How slash commands work:
When you use this tool or when a user types a slash command, you will see <command-message>{name} is running…</command-message> followed by the expanded prompt. For example, if .claude/commands/foo.md contains "Print today's date", then /foo expands to that prompt in the next message.

Usage:
- `command` (required): The slash command to execute, including any arguments
- Example: `command: "/review-pr 123"`

IMPORTANT: Only use this tool for custom slash commands that appear in the Available Commands list below. Do NOT use for:
- Built-in CLI commands (like /help, /clear, etc.)
- Commands not shown in the list
- Commands you think might exist but aren't listed

Notes:
- When a user requests multiple slash commands, execute each one sequentially and check for <command-message>{name} is running…</command-message> to verify each has been processed
- Do not invoke a command that is already running. For example, if you see <command-message>foo is running…</command-message>, do NOT use this tool with "/foo" - process the expanded prompt in the following message
- Only custom slash commands with descriptions are listed in Available Commands. If a user's command is not listed, ask them to check the slash command file and consult the docs."""

    @property
    def parameters_schema(self) -> dict:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": 'The slash command to execute with its arguments, e.g., "/review-pr 123"',
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        }

    @property
    def required_permission(self) -> str | None:
        # No specific permission required - slash commands have their own access control
        return None

    async def execute(self, command: str) -> str:
        """
        Execute a slash command.

        Args:
            command: The slash command to execute (e.g., "/help", "/model gpt-4")

        Returns:
            Result of the command execution
        """
        # Validate command format
        if not command:
            return "Error: Command cannot be empty"

        if not command.startswith("/"):
            return f"Error: Slash commands must start with '/'. Did you mean '/{command}'?"

        # Check if callback is available
        if not self.command_handler:
            return "Error: SlashCommand tool not properly initialized (no command handler provided)"

        try:
            # Call the handler to execute the command
            result = await self.command_handler(command)
            return result or "Command executed successfully (no output)"

        except Exception as e:
            return f"Error executing command '{command}': {str(e)}"
