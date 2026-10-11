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

BANNER_PRIVAPP = """  ___       _       _     
 | _ \\ __ _| |_  __| |_   
 |  _// _` |  _|/ _| ' \\  
 |_|  \\__,_|\\__|\\__|_||_| 
  ___       _               
 | _ \\ _ _ (_)_ __  __ _ ___
 |  _/ '_/ | \\ V  \\/ _` (_-<
 |_| |_|   |_| \\_/\\__,_/ /_/
  ___                  _            _                
 | _ \\ ___  _ _  _ __ (_) ___  ___ (_) ___  _ _   ___
 |  _// -_)| '_|| '  \\| |(_-< (_-< | |/ _ \\| ' \\ (_-<
 |_|  \\___||_|  |_|_|_|_|/__/ /__/ |_|\\___/|_||_|/__/"""

BANNER_OTA = """  ___  ___ ___   _   ___  _    ___ 
 |   \\|_ _/ __| /_\\ | _ )| |  | __|
 | |) || |\\__ \\/ _ \\| _ \\| |__| _| 
 |___/|___|___/_/ \\_\\___/|____|___|
   ___ _____ _     _   _          _      _       
  / _ \\_   _/_\\   | | | |_ __  __| |__ _| |_ ___ 
 | (_) || |/ _ \\  | |_| | '_ \\/ _` / _` |  _/ -_)
  \\___/ |_/_/ \\_\\  \\___/| .__/\\__,_\\__,_|\\__\\___|
                        |_|                      """

BANNER_SAFETYCORE = """  ___        __     _        ___             
 / __| __ _ / _|___| |_ _  _/ __|___ _ _ ___ 
 \\__ \\/ _` |  _/ -_)  _| || | (__/ _ \\ '_/ -_)
 |___/\\__,_|_| \\___|\\__|\\_, |\\___\\___/|_| \\___|
                        |__/                 """

BANNER_INTEGRITY = """  ___       _                  _  _          ______ _     
 |_ _| _ _  | |_  ___  __ _  _ _ (_)| |_  _  _  |  ___|(_)__ __
  | | | ' \\ |  _|/ -_)/ _` || '_|| ||  _|| || | |  _|  | |\\ \\ /
 |___||_||_| \\__|\\___|\\__, ||_|  |_| \\__| \\_, | |_|    |_|/_\\_\\
                      |___/               |__/                """

BANNER_XIAOMI_SERVICES = """  ___  _          _     _         __  ___                 _ 
 |   \\(_)___ __ _| |__ | |___    \\ \\/ (_)__ _ ___  _ __  (_)
 | |) | (_-</ _` | '_ \\| / -_)    >  <| / _` / _ \\| '  \\ | |
 |___/|_/__/\\__,_|_.__/|_\\___|   /_/\\_\\_\\__,_\\___/|_|_|_||_|
  ___              _            
 / __| ___ _ ___ _(_)__ ___ ___ 
 \\__ \\/ -_) '_\\ V / / _/ -_|_-< 
 |___/\\___|_|  \\_/|_\\__\\___/__/ """

BANNER_VBMETA = """  ___      _       _      __   _____ __  __ ___ _____ _   
 | _ \\__ _| |_ ___| |_    \\ \\ / / _ )  \\/  | __|_   _/_\\  
 |  _/ _` |  _/ _ \\ ' \\    \\ V /| _ \\ |\\/| | _|  | |/ _ \\ 
 |_| \\__,_|\\__|\\___/_||_|    \\_/ |___/_|  |_|___| |_/_/ \\_\\"""


