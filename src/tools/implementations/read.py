from pathlib import Path

from src.tools.base import BaseTool
from src.utils.gitignore import GitignoreFilter


class ReadTool(BaseTool):
    """Tool for reading file contents"""

    def __init__(self):
        """Initialize ReadTool with file tracking"""
        self._read_files = set()

    def has_read_file(self, file_path: str) -> bool:
        """Check if a file has been read"""
        # Normalize path for comparison
        try:
            resolved = Path(file_path).resolve()
            return str(resolved) in self._read_files
        except Exception:
            return False

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the specified path. Use this to examine files in the workspace before making changes or to understand the codebase structure."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read (relative to workspace root or absolute)",
                }
            },
            "required": ["file_path"],
        }

    @property
    def required_permission(self) -> str:
        return "allow_file_operations"

    async def execute(self, file_path: str) -> str:
        """Read file contents with security checks"""
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
                return f"Error: Cannot read files outside workspace root ({workspace_root})"

            if not resolved_path.exists():
                return f"Error: File not found: {file_path}"

            if not resolved_path.is_file():
                return f"Error: Path is not a file: {file_path}"

            # Check gitignore - prevent reading gitignored files
            gitignore = GitignoreFilter(workspace_root)
            if gitignore.should_ignore(resolved_path):
                return f"Error: Cannot read '{file_path}' - file is excluded by .gitignore"

            content = resolved_path.read_text()

            # Track that this file was read
            self._read_files.add(str(resolved_path))

            # Add file info for context
            line_count = len(content.splitlines())
            char_count = len(content)

            return f"File: {resolved_path.relative_to(workspace_root)}\nLines: {line_count} | Characters: {char_count}\n\n{content}"

        except PermissionError:
            return f"Error: Permission denied reading file: {file_path}"
        except UnicodeDecodeError:
            return f"Error: File is not a text file or uses unsupported encoding: {file_path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
