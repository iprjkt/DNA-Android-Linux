"""Android ROM and Image Patching Engine.

Implements native Linux equivalents for the DNA-Android Patch Menu:
- AVB vbmeta header flag patching (disable verity/verification)
- Play Integrity / fingerprint spoofing (Pixel 7 Pro)
- SafetyCore placeholder injection
- Priv-App permissions enforcement removal
- Xiaomi OTA update disabling
- Xiaomi telemetry and background service removal
"""

from __future__ import annotations

import re
import shutil
import struct
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from dna_core.prop import PropFile, find_prop_files

# AVB 2.0 Magic bytes
AVB_MAGIC = b"AVB0"
AVB_FLAGS_OFFSET = 120  # uint32_t at offset 120 (big-endian)

# AVB Image Flags
AVB_FLAG_HASHTREE_DISABLED = 1 << 0      # 1: Disable dm-verity
AVB_FLAG_VERIFICATION_DISABLED = 1 << 1  # 2: Disable dm-verification

# Certified default device fingerprint (Pixel 7 Pro)
DEFAULT_FINGERPRINT = (
    "google/cheetah/cheetah:14/AP2A.240805.005/12025142:user/release-keys"
)
DEFAULT_MODEL = "Pixel 7 Pro"


def patch_vbmeta(
    image_path: Path | str,
    mode: str = "both",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Patch AVB vbmeta image flags to disable dm-verity and/or dm-verification.

    Args:
        image_path: Path to vbmeta image file.
        mode: Patch mode: 'verity', 'verification', 'both', or 'enable'.
        dry_run: If True, do not modify the file.

    Returns:
        Dict with status, old_flags, new_flags, and description.
    """
    img = Path(image_path)
    if not img.is_file():
        raise FileNotFoundError(f"vbmeta image not found: {img}")

    with img.open("rb") as f:
        header = f.read(256)

    if len(header) < 124 or header[:4] != AVB_MAGIC:
        raise ValueError(f"Not a valid AVB vbmeta image: magic mismatch ({img})")

    old_flags = struct.unpack(">I", header[AVB_FLAGS_OFFSET : AVB_FLAGS_OFFSET + 4])[0]

    mode_lower = mode.lower()
    if mode_lower == "verity":
        new_flags = old_flags | AVB_FLAG_HASHTREE_DISABLED
    elif mode_lower == "verification":
        new_flags = old_flags | AVB_FLAG_VERIFICATION_DISABLED
    elif mode_lower == "both":
        new_flags = old_flags | AVB_FLAG_HASHTREE_DISABLED | AVB_FLAG_VERIFICATION_DISABLED
    elif mode_lower == "enable":
        new_flags = old_flags & ~(AVB_FLAG_HASHTREE_DISABLED | AVB_FLAG_VERIFICATION_DISABLED)
    else:
        raise ValueError(
            f"Unknown patch mode: '{mode}'. Must be 'verity', 'verification', 'both', or 'enable'."
        )

    if not dry_run and old_flags != new_flags:
        with img.open("r+b") as f:
            f.seek(AVB_FLAGS_OFFSET)
            f.write(struct.pack(">I", new_flags))

    return {
        "image": str(img),
        "mode": mode,
        "old_flags": old_flags,
        "new_flags": new_flags,
        "modified": old_flags != new_flags,
        "dry_run": dry_run,
    }


def patch_integrity_fix(
    target_dir: Path | str,
    fingerprint: Optional[str] = None,
    model: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply Google Play Integrity fingerprint spoofing across build.prop files.

    Args:
        target_dir: Directory containing unpacked partitions or build.prop files.
        fingerprint: Custom build fingerprint (defaults to certified Pixel 7 Pro).
        model: Custom model name (defaults to Pixel 7 Pro).
        dry_run: If True, simulate changes without writing files.

    Returns:
        Dict with list of modified files and applied properties.
    """
    root = Path(target_dir)
    fp = fingerprint or DEFAULT_FINGERPRINT
    mdl = model or DEFAULT_MODEL

    prop_files = find_prop_files(root)
    if not prop_files:
        return {"target": str(root), "modified_files": [], "dry_run": dry_run}

    modified_files: List[str] = []
    applied_props = {
        "ro.build.fingerprint": fp,
        "ro.system.build.fingerprint": fp,
        "ro.product.build.fingerprint": fp,
        "ro.vendor.build.fingerprint": fp,
        "ro.system_ext.build.fingerprint": fp,
        "ro.odm.build.fingerprint": fp,
        "ro.product.brand": "google",
        "ro.product.manufacturer": "Google",
        "ro.product.model": mdl,
        "ro.product.name": "cheetah",
        "ro.product.device": "cheetah",
    }

    for prop_path in prop_files:
        prop = PropFile.load(prop_path)
        changed = False

        # If this prop file already defines any fingerprint property, update them
        for key, val in applied_props.items():
            if prop.has_key(key):
                if prop.get(key) != val:
                    prop.set(key, val)
                    changed = True

        # In system, product, or main build.prop, ensure ro.build.fingerprint and model exist
        if "build.prop" in prop_path.name:
            if not prop.has_key("ro.build.fingerprint"):
                prop.set("ro.build.fingerprint", fp)
                changed = True
            if not prop.has_key("ro.product.model"):
                prop.set("ro.product.model", mdl)
                changed = True

        if changed:
            if not dry_run:
                prop.save()
            modified_files.append(str(prop_path))

    return {
        "target": str(root),
        "fingerprint": fp,
        "model": mdl,
        "modified_files": modified_files,
        "dry_run": dry_run,
    }


def patch_safetycore(
    target_dir: Path | str,
    placeholder_apk: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Inject SafetyCore placeholder APK into target product/app tree.

    Args:
        target_dir: Directory containing unpacked partitions.
        placeholder_apk: Path to custom Safetycore.apk (defaults to bundled APK).
        dry_run: If True, simulate without copying.

    Returns:
        Dict with status and target path.
    """
    root = Path(target_dir)

    if placeholder_apk is not None:
        src_apk = Path(placeholder_apk)
    else:
        # Check repo bundled location
        src_apk = Path(__file__).resolve().parent.parent / "data" / "safetycore" / "Safetycore.apk"

    if not src_apk.is_file():
        raise FileNotFoundError(f"Safetycore placeholder APK not found: {src_apk}")

    # Determine product/app destination
    # Target can be either the unpacked/ root or unpacked/product directly
    if (root / "product" / "app").is_dir():
        dst_dir = root / "product" / "app" / "Safetycore"
    elif (root / "app").is_dir() and "product" in root.name:
        dst_dir = root / "app" / "Safetycore"
    elif (root / "product").is_dir():
        dst_dir = root / "product" / "app" / "Safetycore"
    else:
        dst_dir = root / "product" / "app" / "Safetycore"

    dst_apk = dst_dir / "Safetycore.apk"

    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_apk, dst_apk)
        dst_dir.chmod(0o755)
        dst_apk.chmod(0o644)

    return {
        "source": str(src_apk),
        "destination": str(dst_apk),
        "dry_run": dry_run,
    }


def patch_privapp_permissions(
    target_dir: Path | str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove ro.control_privapp_permissions from build.prop files to bypass enforcement.

    Args:
        target_dir: Directory containing unpacked partitions or build.prop files.
        dry_run: If True, simulate without modifying files.

    Returns:
        Dict with modified files list.
    """
    root = Path(target_dir)
    prop_files = find_prop_files(root)
    modified_files: List[str] = []

    target_prop = "ro.control_privapp_permissions"

    for prop_path in prop_files:
        prop = PropFile.load(prop_path)
        if prop.has_key(target_prop):
            prop.delete(target_prop)
            if not dry_run:
                prop.save()
            modified_files.append(str(prop_path))

    return {
        "target": str(root),
        "property_removed": target_prop,
        "modified_files": modified_files,
        "dry_run": dry_run,
    }


def patch_disable_ota(
    target_dir: Path | str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Disable OTA update validation in Xiaomi device feature XML files.

    Searches for XML files under `device_features/` and replaces
    `support_ota_validate` true values with false.

    Args:
        target_dir: Directory containing unpacked partitions.
        dry_run: If True, simulate without modifying files.

    Returns:
        Dict with modified XML files list.
    """
    root = Path(target_dir)
    if not root.is_dir():
        return {"target": str(root), "modified_files": [], "dry_run": dry_run}

    # Search for all xml files in device_features directories
    xml_files: List[Path] = []
    for p in root.rglob("*.xml"):
        if "device_features" in p.parts:
            xml_files.append(p)

    modified_files: List[str] = []
    pattern = re.compile(
        r'(<bool\s+name=["\']support_ota_validate["\']>)\s*true\s*(</bool>)',
        re.IGNORECASE,
    )

    for xml_path in xml_files:
        content = xml_path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(content):
            new_content = pattern.sub(r"\g<1>false\g<2>", content)
            if not dry_run:
                xml_path.write_text(new_content, encoding="utf-8")
            modified_files.append(str(xml_path))

    return {
        "target": str(root),
        "modified_files": modified_files,
        "count": len(modified_files),
        "dry_run": dry_run,
    }


def patch_disable_xiaomi_services(
    target_dir: Path | str,
    config_path: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove Xiaomi telemetry, tracking, and bloat services based on TOML definitions.

    Args:
        target_dir: Directory containing unpacked partitions.
        config_path: Path to custom TOML config (defaults to data/patches/xiaomi_services.toml).
        dry_run: If True, simulate without deleting files.

    Returns:
        Dict with removed packages and paths.
    """
    root = Path(target_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Target directory not found: {root}")

    if config_path is not None:
        cfg_file = Path(config_path)
    else:
        cfg_file = Path(__file__).resolve().parent.parent / "data" / "patches" / "xiaomi_services.toml"

    if not cfg_file.is_file():
        raise FileNotFoundError(f"Xiaomi services configuration not found: {cfg_file}")

    with cfg_file.open("rb") as f:
        config = tomllib.load(f)

    packages = config.get("packages", [])
    removed_entries: List[Dict[str, Any]] = []
    total_freed_bytes = 0

    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        pkg_paths = pkg.get("paths", [])
        for rel_path in pkg_paths:
            # Check relative to root
            target = root / rel_path
            # Also check if rel_path parts match within subdirectories (e.g. root is product/)
            candidates = [target]
            parts = Path(rel_path).parts
            if parts and parts[0] in [d.name for d in root.iterdir() if d.is_dir()]:
                # Directly under partition
                pass
            else:
                # If root IS the partition (e.g. root is 'product')
                if parts and root.name == parts[0]:
                    candidates.append(root.joinpath(*parts[1:]))

            for cand in candidates:
                if cand.exists() and cand.is_dir():
                    freed = sum(f.stat().st_size for f in cand.rglob("*") if f.is_file())
                    total_freed_bytes += freed
                    removed_entries.append({
                        "package": pkg_name,
                        "path": str(cand),
                        "freed_bytes": freed,
                    })
                    if not dry_run:
                        shutil.rmtree(cand)

    return {
        "target": str(root),
        "removed_entries": removed_entries,
        "total_removed": len(removed_entries),
        "total_freed_bytes": total_freed_bytes,
        "dry_run": dry_run,
    }
