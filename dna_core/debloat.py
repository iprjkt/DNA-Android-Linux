"""Data-driven ROM debloating engine for MIUI and HyperOS."""

from __future__ import annotations

import fnmatch
import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DebloatPackage:
    name: str
    description: str
    patterns: list[str]


@dataclass
class DebloatPreset:
    name: str
    title: str
    description: str
    packages: list[DebloatPackage]


@dataclass
class DebloatResult:
    preset_name: str
    removed_directories: list[Path]
    freed_bytes: int
    packages_affected: list[str]
    dry_run: bool


def get_default_debloat_dir() -> Path:
    """Return the repository's data/debloat directory."""
    return Path(__file__).resolve().parent.parent / "data" / "debloat"


def load_debloat_preset(preset_ref: str | Path) -> DebloatPreset:
    """Load debloat preset from preset name ('global', 'china') or an explicit TOML file path."""
    cand = Path(preset_ref).expanduser()
    if cand.is_file():
        toml_path = cand.resolve()
    else:
        # Check in data/debloat/<preset_ref>.toml
        debloat_dir = get_default_debloat_dir()
        toml_path = debloat_dir / f"{preset_ref.lower()}.toml"
        if not toml_path.is_file():
            # Check with .toml suffix directly
            toml_path = debloat_dir / preset_ref
            if not toml_path.is_file():
                raise FileNotFoundError(
                    f"Debloat preset '{preset_ref}' not found. Available defaults: 'global', 'china'."
                )

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    meta = data.get("metadata", {})
    raw_pkgs = data.get("packages", [])

    packages: list[DebloatPackage] = []
    for pkg in raw_pkgs:
        packages.append(
            DebloatPackage(
                name=pkg.get("name", "Unknown"),
                description=pkg.get("description", ""),
                patterns=pkg.get("patterns", []),
            )
        )

    return DebloatPreset(
        name=meta.get("name", toml_path.stem),
        title=meta.get("title", toml_path.stem),
        description=meta.get("description", ""),
        packages=packages,
    )


def calculate_directory_size(path: Path) -> int:
    """Calculate the total size in bytes of a directory tree."""
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                if not fp.is_symlink():
                    total += fp.stat().st_size
            except OSError:
                pass
    return total


BANNER_DEBLOAT = """  ___       _     _             _   _            
 |   \\ ___ | |__ | | ___  __ _ | |_(_) _ _   __ _ 
 | |) / -_)| '_ \\| |/ _ \\/ _` ||  _| || ' \\ / _` |
 |___/\\___||_.__/|_|\\___/\\__,_| \\__|_||_||_|\\__, |
                                            |___/ """


def run_debloat(
    target_root: Path | str,
    preset: DebloatPreset,
    dry_run: bool = False,
) -> DebloatResult:
    """Scan and safely debloat packages matching preset patterns in target_root."""
    print(BANNER_DEBLOAT + "\n")
    print("Removing bloatware please wait...\n")

    root = Path(target_root).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir

    if not eff_root.is_dir():
        print(f"find: '{base_dir}': No such file or directory\n")
        print("[✓] Debloating complete\n")
        return DebloatResult(
            preset_name=preset.name,
            removed_directories=[],
            freed_bytes=0,
            packages_affected=[],
            dry_run=dry_run,
        )

    # Check partitions under eff_root / base_dir
    for p_name in ("system", "product"):
        has_part = (
            (eff_root / p_name).is_dir()
            or (eff_root / f"{p_name}_a").is_dir()
            or eff_root.name.startswith(p_name)
            or (base_dir / p_name).is_dir()
            or (base_dir / f"{p_name}_a").is_dir()
        )
        if not has_part:
            print(f"find: '{base_dir / p_name}': No such file or directory")

    removed: list[Path] = []
    affected_packages: set[str] = set()
    total_freed = 0

    # Scan directory tree
    for pkg in preset.packages:
        pkg_matched = False
        for pattern in pkg.patterns:
            # Match pattern relative to eff_root
            for match_path in eff_root.glob(pattern):
                if match_path.is_dir() and match_path not in removed:
                    size = calculate_directory_size(match_path)
                    total_freed += size
                    removed.append(match_path)
                    pkg_matched = True
                    try:
                        rel = match_path.relative_to(eff_root)
                    except ValueError:
                        rel = match_path.name
                    print(f"Removing: ./{rel} (Package: {pkg.name})")

        if pkg_matched:
            affected_packages.add(pkg.name)

    if not dry_run:
        for p in removed:
            shutil.rmtree(p, ignore_errors=True)

    print("[✓] Debloating complete\n")

    return DebloatResult(
        preset_name=preset.name,
        removed_directories=removed,
        freed_bytes=total_freed,
        packages_affected=sorted(affected_packages),
        dry_run=dry_run,
    )


def debloat_rom(
    target_dir: Path | str,
    profile: str = "global",
    dry_run: bool = False,
) -> DebloatResult:
    """Load specified preset and run debloating on target directory."""
    preset = load_debloat_preset(profile)
    return run_debloat(target_dir, preset, dry_run=dry_run)

