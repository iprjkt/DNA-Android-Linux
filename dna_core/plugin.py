"""Plugin architecture and execution sandbox for DNA-Linux.

Provides:
- Manifest specification via plugin.toml
- Safe archive validation and extraction (Zip-Slip prevention)
- Project-level and global plugin discovery
- Sandboxed execution with workspace containment and environment injection
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dna_core.paths import ProjectPaths, get_global_config_dir


@dataclass(frozen=True)
class PluginMetadata:
    """Plugin manifest information and directory location."""

    id: str
    name: str
    version: str
    author: str
    description: str
    entrypoint: str
    min_dna_version: str
    path: Path
    scope: str  # "project" or "global"


def get_global_plugins_dir() -> Path:
    """Return the global plugins directory (~/.config/dna-linux/plugins)."""
    d = get_global_config_dir() / "plugins"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_plugin_manifest(plugin_dir: Path | str, scope: str = "project") -> PluginMetadata:
    """Load and validate plugin.toml in a given directory."""
    p_dir = Path(plugin_dir)
    toml_path = p_dir / "plugin.toml"
    if not toml_path.is_file():
        raise FileNotFoundError(f"Missing plugin.toml in {p_dir}")

    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    meta = data.get("plugin", {})
    plugin_id = meta.get("id")
    name = meta.get("name")
    version = meta.get("version", "1.0.0")
    author = meta.get("author", "Unknown")
    description = meta.get("description", "")
    entrypoint = meta.get("entrypoint", "run.sh")
    min_dna_version = meta.get("min_dna_version", "1.0.0")

    if not plugin_id or not re_valid_id(plugin_id):
        raise ValueError(
            f"Invalid plugin id '{plugin_id}'. Must be alphanumeric with dashes or underscores."
        )
    if not name:
        raise ValueError(f"Plugin in {p_dir} must specify a 'name'.")

    entrypoint_path = p_dir / entrypoint
    if not entrypoint_path.is_file():
        raise FileNotFoundError(
            f"Plugin entrypoint '{entrypoint}' not found in {p_dir}"
        )

    return PluginMetadata(
        id=plugin_id,
        name=name,
        version=str(version),
        author=author,
        description=description,
        entrypoint=entrypoint,
        min_dna_version=str(min_dna_version),
        path=p_dir.resolve(),
        scope=scope,
    )


def re_valid_id(raw_id: str) -> bool:
    """Validate plugin ID syntax (lowercase alphanumeric with dashes/underscores)."""
    import re

    return bool(re.match(r"^[a-zA-Z0-9_\-]+$", raw_id))


def list_plugins(
    project_plugins_dir: Optional[Path | str] = None,
    include_global: bool = True,
) -> List[PluginMetadata]:
    """Discover all installed plugins from project and global scopes."""
    plugins: Dict[str, PluginMetadata] = {}

    # 1. Project plugins (higher priority)
    if project_plugins_dir is not None:
        proj_dir = Path(project_plugins_dir)
        if proj_dir.is_dir():
            for item in sorted(proj_dir.iterdir()):
                if item.is_dir() and (item / "plugin.toml").is_file():
                    try:
                        p = load_plugin_manifest(item, scope="project")
                        plugins[p.id] = p
                    except Exception:
                        pass

    # 2. Global plugins
    if include_global:
        glob_dir = get_global_plugins_dir()
        if glob_dir.is_dir():
            for item in sorted(glob_dir.iterdir()):
                if item.is_dir() and (item / "plugin.toml").is_file():
                    try:
                        p = load_plugin_manifest(item, scope="global")
                        if p.id not in plugins:
                            plugins[p.id] = p
                    except Exception:
                        pass

    return sorted(plugins.values(), key=lambda p: p.id)


def get_plugin(
    plugin_id: str,
    project_plugins_dir: Optional[Path | str] = None,
) -> PluginMetadata:
    """Retrieve an installed plugin by ID."""
    all_plugins = list_plugins(project_plugins_dir=project_plugins_dir, include_global=True)
    for p in all_plugins:
        if p.id == plugin_id:
            return p
    raise KeyError(f"Plugin '{plugin_id}' not found.")


def import_plugin(
    archive_path: Path | str,
    target_dir: Path | str,
    scope: str = "project",
    overwrite: bool = False,
) -> PluginMetadata:
    """Safely import and extract a plugin from a ZIP archive or directory.

    Guarantees Zip-Slip safety and validates the manifest and entrypoint.
    """
    src = Path(archive_path)
    dst_root = Path(target_dir)
    dst_root.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Source plugin archive not found: {src}")

    with tempfile.TemporaryDirectory() as td:
        temp_extract = Path(td) / "extracted"
        temp_extract.mkdir()

        if src.is_dir():
            # Source is already an unzipped directory
            shutil.copytree(src, temp_extract, dirs_exist_ok=True)
        elif zipfile.is_zipfile(src):
            with zipfile.ZipFile(src, "r") as zf:
                # Zip-Slip verification
                for member in zf.infolist():
                    target_member_path = (temp_extract / member.filename).resolve()
                    if not target_member_path.is_relative_to(temp_extract.resolve()):
                        raise PermissionError(
                            f"Malicious archive member '{member.filename}' escapes target extraction root."
                        )
                zf.extractall(temp_extract)
        else:
            raise ValueError(f"File {src} is neither a directory nor a valid ZIP archive.")

        # Locate plugin.toml (either in root of archive or nested 1 level)
        manifest_path = temp_extract / "plugin.toml"
        source_plugin_dir = temp_extract

        if not manifest_path.is_file():
            # Check single subfolder
            subdirs = [d for d in temp_extract.iterdir() if d.is_dir()]
            if len(subdirs) == 1 and (subdirs[0] / "plugin.toml").is_file():
                source_plugin_dir = subdirs[0]
                manifest_path = source_plugin_dir / "plugin.toml"
            else:
                # Search anywhere
                found = list(temp_extract.rglob("plugin.toml"))
                if found:
                    manifest_path = found[0]
                    source_plugin_dir = manifest_path.parent
                else:
                    raise FileNotFoundError("Archive does not contain a 'plugin.toml' manifest.")

        # Validate manifest
        metadata = load_plugin_manifest(source_plugin_dir, scope=scope)

        # Final destination
        dest_plugin_dir = dst_root / metadata.id
        if dest_plugin_dir.exists():
            if not overwrite:
                raise FileExistsError(
                    f"Plugin '{metadata.id}' is already installed at {dest_plugin_dir}. Use --overwrite to replace."
                )
            shutil.rmtree(dest_plugin_dir)

        shutil.copytree(source_plugin_dir, dest_plugin_dir)

        # Make entrypoint executable
        entry_file = dest_plugin_dir / metadata.entrypoint
        if entry_file.is_file():
            current_mode = entry_file.stat().st_mode
            entry_file.chmod(current_mode | 0o755)

        return load_plugin_manifest(dest_plugin_dir, scope=scope)


def run_plugin(
    plugin: PluginMetadata,
    project_paths: ProjectPaths,
    args: Optional[List[str]] = None,
    env_overrides: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a plugin entrypoint in a sandboxed workspace environment."""
    project_paths.ensure_layout()
    entry_file = plugin.path / plugin.entrypoint
    if not entry_file.is_file():
        raise FileNotFoundError(f"Plugin entrypoint not found: {entry_file}")

    # Build sandbox environment
    env = os.environ.copy()
    env["DNA_PROJECT"] = str(project_paths.project_dir)
    env["DNA_PROJECT_NAME"] = project_paths.project_name
    env["DNA_ROM"] = str(project_paths.rom_dir)
    env["DNA_IMAGES"] = str(project_paths.images_dir)
    env["DNA_UNPACKED"] = str(project_paths.unpacked_dir)
    env["DNA_CONFIG"] = str(project_paths.config_dir)
    env["DNA_OUT"] = str(project_paths.out_dir)
    env["DNA_LOGS"] = str(project_paths.logs_dir)
    env["DNA_PLUGIN_DIR"] = str(plugin.path)
    env["DNA_PLUGIN_ID"] = plugin.id

    # Append DNA package root to PYTHONPATH so plugins can import dna_core if desired
    repo_root = str(Path(__file__).resolve().parent.parent)
    existing_py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{repo_root}:{existing_py_path}" if existing_py_path else repo_root

    if env_overrides:
        env.update(env_overrides)

    # Determine command invocation
    cli_args = args or []
    if entry_file.suffix == ".py":
        cmd = [sys.executable, str(entry_file)] + cli_args
    elif entry_file.suffix == ".sh":
        cmd = ["/bin/bash", str(entry_file)] + cli_args
    else:
        cmd = [str(entry_file)] + cli_args

    timestamp = int(time.time())
    log_file = project_paths.logs_dir / f"plugin_{plugin.id}_{timestamp}.log"

    res = subprocess.run(
        cmd,
        cwd=str(project_paths.project_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    # Write log file
    try:
        log_content = (
            f"=== Plugin Execution: {plugin.id} ({plugin.name} v{plugin.version}) ===\n"
            f"Timestamp: {timestamp}\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit Code: {res.returncode}\n\n"
            f"--- STDOUT ---\n{res.stdout}\n\n"
            f"--- STDERR ---\n{res.stderr}\n"
        )
        log_file.write_text(log_content, encoding="utf-8")
    except Exception:
        pass

    return res


def delete_plugin(plugin: PluginMetadata) -> bool:
    """Delete an installed plugin."""
    if plugin.path.is_dir():
        shutil.rmtree(plugin.path)
        return True
    return False
