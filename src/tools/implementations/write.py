from pathlib import Path

from src.tools.base import BaseTool


class WriteTool(BaseTool):
    """Tool for writing content to files"""

    @property
    def name(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return "Write or overwrite a file with the specified content. Creates parent directories if needed. Use this to create new files or modify existing ones."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write (relative to workspace root or absolute)",
                },
                "content": {
                    "type": "string",
                    "description": "The complete content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    @property
    def required_permission(self) -> str:
        return "allow_file_operations"

    async def execute(self, file_path: str, content: str) -> str:
        """Write content to file with security checks"""
        try:
            path = Path(file_path)

            # Security: prevent directory traversal outside workspace
            workspace_root = Path.cwd()

            # Handle both absolute and relative paths
            if path.is_absolute():
                resolved_path = path.resolve()
            else:
                resolved_path = (workspace_root / path).resolve()

            # Ensure path is within workspace
            try:
                resolved_path.relative_to(workspace_root)
            except ValueError:
                return f"Error: Cannot write files outside workspace root ({workspace_root})"

            # Create parent directories if needed
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            resolved_path.write_text(content)

            # Return success message with stats
            line_count = len(content.splitlines())
            char_count = len(content)
            relative_path = resolved_path.relative_to(workspace_root)

            return f"Successfully wrote to {relative_path}\nLines: {line_count} | Characters: {char_count}"

        except PermissionError:
            return f"Error: Permission denied writing file: {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
