"""Filesystem metadata preservation: SELinux file_contexts and fs_config."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FsConfigEntry:
    path: str
    uid: int
    gid: int
    mode: str
    capabilities: str | None = None

    def serialize(self) -> str:
        base = f"{self.path} {self.uid} {self.gid} {self.mode}"
        if self.capabilities:
            return f"{base} capabilities={self.capabilities}"
        return base


try:
    from dna_core import dna_core_cpp
    _HAVE_CPP = True
except ImportError:
    _HAVE_CPP = False


def scan_directory_fs_metadata(
    root_dir: Path | str,
    mount_point: str = "system",
) -> tuple[list[FsConfigEntry], list[tuple[str, str]]]:
    """Scan an extracted directory tree and generate fs_config and file_contexts entries."""
    root = Path(root_dir).resolve()
    clean_mount = mount_point.strip("/")

    if _HAVE_CPP:
        try:
            cpp_res = dna_core_cpp.scan_directory_fs_metadata(str(root), clean_mount)
            fs_list = [
                FsConfigEntry(path=e.path, uid=e.uid, gid=e.gid, mode=e.mode, capabilities=e.capabilities or None)
                for e in cpp_res.fs_entries
            ]
            return fs_list, cpp_res.fc_entries
        except Exception:
            pass

    fs_entries: list[FsConfigEntry] = []
    fc_entries: list[tuple[str, str]] = []

    # Root filesystem entries for e2fsdroid
    fs_entries.append(FsConfigEntry(path="/", uid=0, gid=0, mode="755"))
    if clean_mount:
        fs_entries.append(FsConfigEntry(path=clean_mount, uid=0, gid=0, mode="755"))
    fc_entries.append((f"/{clean_mount}(/.*)?", "u:object_r:system_file:s0"))

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        prefix = f"{clean_mount}/{rel_dir}" if str(rel_dir) != "." else clean_mount

        # Entries for directories
        for d in sorted(dirnames):
            d_path = Path(dirpath) / d
            d_rel = f"{prefix}/{d}" if prefix else d
            try:
                st = os.lstat(d_path)
                mode_octal = oct(st.st_mode & 0o7777)[2:]
                fs_entries.append(
                    FsConfigEntry(path=d_rel, uid=st.st_uid, gid=st.st_gid, mode=mode_octal)
                )
            except OSError:
                fs_entries.append(FsConfigEntry(path=d_rel, uid=0, gid=0, mode="755"))

            # Check SELinux xattr if available
            try:
                selinux_val = os.getxattr(d_path, "security.selinux").decode("utf-8", errors="ignore").strip("\x00")
                if selinux_val:
                    fc_entries.append((f"/{d_rel}", selinux_val))
            except (OSError, AttributeError):
                pass

        # Entries for files
        for f in sorted(filenames):
            f_path = Path(dirpath) / f
            f_rel = f"{prefix}/{f}" if prefix else f
            try:
                st = os.lstat(f_path)
                mode_octal = oct(st.st_mode & 0o7777)[2:]
                fs_entries.append(
                    FsConfigEntry(path=f_rel, uid=st.st_uid, gid=st.st_gid, mode=mode_octal)
                )
            except OSError:
                fs_entries.append(FsConfigEntry(path=f_rel, uid=0, gid=0, mode="644"))

            # Check SELinux xattr if available
            try:
                selinux_val = os.getxattr(f_path, "security.selinux").decode("utf-8", errors="ignore").strip("\x00")
                if selinux_val:
                    fc_entries.append((f"/{f_rel}", selinux_val))
            except (OSError, AttributeError):
                pass

    return fs_entries, fc_entries


def write_fs_config_file(entries: list[FsConfigEntry], target_file: Path | str) -> Path:
    """Serialize fs_config entries to disk."""
    dst = Path(target_file).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.serialize() + "\n")
    return dst


def write_file_contexts_file(entries: list[tuple[str, str]], target_file: Path | str) -> Path:
    """Serialize file_contexts entries to disk."""
    dst = Path(target_file).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        for path_pattern, label in entries:
            f.write(f"{path_pattern} {label}\n")
    return dst


def sync_fs_config_file(root_dir: Path | str, mount_point: str, fs_file: Path | str) -> Path:
    """Ensure canned fs_config covers all files currently in root_dir tree, fixing corrupted paths."""
    target = Path(fs_file).resolve()
    if not target.is_file():
        entries, _ = scan_directory_fs_metadata(root_dir, mount_point)
        return write_fs_config_file(entries, target)

    existing_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    existing_paths: set[str] = set()
    cleaned_lines: list[str] = []
    has_corruptions = False

    for line in existing_lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        path_str = parts[0]
        if ".." in path_str:
            has_corruptions = True
            continue
        existing_paths.add(path_str)
        cleaned_lines.append(s)

    # Scan current filesystem tree to find any missing entries
    scanned_entries, _ = scan_directory_fs_metadata(root_dir, mount_point)
    added_count = 0
    for entry in scanned_entries:
        if entry.path not in existing_paths:
            cleaned_lines.append(entry.serialize())
            existing_paths.add(entry.path)
            added_count += 1

    if has_corruptions or added_count > 0:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")
        if added_count > 0:
            print(f"> Synchronized canned fs_config: added {added_count} missing entries to {target.name}")

    return target


def sync_file_contexts_file(mount_point: str, fc_file: Path | str) -> Path:
    """Ensure canned file_contexts has no corrupted paths and contains root partition fallback pattern."""
    target = Path(fc_file).resolve()
    if not target.is_file():
        return target

    clean_mount = mount_point.strip("/")
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    cleaned_lines = []
    has_corruptions = False
    has_root_fallback = False
    root_pattern = f"/{clean_mount}(/.*)?"

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if not parts:
            continue
        if ".." in parts[0]:
            has_corruptions = True
            continue
        if parts[0] == root_pattern:
            has_root_fallback = True
        cleaned_lines.append(s)

    if not has_root_fallback and clean_mount:
        cleaned_lines.insert(0, f"{root_pattern} u:object_r:system_file:s0")
        has_corruptions = True

    if has_corruptions:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(cleaned_lines) + "\n", encoding="utf-8")

    return target
