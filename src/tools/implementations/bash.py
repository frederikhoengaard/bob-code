import asyncio
from pathlib import Path

from src.tools.base import BaseTool


class BashTool(BaseTool):
    """Tool for executing bash commands"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a bash command in the workspace directory. Returns both stdout and stderr. Use for running scripts, checking file listings, or executing system commands."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                }
            },
            "required": ["command"],
        }

    @property
    def required_permission(self) -> str:
        return "allow_shell_commands"

    async def execute(self, command: str) -> str:
        """Execute bash command with timeout"""
        try:
            # Execute in workspace directory
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.cwd()),
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            except TimeoutError:
                process.kill()
                return f"Error: Command timed out after {self.timeout} seconds"

            # Build output
            output_parts = []

            if stdout:
                stdout_text = stdout.decode().strip()
                if stdout_text:
                    output_parts.append(f"STDOUT:\n{stdout_text}")

            if stderr:
                stderr_text = stderr.decode().strip()
                if stderr_text:
                    output_parts.append(f"STDERR:\n{stderr_text}")

            # Check exit code
            if process.returncode != 0:
                status = f"\nExit code: {process.returncode} (failed)"
            else:
                status = f"\nExit code: {process.returncode} (success)"

            if output_parts:
                return "\n\n".join(output_parts) + status
            else:
                return f"Command executed successfully (no output){status}"

        except Exception as e:
            return f"Error executing command: {str(e)}"
