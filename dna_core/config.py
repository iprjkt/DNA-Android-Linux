"""User configuration manager for DNA-Linux."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dna_core.paths import get_default_workspace_root, get_global_config_dir


@dataclass
class GlobalConfig:
    """Global configuration settings for DNA-Linux."""

    workspace_root: str = field(default_factory=lambda: str(get_default_workspace_root()))
    active_project: str | None = None
    auto_confirm: bool = False
    verbose: bool = False
    background_image: str | None = None
    tool_overrides: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Path | None = None) -> GlobalConfig:
        """Load global config from file, or return defaults if file does not exist."""
        path = config_path or (get_global_config_dir() / "config.toml")
        if not path.is_file():
            return cls()

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            return cls(
                workspace_root=data.get("workspace_root", str(get_default_workspace_root())),
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

    ws_root = Path(cfg.workspace_root).expanduser()
    direct_match = ws_root / cfg.active_project
    if direct_match.is_dir():
        return direct_match.resolve()

    prefixed_match = ws_root / f"DNA_{cfg.active_project}"
    if prefixed_match.is_dir():
        return prefixed_match.resolve()

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

