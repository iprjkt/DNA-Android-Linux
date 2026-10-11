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
from dna_core.paths import (
    ProjectPaths,
    get_default_io_root,
    get_default_work_root,
    get_default_workspace_root,
    normalize_project_name,
)


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
        """Read project.toml metadata from work_dir or io_dir."""
        target_file = self.paths.project_file
        if not target_file.is_file():
            alt_file = self.paths.io_dir / "project.toml"
            if alt_file.is_file():
                target_file = alt_file
            else:
                return {}

        try:
            with open(target_file, "rb") as f:
                self.metadata = tomllib.load(f)
            return self.metadata
        except Exception:
            return {}

    def save_metadata(self) -> None:
        """Persist metadata to project.toml in work_dir and io_dir."""
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

        target_dirs = [self.paths.work_dir]
        if self.paths.io_dir.resolve() != self.paths.work_dir.resolve():
            target_dirs.append(self.paths.io_dir)

        for d in target_dirs:
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "project.toml", "w", encoding="utf-8") as f:
                f.write(content)


def create_project(
    name: str,
    root_dir: Path | None = None,
    io_root: Path | None = None,
    work_root: Path | None = None,
    description: str = "",
    set_active: bool = True,
    auto_rename_on_conflict: bool = False,
) -> Project:
    """Create a new project workspace directory with full layout scaffold."""
    clean_name = normalize_project_name(name)
    cfg = GlobalConfig.load()

    if root_dir is not None:
        eff_io_root = Path(root_dir).resolve()
        eff_work_root = Path(root_dir).resolve()
    else:
        eff_io_root = (io_root or Path(cfg.io_root)).resolve()
        eff_work_root = (work_root or Path(cfg.work_root)).resolve()

    eff_io_root.mkdir(parents=True, exist_ok=True)
    eff_work_root.mkdir(parents=True, exist_ok=True)

    target_io = eff_io_root / f"DNA_{clean_name}"
    target_work = eff_work_root / f"DNA_{clean_name}"

    if target_io.exists() or target_work.exists():
        if auto_rename_on_conflict:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            clean_name = f"{clean_name}_{timestamp}"
            target_io = eff_io_root / f"DNA_{clean_name}"
            target_work = eff_work_root / f"DNA_{clean_name}"
        else:
            conflict_path = target_io if target_io.exists() else target_work
            raise FileExistsError(
                f"Project workspace '{conflict_path}' already exists. Use a different name or remove it first."
            )

    paths = ProjectPaths(work_dir=target_work, io_dir=target_io)
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
        cfg.active_project = clean_name
        cfg.save()

    return project


def resolve_project(
    name_or_path: str,
    root_dir: Path | None = None,
    io_root: Path | None = None,
    work_root: Path | None = None,
) -> Project:
    """Resolve a project by name or explicit path."""
    cand_path = Path(name_or_path).expanduser()
    if cand_path.is_dir():
        proj = Project(paths=ProjectPaths.from_path(cand_path))
        proj.load_metadata()
        return proj

    clean_name = normalize_project_name(name_or_path)

    if root_dir is not None:
        ws_root = Path(root_dir).resolve()
        target_dir = ws_root / f"DNA_{clean_name}"
        if not target_dir.is_dir():
            target_dir = ws_root / clean_name
            if not target_dir.is_dir():
                raise FileNotFoundError(
                    f"Project '{name_or_path}' not found in workspace root '{ws_root}'."
                )
        proj = Project(paths=ProjectPaths(target_dir))
        proj.load_metadata()
        return proj

    cfg = GlobalConfig.load()
    eff_io = (io_root or Path(cfg.io_root)).resolve()
    eff_work = (work_root or Path(cfg.work_root)).resolve()

    cand_io = eff_io / f"DNA_{clean_name}"
    if not cand_io.is_dir():
        cand_io = eff_io / clean_name

    cand_work = eff_work / f"DNA_{clean_name}"
    if not cand_work.is_dir():
        cand_work = eff_work / clean_name

    if cand_io.is_dir() or cand_work.is_dir():
        real_io = cand_io if cand_io.is_dir() else (eff_io / f"DNA_{clean_name}")
        real_work = cand_work if cand_work.is_dir() else (eff_work / f"DNA_{clean_name}")
        proj = Project(paths=ProjectPaths(work_dir=real_work, io_dir=real_io))
        proj.load_metadata()
        return proj

    raise FileNotFoundError(
        f"Project '{name_or_path}' not found in workspace roots '{eff_io}' / '{eff_work}'."
    )


