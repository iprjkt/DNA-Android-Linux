"""User configuration manager for DNA-Linux."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dna_core.paths import (
    get_default_io_root,
    get_default_work_root,
    get_default_workspace_root,
    get_global_config_dir,
)


@dataclass
class GlobalConfig:
    """Global configuration settings for DNA-Linux."""

    workspace_root: str = field(default_factory=lambda: str(get_default_io_root()))
    io_root: str = field(default_factory=lambda: str(get_default_io_root()))
    work_root: str = field(default_factory=lambda: str(get_default_work_root()))
    active_project: str | None = None
    auto_confirm: bool = False
    verbose: bool = False
    background_image: str | None = None
    tool_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        default_io = str(get_default_io_root())
        if self.workspace_root != default_io and self.io_root == default_io:
            self.io_root = self.workspace_root
        elif self.io_root != default_io and self.workspace_root == default_io:
            self.workspace_root = self.io_root

    @classmethod
    def load(cls, config_path: Path | None = None) -> GlobalConfig:
        """Load global config from file, or return defaults if file does not exist."""
        path = config_path or (get_global_config_dir() / "config.toml")
        if not path.is_file():
            return cls()

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            ws_val = data.get("workspace_root")
            io_val = data.get("io_root")
            chosen_io = io_val or ws_val or str(get_default_io_root())
            chosen_work = data.get("work_root", str(get_default_work_root()))
            return cls(
                workspace_root=ws_val or chosen_io,
                io_root=chosen_io,
                work_root=chosen_work,
                active_project=data.get("active_project"),
                auto_confirm=data.get("auto_confirm", False),
                verbose=data.get("verbose", False),
                background_image=data.get("background_image"),
                tool_overrides=data.get("tool_overrides", {}),
            )
        except Exception:
            return cls()

    def save(self, config_path: Path | None = None) -> Path:
        """Persist global configuration to disk."""
        path = config_path or (get_global_config_dir() / "config.toml")
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# DNA-Linux Global Configuration",
            f'io_root = "{self.io_root}"',
            f'work_root = "{self.work_root}"',
            f'workspace_root = "{self.workspace_root}"',
        ]
        if self.active_project:
            lines.append(f'active_project = "{self.active_project}"')
        else:
            lines.append('# active_project = ""')

        lines.append(f"auto_confirm = {str(self.auto_confirm).lower()}")
        lines.append(f"verbose = {str(self.verbose).lower()}")
        if self.background_image:
            lines.append(f'background_image = "{self.background_image}"')
        else:
            lines.append('# background_image = ""')

        lines.append("\n[tool_overrides]")
        for tool_name, tool_path in self.tool_overrides.items():
            lines.append(f'{tool_name} = "{tool_path}"')

        content = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path


def get_background_image(config: GlobalConfig | None = None) -> str | None:
    """Return the currently configured custom background image path, or None."""
    cfg = config or GlobalConfig.load()
    return cfg.background_image


def set_background_image(path: str | None, config_path: Path | None = None) -> None:
    """Update and persist the custom background image path."""
    cfg = GlobalConfig.load(config_path)
    cfg.background_image = path
    cfg.save(config_path)


def get_active_project_path(config: GlobalConfig | None = None) -> Path | None:
    """Resolve the currently active project path based on config."""
    cfg = config or GlobalConfig.load()
    if not cfg.active_project:
        return None

    # Check if active_project is an absolute path or relative to workspace root
    candidate = Path(cfg.active_project).expanduser()
    if candidate.is_absolute() and candidate.is_dir():
        return candidate.resolve()

    for root_str in (cfg.io_root, cfg.workspace_root, cfg.work_root):
        r = Path(root_str).expanduser()
        direct = r / cfg.active_project
        if direct.is_dir():
            return direct.resolve()
        prefixed = r / f"DNA_{cfg.active_project}"
        if prefixed.is_dir():
            return prefixed.resolve()

    return None


def get_active_project_name(config: GlobalConfig | None = None) -> str | None:
    """Return the name of the currently active project, or None."""
    cfg = config or GlobalConfig.load()
    return cfg.active_project


def set_active_project_name(name: str | None, config_path: Path | None = None) -> None:
    """Update and persist the active project name."""
    cfg = GlobalConfig.load(config_path)
    cfg.active_project = name
    cfg.save(config_path)
