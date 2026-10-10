"""Workspace and project management operations for DNA-Linux."""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dna_core.config import GlobalConfig, get_active_project_path
from dna_core.paths import ProjectPaths, get_default_workspace_root, normalize_project_name


@dataclass
class Project:
    """Represents an instantiated DNA-Linux project workspace."""

    paths: ProjectPaths
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.paths.project_name

    @property
    def directory(self) -> Path:
        return self.paths.project_dir

    def load_metadata(self) -> dict[str, Any]:
        """Read project.toml metadata."""
        if not self.paths.project_file.is_file():
            return {}
        try:
            with open(self.paths.project_file, "rb") as f:
                self.metadata = tomllib.load(f)
            return self.metadata
        except Exception:
            return {}

    def save_metadata(self) -> None:
        """Persist metadata to project.toml."""
        self.paths.project_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "# DNA-Linux Project Metadata",
            f'name = "{self.metadata.get("name", self.name)}"',
            f'created_at = "{self.metadata.get("created_at", datetime.now().isoformat())}"',
            f'updated_at = "{datetime.now().isoformat()}"',
            f'description = "{self.metadata.get("description", "")}"',
            f'source_rom = "{self.metadata.get("source_rom", "")}"',
            f'android_version = "{self.metadata.get("android_version", "")}"',
        ]
        content = "\n".join(lines) + "\n"
        with open(self.paths.project_file, "w", encoding="utf-8") as f:
            f.write(content)


def create_project(
    name: str,
    root_dir: Path | None = None,
    description: str = "",
    set_active: bool = True,
    auto_rename_on_conflict: bool = False,
) -> Project:
    """Create a new project workspace directory with full layout scaffold."""
    clean_name = normalize_project_name(name)
    workspace_root = (root_dir or get_default_workspace_root()).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    target_dir = workspace_root / f"DNA_{clean_name}"
    if target_dir.exists():
        if auto_rename_on_conflict:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            clean_name = f"{clean_name}_{timestamp}"
            target_dir = workspace_root / f"DNA_{clean_name}"
        else:
            raise FileExistsError(
                f"Project workspace '{target_dir}' already exists. Use a different name or remove it first."
            )

    paths = ProjectPaths(project_dir=target_dir)
    paths.ensure_layout()

    project = Project(
        paths=paths,
        metadata={
            "name": clean_name,
            "created_at": datetime.now().isoformat(),
            "description": description,
        },
    )
    project.save_metadata()

    if set_active:
        cfg = GlobalConfig.load()
        cfg.active_project = clean_name
        cfg.save()

    return project


def resolve_project(name_or_path: str, root_dir: Path | None = None) -> Project:
    """Resolve a project by name or explicit path."""
    cand_path = Path(name_or_path).expanduser()
    if cand_path.is_dir():
        proj = Project(paths=ProjectPaths.from_path(cand_path))
        proj.load_metadata()
        return proj

    clean_name = normalize_project_name(name_or_path)
    workspace_root = (root_dir or get_default_workspace_root()).resolve()

    target_dir = workspace_root / f"DNA_{clean_name}"
    if not target_dir.is_dir():
        # Check without DNA_ prefix
        target_dir = workspace_root / clean_name
        if not target_dir.is_dir():
            raise FileNotFoundError(
                f"Project '{name_or_path}' not found in workspace root '{workspace_root}'."
            )

    proj = Project(paths=ProjectPaths(project_dir=target_dir))
    proj.load_metadata()
    return proj


def select_project(name_or_path: str, root_dir: Path | None = None) -> Project:
    """Select a project and set it as active in the global configuration."""
    project = resolve_project(name_or_path, root_dir)
    cfg = GlobalConfig.load()
    cfg.active_project = project.name
    cfg.save()
    return project


def delete_project(name_or_path: str, root_dir: Path | None = None) -> Path:
    """Delete a project workspace directory and clean up config if active."""
    project = resolve_project(name_or_path, root_dir)
    target_dir = project.directory

    cfg = GlobalConfig.load()
    if cfg.active_project in (project.name, f"DNA_{project.name}", str(target_dir)):
        cfg.active_project = None
        cfg.save()

    shutil.rmtree(target_dir)
    return target_dir


def list_projects(root_dir: Path | None = None) -> list[tuple[Project, bool]]:
    """List all project workspaces in root_dir, with an active boolean flag."""
    workspace_root = (root_dir or get_default_workspace_root()).resolve()
    if not workspace_root.is_dir():
        return []

    active_path = get_active_project_path()
    projects: list[tuple[Project, bool]] = []

    for entry in sorted(workspace_root.iterdir()):
        if entry.is_dir() and (entry.name.startswith("DNA_") or (entry / "project.toml").is_file()):
            proj = Project(paths=ProjectPaths(project_dir=entry))
            proj.load_metadata()
            is_active = (active_path is not None and active_path.resolve() == entry.resolve())
            projects.append((proj, is_active))

    return projects


def get_current_project(project_override: str | None = None) -> Project:
    """Get the currently active project, or raise ValueError if none is active."""
    if project_override:
        return resolve_project(project_override)

    active_path = get_active_project_path()
    if not active_path or not active_path.is_dir():
        raise ValueError(
            "No active project selected. Run 'dna project select <name>' or 'dna project create <name>' first."
        )

    proj = Project(paths=ProjectPaths(project_dir=active_path))
    proj.load_metadata()
    return proj


def get_active_project(project_override: str | None = None) -> Project | None:
    """Get the currently active project, or None if none is active."""
    try:
        return get_current_project(project_override)
    except (ValueError, FileNotFoundError):
        return None