def select_project(name_or_path: str, root_dir: Path | None = None) -> Project:
    """Select a project and set it as active in the global configuration."""
    project = resolve_project(name_or_path, root_dir)
    cfg = GlobalConfig.load()
    cfg.active_project = project.name
    cfg.save()
    return project


def delete_project(
    name_or_path: str,
    root_dir: Path | None = None,
    io_root: Path | None = None,
    work_root: Path | None = None,
) -> Path:
    """Delete a project workspace directory and clean up config if active."""
    project = resolve_project(name_or_path, root_dir, io_root, work_root)
    io_dir = project.paths.io_dir
    work_dir = project.paths.work_dir

    cfg = GlobalConfig.load()
    if cfg.active_project in (project.name, f"DNA_{project.name}", str(io_dir), str(work_dir)):
        cfg.active_project = None
        cfg.save()

    if io_dir.exists():
        shutil.rmtree(io_dir)
    if work_dir.exists() and work_dir.resolve() != io_dir.resolve():
        shutil.rmtree(work_dir)
    return io_dir


def list_projects(
    root_dir: Path | None = None,
    io_root: Path | None = None,
    work_root: Path | None = None,
) -> list[tuple[Project, bool]]:
    """List all project workspaces in root directories, with an active boolean flag."""
    if root_dir is not None:
        workspace_root = Path(root_dir).resolve()
        if not workspace_root.is_dir():
            return []
        active_path = get_active_project_path()
        projects: list[tuple[Project, bool]] = []
        for entry in sorted(workspace_root.iterdir()):
            if entry.is_dir() and (entry.name.startswith("DNA_") or (entry / "project.toml").is_file()):
                proj = Project(paths=ProjectPaths(entry))
                proj.load_metadata()
                is_active = (active_path is not None and active_path.resolve() == entry.resolve())
                projects.append((proj, is_active))
        return projects

    cfg = GlobalConfig.load()
    eff_io = (io_root or Path(cfg.io_root)).resolve()
    eff_work = (work_root or Path(cfg.work_root)).resolve()

    active_name = cfg.active_project
    active_path = get_active_project_path(cfg)
    seen_names: set[str] = set()
    projects: list[tuple[Project, bool]] = []

    for root in (eff_io, eff_work):
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry.name.startswith("DNA_") or (entry / "project.toml").is_file()):
                clean = normalize_project_name(entry.name) if entry.name.startswith("DNA_") else entry.name
                if clean in seen_names:
                    continue
                seen_names.add(clean)
                try:
                    proj = resolve_project(clean, io_root=eff_io, work_root=eff_work)
                    is_active = (
                        clean == active_name
                        or (
                            active_path is not None
                            and active_path.resolve() in (proj.paths.io_dir.resolve(), proj.paths.work_dir.resolve())
                        )
                    )
                    projects.append((proj, is_active))
                except Exception:
                    pass

    return projects


def get_current_project(project_override: str | None = None) -> Project:
    """Get the currently active project, or raise ValueError if none is active."""
    if project_override:
        return resolve_project(project_override)

    cfg = GlobalConfig.load()
    if not cfg.active_project:
        raise ValueError(
            "No active project selected. Run 'dna project select <name>' or 'dna project create <name>' first."
        )

    return resolve_project(cfg.active_project)


def get_active_project(project_override: str | None = None) -> Project | None:
    """Get the currently active project, or None if none is active."""
    try:
        return get_current_project(project_override)
    except (ValueError, FileNotFoundError):
        return None
