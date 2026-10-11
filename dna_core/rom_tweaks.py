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


BANNER_OAT = """  ___                                ___    _ _____ 
 | _ \\___ _ __  _____ _____ ___     / _ \\  /_\\_   _|
 |   / -_) '  \\/ _ \\ V / -_) -_)   | (_) |/ _ \\| |  
 |_|_\\___|_|_|_\\___/\\_/\\___|___|    \\___//_/ \\_\\_|  """

BANNER_ROM_RW = """  __  __      _         ___  ___  __  __     _____      __
 |  \\/  |__ _| |_____  | _ \\/ _ \\|  \\/  |___ | _ \\ \\    / /
 | |\\/| / _` | / / -_) |   / (_) | |\\/| |___||   /\\ \\/\\/ / 
 |_|  |_\\__,_|_\\_\\___| |_|_\\\\___/|_|  |_|    |_|_\\ \\_/\\_/  """

BANNER_DECRYPT = """  ___                          _      ___  ___  __  __ 
 |   \\ ___  __ _ _ _  _ _  ___| |_   | _ \\/ _ \\|  \\/  |
 | |) / -_)/ _| '_| || | '_ \\  _|    |   / (_) | |\\/| |
 |___/\\___|\\__|_|  \\_, | .__/\\__|    |_|_\\\\___/|_|  |_|
                   |__/|_|                             """


def remove_oat_directories(target_root: Path | str, dry_run: bool = False) -> tuple[list[Path], int]:
    """Find and delete all 'oat' optimized bytecode directories in the unpacked tree."""
    print(BANNER_OAT + "\n")
    print("Searching for oat directories...\n")

    root = Path(target_root).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    if not eff_root.is_dir():
        print(f"find: '{base_dir}': No such file or directory\n")
        print(f"No oat directories found in: {base_dir}\n")
        return [], 0

    removed: list[Path] = []
    freed_bytes = 0

    for dirpath, dirnames, _ in os.walk(eff_root):
        if "oat" in dirnames:
            oat_path = Path(dirpath) / "oat"
            size = calculate_directory_size(oat_path)
            freed_bytes += size
            removed.append(oat_path)
            sz_mb = size / (1024 * 1024)
            print(f"Removing: {oat_path.relative_to(eff_root)} ({sz_mb:.1f} MB)")

    if not dry_run:
        for p in removed:
            shutil.rmtree(p, ignore_errors=True)

    if removed:
        total_mb = freed_bytes / (1024 * 1024)
        print(f"[✓] Removed {len(removed)} oat directories ({total_mb:.1f} MB freed)\n")
    else:
        print(f"No oat directories found in: {eff_root}\n")

    return removed, freed_bytes


def make_rom_rw(target_root: Path | str, dry_run: bool = False) -> RomRwResult:
    """Enable full read-write access to ROM by removing overlay mounts and unsharing ext4 blocks."""
    print(BANNER_ROM_RW + "\n")

    root = Path(target_root).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    if not eff_root.is_dir():
        print(f"find: '{base_dir}': No such file or directory\n")
        print(f"stat: '{base_dir / 'vendor' / 'etc' / 'fstab*'}': No such file or directory")
        print(f"Error: fstab files not found at {base_dir / 'vendor' / 'etc' / 'fstab*'}\n")
        return RomRwResult([], 0, [], [], dry_run)

    modified_fstabs: list[Path] = []
    total_overlay_lines = 0
    removed_inits: list[Path] = []
    unshared_images: list[Path] = []

    # 1. Modify fstab files to remove 'overlay' mounts
    fstab_candidates = list(eff_root.glob("**/etc/fstab*"))
    if not fstab_candidates and base_dir != eff_root:
        fstab_candidates = list(base_dir.glob("**/etc/fstab*"))
    if not fstab_candidates:
        print(f"stat: '{base_dir / 'vendor' / 'etc' / 'fstab*'}': No such file or directory")
        print(f"Error: fstab files not found at {base_dir / 'vendor' / 'etc' / 'fstab*'}")

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
                    print(f"Removing overlay mounts from: {fstab.name} ({lines_changed} mounts)")
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
            print(f"Removing MIUI overlay init: {init_file.name}")
            if not dry_run:
                init_file.unlink()

    # 3. Unshare ext4 blocks for any .img files in the directory
    for img in root.glob("**/*.img"):
        if img.is_file() and detect_image_type(img) == ImageType.EXT4:
            unshared_images.append(img)
            print(f"Unsharing ext4 blocks for: {img.name}")
            if not dry_run:
                try:
                    run_tool("e2fsck", ["-y", "-E", "unshare_blocks", str(img)], check=False)
                except Exception:
                    pass

    if modified_fstabs or removed_inits:
        print(f"[✓] ROM Read-Write patch applied ({total_overlay_lines} overlay lines removed)\n")
    else:
        print(f"ROM Read-Write complete (no overlay mounts found to remove)\n")

    return RomRwResult(
        fstab_files_modified=modified_fstabs,
        overlay_lines_removed=total_overlay_lines,
        init_scripts_removed=removed_inits,
        unshared_ext4_images=unshared_images,
        dry_run=dry_run,
    )


def decrypt_rom(target_root: Path | str, dry_run: bool = False) -> RomDecryptResult:
    """Modify fstab files to convert forced fileencryption to fileencryptable for dirty flashing."""
    print(BANNER_DECRYPT + "\n")

    root = Path(target_root).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    if not eff_root.is_dir():
        print(f"find: '{base_dir}': No such file or directory\n")
        print(f"stat: '{base_dir / 'vendor' / 'etc' / 'fstab*'}': No such file or directory")
        print(f"Error: fstab files not found at {base_dir / 'vendor' / 'etc' / 'fstab*'}\n")
        return RomDecryptResult([], 0, dry_run)

    modified_fstabs: list[Path] = []
    total_lines_changed = 0

    fstab_candidates = list(eff_root.glob("**/etc/fstab*"))
    if not fstab_candidates and base_dir != eff_root:
        fstab_candidates = list(base_dir.glob("**/etc/fstab*"))
    if not fstab_candidates:
        print(f"stat: '{base_dir / 'vendor' / 'etc' / 'fstab*'}': No such file or directory")
        print(f"Error: fstab files not found at {base_dir / 'vendor' / 'etc' / 'fstab*'}")

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
                    print(f"Disabling encryption in fstab: {fstab.name} ({fstab_changed} flags)")
                    if not dry_run:
                        fstab.with_suffix(fstab.suffix + ".bak").write_text(content, encoding="utf-8")
                        fstab.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except OSError:
                pass

    if modified_fstabs:
        print(f"[✓] ROM Decryption patch applied ({total_lines_changed} encryption lines disabled)\n")
    else:
        print(f"ROM Decryption complete (no encryption flags found to modify)\n")

    return RomDecryptResult(
        fstab_files_modified=modified_fstabs,
        lines_modified=total_lines_changed,
        dry_run=dry_run,
    )
