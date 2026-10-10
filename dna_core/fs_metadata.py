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


def scan_directory_fs_metadata(
    root_dir: Path | str,
    mount_point: str = "system",
) -> tuple[list[FsConfigEntry], list[tuple[str, str]]]:
    """Scan an extracted directory tree and generate fs_config and file_contexts entries."""
    root = Path(root_dir).resolve()
    clean_mount = mount_point.strip("/")

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
