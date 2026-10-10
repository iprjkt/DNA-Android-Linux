"""ROM modifications: Remove oat, Make full ROM-RW, and ROM Decryption."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from dna_core.debloat import calculate_directory_size
from dna_core.detection import ImageType, detect_image_type
from dna_core.tools import run_tool


@dataclass
class RomRwResult:
    fstab_files_modified: list[Path]
    overlay_lines_removed: int
    init_scripts_removed: list[Path]
    unshared_ext4_images: list[Path]
    dry_run: bool


@dataclass
class RomDecryptResult:
    fstab_files_modified: list[Path]
    lines_modified: int
    dry_run: bool


def remove_oat_directories(target_root: Path | str, dry_run: bool = False) -> tuple[list[Path], int]:
    """Find and delete all 'oat' optimized bytecode directories in the unpacked tree."""
    root = Path(target_root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory '{root}' does not exist.")

    removed: list[Path] = []
    freed_bytes = 0

    for dirpath, dirnames, _ in os.walk(root):
        if "oat" in dirnames:
            oat_path = Path(dirpath) / "oat"
            size = calculate_directory_size(oat_path)
            freed_bytes += size
            removed.append(oat_path)

    if not dry_run:
        for p in removed:
            shutil.rmtree(p, ignore_errors=True)

    return removed, freed_bytes


def make_rom_rw(target_root: Path | str, dry_run: bool = False) -> RomRwResult:
    """Enable full read-write access to ROM by removing overlay mounts and unsharing ext4 blocks."""
    root = Path(target_root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory '{root}' does not exist.")

    modified_fstabs: list[Path] = []
    total_overlay_lines = 0
    removed_inits: list[Path] = []
    unshared_images: list[Path] = []

    # 1. Modify fstab files to remove 'overlay' mounts
    fstab_candidates = list(root.glob("**/etc/fstab*"))
    for fstab in fstab_candidates:
        if fstab.is_file() and not fstab.name.endswith(".bak"):
            try:
                lines = fstab.read_text(encoding="utf-8", errors="ignore").splitlines()
                new_lines = []
                lines_changed = 0
                for line in lines:
                    stripped = line.strip()
                    # Check if line contains overlay mount definition
                    if stripped and not stripped.startswith("#") and "overlay" in line:
                        lines_changed += 1
                        total_overlay_lines += 1
                    else:
                        new_lines.append(line)

                if lines_changed > 0:
                    modified_fstabs.append(fstab)
                    if not dry_run:
                        # Create backup
                        fstab.with_suffix(fstab.suffix + ".bak").write_text("\n".join(lines) + "\n", encoding="utf-8")
                        fstab.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except OSError:
                pass

    # 2. Check and delete init.miui.mi_ext.rc (MIUI overlay setup)
    init_candidates = list(root.glob("**/mi_ext/etc/init/init.miui.mi_ext.rc"))
    for init_file in init_candidates:
        if init_file.is_file():
            removed_inits.append(init_file)
            if not dry_run:
                init_file.unlink()

    # 3. Unshare ext4 blocks for any .img files in the directory
    for img in root.glob("**/*.img"):
        if img.is_file() and detect_image_type(img) == ImageType.EXT4:
            unshared_images.append(img)
            if not dry_run:
                try:
                    run_tool("e2fsck", ["-y", "-E", "unshare_blocks", str(img)], check=False)
                except Exception:
                    pass

    return RomRwResult(
        fstab_files_modified=modified_fstabs,
        overlay_lines_removed=total_overlay_lines,
        init_scripts_removed=removed_inits,
        unshared_ext4_images=unshared_images,
        dry_run=dry_run,
    )


def decrypt_rom(target_root: Path | str, dry_run: bool = False) -> RomDecryptResult:
    """Modify fstab files to convert forced fileencryption to fileencryptable for dirty flashing."""
    root = Path(target_root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory '{root}' does not exist.")

    modified_fstabs: list[Path] = []
    total_lines_changed = 0

    fstab_candidates = list(root.glob("**/etc/fstab*"))
    for fstab in fstab_candidates:
        if fstab.is_file() and not fstab.name.endswith(".bak"):
            try:
                content = fstab.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                new_lines = []
                fstab_changed = 0

                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and ("fileencryption" in line or "forceencrypt" in line):
                        # Replace fileencryption with fileencryptable
                        updated = re.sub(r"fileencryption=[^,\s]+", "fileencryptable", line)
                        updated = re.sub(r"fileencryption", "fileencryptable", updated)
                        updated = re.sub(r"forceencrypt=[^,\s]+", "encryptable", updated)
                        if updated != line:
                            fstab_changed += 1
                            total_lines_changed += 1
                            new_lines.append(updated)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)

                if fstab_changed > 0:
                    modified_fstabs.append(fstab)
                    if not dry_run:
                        fstab.with_suffix(fstab.suffix + ".bak").write_text(content, encoding="utf-8")
                        fstab.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except OSError:
                pass

    return RomDecryptResult(
        fstab_files_modified=modified_fstabs,
        lines_modified=total_lines_changed,
        dry_run=dry_run,
    )