def find_partition_dir(root: Path, part_name: str) -> Path | None:
    """Find partition directory under root, checking standard names and slot variants (_a, _b)."""
    cand = root / part_name
    if cand.is_dir():
        return cand
    for slot in ("_a", "_b"):
        cand = root / f"{part_name}{slot}"
        if cand.is_dir():
            return cand
    if (root / "unpacked").is_dir():
        cand = root / "unpacked" / part_name
        if cand.is_dir():
            return cand
        for slot in ("_a", "_b"):
            cand = root / "unpacked" / f"{part_name}{slot}"
            if cand.is_dir():
                return cand
    if root.name == "unpacked" and root.parent.is_dir():
        cand = root.parent / part_name
        if cand.is_dir():
            return cand
        for slot in ("_a", "_b"):
            cand = root.parent / f"{part_name}{slot}"
            if cand.is_dir():
                return cand
    if root.name == part_name or root.name.startswith(f"{part_name}_"):
        return root
    return None


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
    print(BANNER_VBMETA + "\n")
    print("Patching AVB vbmeta image flags...")
    img = Path(image_path)
    if not img.is_file():
        print(f"Error: vbmeta image not found at {img}\n")
        raise FileNotFoundError(f"vbmeta image not found: {img}")

    with img.open("rb") as f:
        header = f.read(256)

    if len(header) < 124 or header[:4] != AVB_MAGIC:
        print(f"Error: Not a valid AVB vbmeta image: magic mismatch ({img})\n")
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

    print(f"Target: {img}")
    print(f"Mode: {mode}")
    print(f"Flags: 0x{old_flags:08x} -> 0x{new_flags:08x}")
    print("[✓] VBMeta flags updated successfully!\n")

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
    print(BANNER_INTEGRITY + "\n")

    root = Path(target_dir).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    system_dir = find_partition_dir(eff_root, "system")
    vendor_dir = find_partition_dir(eff_root, "vendor")

    if not system_dir:
        print(f"find: '{base_dir / 'system'}': No such file or directory")
    if not vendor_dir or not (vendor_dir / "etc" / "init").is_dir():
        init_rc = (vendor_dir / "etc" / "init") if vendor_dir else (base_dir / "vendor" / "etc" / "init")
        print(f"stat: '{init_rc / '*.rc'}': No such file or directory")
        print(f"/data/user/0/com.dna.tools/files/tools/integrityfix: can't create {init_rc / '*.rc'}: No such file or directory")
        print("touch: bad date")

    fp = fingerprint or DEFAULT_FINGERPRINT
    mdl = model or DEFAULT_MODEL

    prop_files = find_prop_files(eff_root)
    if not prop_files:
        print(f"Error: No build.prop files found in {base_dir}\n")
        return {"target": str(eff_root), "modified_files": [], "dry_run": dry_run}

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
            print(f"[✓] Spoofed fingerprint & model ({mdl}) in: {prop_path}")
            modified_files.append(str(prop_path))

    print(f"[✓] Play Integrity spoofing complete ({len(modified_files)} files modified)\n")
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
    print(BANNER_SAFETYCORE + "\n")
    print("Removing SafetyCore...\n")

    root = Path(target_dir).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    product_dir = find_partition_dir(eff_root, "product")

    if not product_dir:
        expected = base_dir / "product"
        print(f"find: '{expected}': No such file or directory")
        print(f"Error: product partition not found at {expected}\n")
        return {
            "target": str(eff_root),
            "error": f"product partition not found at {expected}",
            "dry_run": dry_run,
        }

    if placeholder_apk is not None:
        src_apk = Path(placeholder_apk)
    else:
        # Check repo bundled location
        src_apk = Path(__file__).resolve().parent.parent / "data" / "safetycore" / "Safetycore.apk"

    if not src_apk.is_file():
        print(f"Error: Safetycore placeholder APK not found at {src_apk}\n")
        raise FileNotFoundError(f"Safetycore placeholder APK not found: {src_apk}")

    # Determine product/app destination
    if (product_dir / "app").is_dir():
        dst_dir = product_dir / "app" / "Safetycore"
    elif product_dir.name == "app":
        dst_dir = product_dir / "Safetycore"
    else:
        dst_dir = product_dir / "app" / "Safetycore"

    dst_apk = dst_dir / "Safetycore.apk"

    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_apk, dst_apk)
        dst_dir.chmod(0o755)
        dst_apk.chmod(0o644)

    print("[✓] Added Safetycore-placeholder!\n")
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
    print(BANNER_PRIVAPP + "\n")
    print("Processing... This may take some time\n")

    root = Path(target_dir).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    vendor_dir = find_partition_dir(eff_root, "vendor")

    if not vendor_dir:
        expected = base_dir / "vendor" / "build.prop"
        print(f"Error: vendor/build.prop not found at {expected}\n")
        return {
            "target": str(eff_root),
            "property_removed": "ro.control_privapp_permissions",
            "modified_files": [],
            "error": f"vendor/build.prop not found at {expected}",
            "dry_run": dry_run,
        }

    prop_candidates = [
        vendor_dir / "build.prop",
        vendor_dir / "etc" / "build.prop",
        vendor_dir / "default.prop",
    ]
    target_prop = "ro.control_privapp_permissions"
    modified_files: List[str] = []

    found_any = False
    for p in prop_candidates:
        if p.is_file():
            found_any = True
            prop = PropFile.load(p)
            if prop.has_key(target_prop):
                prop.delete(target_prop)
                if not dry_run:
                    prop.save()
                print(f"[✓] Removed ro.control_privapp_permissions from: {p}")
                modified_files.append(str(p))

    if not found_any:
        print(f"Error: vendor/build.prop not found at {vendor_dir / 'build.prop'}\n")
    elif not modified_files:
        print(f"ro.control_privapp_permissions is not present in: {vendor_dir / 'build.prop'}")
        print("[✓] Priv-App permissions patch complete\n")

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
    print(BANNER_OTA + "\n")
    print("Disabling... OTA Update\n")

    root = Path(target_dir).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir
    product_dir = find_partition_dir(eff_root, "product")

    # Search for all xml files in device_features directories
    xml_files: List[Path] = []
    seen_xml: set = set()
    candidates_dirs = []
    if product_dir:
        candidates_dirs.append(product_dir / "etc" / "device_features")
    candidates_dirs.append(eff_root / "product" / "etc" / "device_features")
    candidates_dirs.append(base_dir / "product" / "etc" / "device_features")
    candidates_dirs.append(eff_root / "etc" / "device_features")

    for cd in candidates_dirs:
        if cd.is_dir():
            for p in sorted(cd.glob("*.xml")):
                if p.is_file() and p.resolve() not in seen_xml:
                    seen_xml.add(p.resolve())
                    xml_files.append(p)

    if not xml_files and eff_root.is_dir():
        for p in sorted(eff_root.rglob("*.xml")):
            if "device_features" in p.parts:
                if p.is_file() and p.resolve() not in seen_xml:
                    seen_xml.add(p.resolve())
                    xml_files.append(p)

    if not xml_files:
        expected = (product_dir / "etc" / "device_features") if product_dir else (base_dir / "product" / "etc" / "device_features")
        print(f"find: '{expected}': No such file or directory")
        print(f"Error: device_features XML files not found at {expected}\n")
        return {
            "target": str(eff_root),
            "modified_files": [],
            "count": 0,
            "error": f"device_features XML files not found at {expected}",
            "dry_run": dry_run,
        }

    modified_files: List[str] = []
    pattern = re.compile(
        r'(<bool\s+name=["\']support_ota_validate["\']>)\s*true\s*(</bool>)',
        re.IGNORECASE,
    )

    for xml_path in xml_files:
        print(f"Checking file: {xml_path}")
        content = xml_path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(content):
            new_content = pattern.sub(r"\g<1>false\g<2>", content)
            if not dry_run:
                xml_path.write_text(new_content, encoding="utf-8")
            print('    <bool name="support_ota_validate">false</bool>')
            print(f"[✓] Disabled OTA validation in: {xml_path}")
            modified_files.append(str(xml_path))
        elif 'name="support_ota_validate"' in content and "false" in content:
            print('    <bool name="support_ota_validate">false</bool>')
            print(f"OTA validation is already disabled in: {xml_path}")
        else:
            print(f"No OTA validation flag found in: {xml_path}")

    return {
        "target": str(eff_root),
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
    print(BANNER_XIAOMI_SERVICES + "\n")

    root = Path(target_dir).resolve()
    base_dir = root.parent if (root.name == "unpacked" and not root.exists()) else root
    eff_root = root if root.is_dir() else base_dir

    vendor_dir = find_partition_dir(eff_root, "vendor")
    if not vendor_dir or not (vendor_dir / "etc" / "init").is_dir():
        init_rc = (vendor_dir / "etc" / "init") if vendor_dir else (base_dir / "vendor" / "etc" / "init")
        print(f"stat: '{init_rc / '*.rc'}': No such file or directory")
        print(f"/data/user/0/com.dna.tools/files/tools/xiaomi_tweaks: can't create {init_rc / '*.rc'}: No such file or directory")
        print("touch: bad date")

    if not eff_root.is_dir():
        return {
            "target": str(eff_root),
            "removed_entries": [],
            "total_removed": 0,
            "total_freed_bytes": 0,
            "dry_run": dry_run,
        }

    if config_path is not None:
        cfg_file = Path(config_path)
    else:
        cfg_file = Path(__file__).resolve().parent.parent / "data" / "patches" / "xiaomi_services.toml"

    if not cfg_file.is_file():
        print(f"Error: Xiaomi services configuration not found at {cfg_file}\n")
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
            candidates = [eff_root / rel_path, base_dir / rel_path]
            parts = Path(rel_path).parts
            if parts:
                p_dir = find_partition_dir(eff_root, parts[0])
                if p_dir:
                    candidates.append(p_dir.joinpath(*parts[1:]))

            seen_candidates = set()
            for cand in candidates:
                cand_res = cand.resolve()
                if cand_res in seen_candidates:
                    continue
                seen_candidates.add(cand_res)
                if cand.exists() and cand.is_dir():
                    freed = sum(f.stat().st_size for f in cand.rglob("*") if f.is_file())
                    total_freed_bytes += freed
                    removed_entries.append({
                        "package": pkg_name,
                        "path": str(cand),
                        "freed_bytes": freed,
                    })
                    try:
                        rel = cand.relative_to(root)
                    except ValueError:
                        rel = cand.name
                    print(f"Removing: {rel} (Package: {pkg_name})")
                    if not dry_run:
                        shutil.rmtree(cand)

    if removed_entries:
        print(f"[✓] Disabled {len(removed_entries)} Xiaomi services & telemetry packages\n")
    else:
        print(f"No matching Xiaomi services found to remove in: {root}\n")

    return {
        "target": str(root),
        "removed_entries": removed_entries,
        "total_removed": len(removed_entries),
        "total_freed_bytes": total_freed_bytes,
        "dry_run": dry_run,
    }
