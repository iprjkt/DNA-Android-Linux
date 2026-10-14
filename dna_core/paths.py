"""Path management and workspace layout abstractions for DNA-Linux."""

from __future__ import annotations

import os
import re
from pathlib import Path


def get_default_io_root() -> Path:
    """Return default input/output root directory (/sdcard/DNA or fallback ~/DNA)."""
    env_io = (
        os.environ.get("DNA_IO_ROOT")
        or os.environ.get("DNA_SDCARD")
        or os.environ.get("DNA_DIR")
        or os.environ.get("DNA_HOME")
    )
    if env_io:
        return Path(env_io).expanduser().resolve()

    # Check Android /sdcard or /storage/emulated/0
    for cand in (Path("/sdcard/DNA"), Path("/storage/emulated/0/DNA")):
        try:
            if cand.parent.is_dir() and os.access(cand.parent, os.W_OK):
                return cand.resolve()
            if cand.is_dir() and os.access(cand, os.W_OK):
                return cand.resolve()
        except OSError:
            pass

    return (Path.home() / "DNA").resolve()


def get_default_work_root() -> Path:
    """Return default working directory (/data/DNA or fallback ~/DNA/work)."""
    env_work = (
        os.environ.get("DNA_WORK_ROOT")
        or os.environ.get("DNA_DATA")
        or os.environ.get("DNA_TMP")
    )
    if env_work:
        return Path(env_work).expanduser().resolve()

    try:
        cand = Path("/data/DNA")
        if cand.parent.is_dir() and os.access(cand.parent, os.W_OK):
            return cand.resolve()
        if cand.is_dir() and os.access(cand, os.W_OK):
            return cand.resolve()
    except OSError:
        pass

    # Fallback on Linux environments without /data write access
    io_root = get_default_io_root()
    return (io_root / "work").resolve()


def get_default_workspace_root() -> Path:
    """Return default workspace root directory (alias to IO root)."""
    return get_default_io_root()


