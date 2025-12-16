from src.tools.base import BaseTool


class EditTool(BaseTool):
    """Tool for performing exact string replacements in files"""

    def __init__(self, read_tool=None):
        """
        Initialize EditTool.

        Args:
            read_tool: Optional ReadTool instance to check if files were read first
        """
        self.read_tool = read_tool

    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return """Performs exact string replacements in files.

Usage:
- You must use the `read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file.
- When editing text from read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`.
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences of old_string (default false)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    @property
    def required_permission(self) -> str | None:
        return "allow_file_operations"

    async def execute(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> str:
        """
        Execute exact string replacement in a file.

        Args:
            file_path: Absolute path to the file to modify
            old_string: The text to replace
            new_string: The text to replace it with
            replace_all: Whether to replace all occurrences (default: False)

        Returns:
            Success message or error description
        """
        import os

        # Validate inputs
        if old_string == new_string:
            return "Error: old_string and new_string must be different"

        # Check if file was read first (if read_tool is provided)
        if self.read_tool and not self.read_tool.has_read_file(file_path):
            return f"Error: You must use the `read` tool to read {file_path} before editing it"

        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Check if it's a file (not a directory)
        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"

        try:
            # Read the file content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists in the file
            if old_string not in content:
                return f"Error: old_string not found in {file_path}"

            # Perform replacement
            if replace_all:
                # Replace all occurrences
                occurrences = content.count(old_string)
                new_content = content.replace(old_string, new_string)
                replacement_msg = f"Replaced {occurrences} occurrence(s)"
            else:
                # Replace only first occurrence, but check for uniqueness
                occurrences = content.count(old_string)
                if occurrences > 1:
                    return f"Error: old_string is not unique in {file_path} (found {occurrences} occurrences). Either provide a larger string with more surrounding context to make it unique or use `replace_all=true` to change every instance."

                new_content = content.replace(old_string, new_string, 1)
                replacement_msg = "Replaced 1 occurrence"

            # Write the modified content back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Successfully edited {file_path}. {replacement_msg}."

        except PermissionError:
            return f"Error: Permission denied when trying to edit {file_path}"
        except UnicodeDecodeError:
            return f"Error: File {file_path} is not a valid UTF-8 text file"
        except Exception as e:
            return f"Error editing {file_path}: {str(e)}"
