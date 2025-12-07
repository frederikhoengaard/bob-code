import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from src.providers.models import LLM


class ToolPermissions(BaseModel):
    """Placeholder for future tool permissions"""

    allow_file_operations: bool = False
    allow_shell_commands: bool = False
    allow_network_access: bool = False


class WorkspaceSettings(BaseModel):
    """Workspace configuration"""

    model: str  # LLM enum value
    permissions: ToolPermissions = ToolPermissions()
    created_at: str  # ISO timestamp
    last_updated: str  # ISO timestamp


class WorkspaceConfig:
    """Manages workspace settings and initialization"""

    def __init__(self, workspace_dir: str | None = None):
        """
        Initialize workspace configuration.

        Args:
            workspace_dir: Directory for workspace. Defaults to current working directory.
        """
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path(os.getcwd())
        self.bob_dir = self.workspace_dir / ".bob"

    def initialize_workspace(self) -> bool:
        """
        Create .bob/ directory structure if it doesn't exist.

        Returns:
            True if workspace was created, False if it already existed.

        Raises:
            PermissionError: If unable to create directories due to permissions.
            OSError: If unable to create directories for other reasons.
        """
        if self.bob_dir.exists():
            return False

        # Create .bob/ and .bob/conversations/
        self.bob_dir.mkdir(parents=True, exist_ok=True)
        self.get_conversations_dir().mkdir(parents=True, exist_ok=True)

        return True

    def load_settings(self) -> WorkspaceSettings:
        """
        Load settings from .bob/settings.json.

        Returns:
            WorkspaceSettings object.

        Raises:
            FileNotFoundError: If settings.json doesn't exist.
            ValidationError: If JSON is malformed or invalid.
        """
        settings_path = self.get_settings_path()

        if not settings_path.exists():
            raise FileNotFoundError(f"Settings file not found: {settings_path}")

        try:
            with open(settings_path) as f:
                data = json.load(f)
            return WorkspaceSettings(**data)
        except (json.JSONDecodeError, ValidationError):
            # Backup corrupted file and raise
            backup_path = settings_path.with_suffix(".json.bak")
            shutil.copy(settings_path, backup_path)

            # Create fresh settings with defaults
            default_settings = WorkspaceSettings(
                model=str(LLM.GPT_4o_mini),
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
            )
            self.save_settings(default_settings)

            import sys

            print(
                f"Warning: Corrupted settings.json backed up to {backup_path}",
                file=sys.stderr,
            )

            return default_settings

    def save_settings(self, settings: WorkspaceSettings) -> None:
        """
        Save settings to .bob/settings.json with updated timestamp.

        Args:
            settings: WorkspaceSettings object to save.

        Raises:
            OSError: If unable to write file.
        """
        # Update last_updated timestamp
        settings.last_updated = datetime.now().isoformat()

        settings_path = self.get_settings_path()
        with open(settings_path, "w") as f:
            json.dump(settings.model_dump(), f, indent=2)

    def update_model(self, model: LLM) -> None:
        """
        Update model in settings and save.

        Args:
            model: LLM enum value.

        Raises:
            FileNotFoundError: If settings.json doesn't exist.
            OSError: If unable to write file.
        """
        settings = self.load_settings()
        settings.model = str(model)
        self.save_settings(settings)

    def get_settings_path(self) -> Path:
        """
        Get path to settings.json.

        Returns:
            Path to .bob/settings.json.
        """
        return self.bob_dir / "settings.json"

    def get_conversations_dir(self) -> Path:
        """
        Get path to conversations directory.

        Returns:
            Path to .bob/conversations/.
        """
        return self.bob_dir / "conversations"
