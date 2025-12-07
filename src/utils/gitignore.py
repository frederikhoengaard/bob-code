"""Gitignore filtering utility for file exploration"""

from pathlib import Path

# Feature flag - hardcoded to True for now
SKIP_GITIGNORE_FILES = True


class GitignoreFilter:
    """Filter files and directories based on .gitignore patterns"""

    def __init__(self, workspace_root: Path | None = None):
        """
        Initialize gitignore filter

        Args:
            workspace_root: Root directory to search for .gitignore (defaults to cwd)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.spec = None

        if SKIP_GITIGNORE_FILES:
            self._load_gitignore()

    def _load_gitignore(self):
        """Load and parse .gitignore file if it exists"""
        gitignore_path = self.workspace_root / ".gitignore"

        if not gitignore_path.exists():
            return

        try:
            import pathspec

            with open(gitignore_path) as f:
                patterns = f.read().splitlines()

            # Create PathSpec from gitignore patterns
            self.spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception as e:
            # If loading fails, we'll just not filter anything
            import sys

            print(f"Warning: Could not load .gitignore: {e}", file=sys.stderr)
            self.spec = None

    def should_ignore(self, path: Path | str) -> bool:
        """
        Check if a path should be ignored based on gitignore patterns

        Args:
            path: Path to check (can be relative or absolute)

        Returns:
            True if the path should be ignored, False otherwise
        """
        # If feature is disabled or no spec loaded, don't ignore anything
        if not SKIP_GITIGNORE_FILES or self.spec is None:
            return False

        # Convert to Path object
        if isinstance(path, str):
            path = Path(path)

        # Make path relative to workspace root for matching
        try:
            if path.is_absolute():
                rel_path = path.relative_to(self.workspace_root)
            else:
                rel_path = path
        except ValueError:
            # Path is outside workspace, don't ignore
            return False

        # Convert to string for pathspec matching
        # Use posix path for consistent matching across platforms
        path_str = rel_path.as_posix()

        # Check if path matches any gitignore pattern
        return self.spec.match_file(path_str)

    def filter_paths(self, paths: list[Path | str]) -> list[Path]:
        """
        Filter a list of paths, removing ignored ones

        Args:
            paths: List of paths to filter

        Returns:
            List of paths that should not be ignored
        """
        result = []
        for path in paths:
            path_obj = Path(path) if isinstance(path, str) else path
            if not self.should_ignore(path_obj):
                result.append(path_obj)
        return result
