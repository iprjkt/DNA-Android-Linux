"""Path management and workspace layout abstractions for DNA-Linux."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


def get_default_workspace_root() -> Path:
    """Return the default DNA workspaces root directory (~/DNA or $DNA_HOME)."""
    env_home = os.environ.get("DNA_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / "DNA").resolve()


def get_global_config_dir() -> Path:
    """Return global config directory (~/.config/dna-linux or $XDG_CONFIG_HOME/dna-linux)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return (Path(xdg_config) / "dna-linux").resolve()
    return (Path.home() / ".config" / "dna-linux").resolve()


def normalize_project_name(raw_name: str) -> str:
    """Normalize and validate a project name (no path separators, non-empty)."""
    name = raw_name.strip()
    if not name:
        raise ValueError("Project name cannot be empty.")
    # Strip any prefix like 'DNA_' if user passed it
    if name.startswith("DNA_") and len(name) > 4:
        name = name[4:]
    # Check for invalid characters
    if not re.match(r"^[a-zA-Z0-9_\.\-]+$", name):
        raise ValueError(
            f"Invalid project name '{name}'. Only alphanumeric characters, dashes, and underscores are allowed."
        )
    return name


@dataclass(frozen=True)
class ProjectPaths:
    """Paths specific to an active DNA project workspace."""

    project_dir: Path

    @property
    def project_name(self) -> str:
        name = self.project_dir.name
        if name.startswith("DNA_"):
            return name[4:]
        return name

    @property
    def rom_dir(self) -> Path:
        return self.project_dir / "rom"

    @property
    def images_dir(self) -> Path:
        return self.project_dir / "images"

    @property
    def unpacked_dir(self) -> Path:
        return self.project_dir / "unpacked"

    @property
    def config_dir(self) -> Path:
        """Directory storing SELinux file_contexts and fs_config files."""
        return self.project_dir / "config"

    @property
    def out_dir(self) -> Path:
        return self.project_dir / "out"

    @property
    def plugins_dir(self) -> Path:
        return self.project_dir / "plugins"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"

    @property
    def project_file(self) -> Path:
        return self.project_dir / "project.toml"

    def ensure_layout(self) -> None:
        """Create all project subdirectories if they do not exist."""
        for path in (
            self.project_dir,
            self.rom_dir,
            self.images_dir,
            self.unpacked_dir,
            self.config_dir,
            self.out_dir,
            self.plugins_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def is_safe_subpath(self, target: Path) -> bool:
        """Verify that target resides strictly within this project directory."""
        try:
            resolved_target = target.resolve()
            resolved_project = self.project_dir.resolve()
            return resolved_project == resolved_target or resolved_project in resolved_target.parents
        except (OSError, RuntimeError):
            return False

    def validate_safe_subpath(self, target: Path) -> Path:
        """Raise PermissionError if target is outside this project directory."""
        resolved = target.resolve()
        if not self.is_safe_subpath(resolved):
            raise PermissionError(
                f"Safety violation: Path '{resolved}' is outside project directory '{self.project_dir}'."
            )
        return resolved

    @classmethod
    def from_name(cls, name: str, root_dir: Path | None = None) -> ProjectPaths:
        """Instantiate ProjectPaths from a project name and root directory."""
        clean_name = normalize_project_name(name)
        root = (root_dir or get_default_workspace_root()).resolve()
        return cls(project_dir=root / f"DNA_{clean_name}")

    @classmethod
    def from_path(cls, path: Path | str) -> ProjectPaths:
        """Instantiate ProjectPaths from an existing or explicit directory path."""
        p = Path(path).expanduser().resolve()
        return cls(project_dir=p)