def get_global_config_dir() -> Path:
    """Return global config directory (~/.config/dna-linux or $XDG_CONFIG_HOME/dna-linux)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return (Path(xdg_config) / "dna-linux").resolve()
    return (Path.home() / ".config" / "dna-linux").resolve()


def get_data_dir() -> Path:
    """Locate the bundled or installed data directory (presets, icons, placeholders)."""
    # 1. Environment override
    env_data = os.environ.get("DNA_DATA_DIR")
    if env_data:
        p = Path(env_data).expanduser().resolve()
        if p.is_dir():
            return p

    # 2. Local source tree or /usr/lib/dna-linux/data
    repo_data = Path(__file__).resolve().parent.parent / "data"
    if repo_data.is_dir():
        return repo_data

    # 3. System shared directories
    import sys

    for cand in (
        Path(sys.prefix) / "share" / "dna-linux" / "data",
        Path(sys.prefix) / "share" / "dna-linux",
        Path("/usr/local/share/dna-linux/data"),
        Path("/usr/local/share/dna-linux"),
        Path("/usr/share/dna-linux/data"),
        Path("/usr/share/dna-linux"),
        Path.home() / ".local" / "share" / "dna-linux",
    ):
        if cand.is_dir():
            return cand.resolve()

    return repo_data


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


class ProjectPaths:
    """Paths specific to an active DNA project workspace.

    Architecture mirrors DNA-Android MT Manager layout:
      - IO Directory (default /sdcard/DNA/DNA_<project>):
          Contains out/ and source archives/images/APKs at root.
      - Working Directory (default /data/DNA/DNA_<project>):
          Contains config/, logs/, plugins/, and unpacked partition directories
          (e.g. product/, system/) directly.
    """

    def __init__(
        self,
        work_dir: Path | str | None = None,
        io_dir: Path | str | None = None,
        project_dir: Path | str | None = None,
    ) -> None:
        target = project_dir or work_dir or io_dir
        if target is None:
            raise ValueError("At least one directory path must be provided to ProjectPaths.")

        target_path = Path(target).expanduser().resolve()

        if work_dir is not None and io_dir is not None:
            self._work_dir = Path(work_dir).expanduser().resolve()
            self._io_dir = Path(io_dir).expanduser().resolve()
        elif project_dir is not None and work_dir is None and io_dir is None:
            # Standalone or legacy single-path initialization
            name = target_path.name
            if name.startswith("DNA_"):
                cand_io = get_default_io_root() / name
                cand_work = get_default_work_root() / name
                if cand_io.is_dir() and cand_work.is_dir():
                    self._io_dir = cand_io
                    self._work_dir = cand_work
                else:
                    self._io_dir = target_path
                    self._work_dir = target_path
            else:
                self._io_dir = target_path
                self._work_dir = target_path
        else:
            w = Path(work_dir if work_dir is not None else target_path).expanduser().resolve()
            i = Path(io_dir if io_dir is not None else target_path).expanduser().resolve()
            self._work_dir = w
            self._io_dir = i

    @property
    def work_dir(self) -> Path:
        """Working directory holding extracted partitions and config (default /data/DNA/DNA_<project>)."""
        return self._work_dir

    @property
    def io_dir(self) -> Path:
        """Input/output directory holding out/ and ROM files (default /sdcard/DNA/DNA_<project>)."""
        return self._io_dir

    @property
    def project_dir(self) -> Path:
        """Primary project directory pointer (aliases io_dir)."""
        return self._io_dir

    @property
    def project_name(self) -> str:
        name = self._io_dir.name
        if name.startswith("DNA_"):
            return name[4:]
        if self._work_dir.name.startswith("DNA_"):
            return self._work_dir.name[4:]
        return name

    @property
    def rom_dir(self) -> Path:
        """Directory for ROM archives."""
        if (self._io_dir / "rom").is_dir():
            return self._io_dir / "rom"
        if self._work_dir == self._io_dir:
            return self._io_dir / "rom"
        return self._io_dir

    @property
    def images_dir(self) -> Path:
        """Directory for partition image files."""
        if (self._io_dir / "images").is_dir():
            return self._io_dir / "images"
        if self._work_dir == self._io_dir:
            return self._io_dir / "images"
        return self._io_dir

    @property
    def unpacked_dir(self) -> Path:
        """Directory for unpacked partition trees."""
        if (self._work_dir / "unpacked").is_dir():
            return self._work_dir / "unpacked"
        if self._work_dir == self._io_dir:
            return self._work_dir / "unpacked"
        return self._work_dir

    @property
    def config_dir(self) -> Path:
        """Directory storing SELinux file_contexts and fs_config files."""
        return self._work_dir / "config"

    @property
    def out_dir(self) -> Path:
        """Directory storing repacked partition images, super.img, and ROM zips."""
        return self._io_dir / "out"

    @property
    def plugins_dir(self) -> Path:
        return self._work_dir / "plugins"

    @property
    def logs_dir(self) -> Path:
        return self._work_dir / "logs"

    @property
    def project_file(self) -> Path:
        return self._work_dir / "project.toml"

    @property
    def images(self) -> Path:
        return self.images_dir

    @property
    def unpacked(self) -> Path:
        return self.unpacked_dir

    @property
    def out(self) -> Path:
        return self.out_dir

    @property
    def rom(self) -> Path:
        return self.rom_dir

    @property
    def config(self) -> Path:
        return self.config_dir

    def ensure_layout(self) -> None:
        """Create all project subdirectories if they do not exist."""
        dirs_to_create = [
            self._io_dir,
            self.out_dir,
            self._work_dir,
            self.config_dir,
            self.plugins_dir,
            self.logs_dir,
        ]
        if self._work_dir == self._io_dir:
            dirs_to_create.extend([
                self._io_dir / "rom",
                self._io_dir / "images",
                self._work_dir / "unpacked",
            ])
        for path in dirs_to_create:
            path.mkdir(parents=True, exist_ok=True)

    def is_safe_subpath(self, target: Path) -> bool:
        """Verify that target resides strictly within this project's io or work directory."""
        try:
            resolved_target = target.resolve()
            for base in (self._io_dir, self._work_dir):
                resolved_base = base.resolve()
                if resolved_base == resolved_target or resolved_base in resolved_target.parents:
                    return True
            return False
        except (OSError, RuntimeError):
            return False

    def validate_safe_subpath(self, target: Path) -> Path:
        """Raise PermissionError if target is outside this project's directories."""
        resolved = target.resolve()
        if not self.is_safe_subpath(resolved):
            raise PermissionError(
                f"Safety violation: Path '{resolved}' is outside project directories '{self._io_dir}' / '{self._work_dir}'."
            )
        return resolved

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProjectPaths):
            return False
        return self._io_dir == other._io_dir and self._work_dir == other._work_dir

    def __repr__(self) -> str:
        return f"ProjectPaths(work_dir={self._work_dir}, io_dir={self._io_dir})"

    @classmethod
    def from_name(
        cls,
        name: str,
        root_dir: Path | None = None,
        io_root: Path | None = None,
        work_root: Path | None = None,
    ) -> ProjectPaths:
        """Instantiate ProjectPaths from a project name and root directory."""
        clean_name = normalize_project_name(name)
        if root_dir is not None:
            root = Path(root_dir).expanduser().resolve()
            return cls(io_dir=root / f"DNA_{clean_name}", work_dir=root / f"DNA_{clean_name}")
        eff_io_root = (io_root or get_default_io_root()).resolve()
        eff_work_root = (work_root or get_default_work_root()).resolve()
        return cls(
            io_dir=eff_io_root / f"DNA_{clean_name}",
            work_dir=eff_work_root / f"DNA_{clean_name}",
        )

    @classmethod
    def from_path(cls, path: Path | str) -> ProjectPaths:
        """Instantiate ProjectPaths from an existing or explicit directory path."""
        p = Path(path).expanduser().resolve()
        name = p.name
        if name.startswith("DNA_"):
            io_root = get_default_io_root()
            work_root = get_default_work_root()
            cand_io = io_root / name
            cand_work = work_root / name
            if cand_io.is_dir() and cand_work.is_dir():
                return cls(work_dir=cand_work, io_dir=cand_io)
        return cls(project_dir=p)
