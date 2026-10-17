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


def is_system_as_root(src_dir: Path | str | None, part_name: str = "system") -> bool:
    """Detect if the target directory is a System-As-Root (SAR) partition tree.
    In SAR, system.img contains the rootfs layout (e.g. init, d, etc, bin) and a nested
    'system/' directory, mounted directly at '/' during boot."""
    if not src_dir:
        return False
    src = Path(src_dir).resolve()
    clean_part = part_name.strip("/").removesuffix("_a").removesuffix("_b").lower() if part_name else ""
    if clean_part and clean_part != "system":
        return False
    system_sub = src / "system"
    if system_sub.is_dir():
        if (
            (src / "init").exists()
            or (system_sub / "bin" / "init").exists()
            or (system_sub / "build.prop").is_file()
            or (src / "bin").exists()
        ):
            return True
    return False


def get_effective_mount_point(src_dir: Path | str, part_name: str) -> str:
    """Return the effective mount point for a partition.
    For System-As-Root system partition, the image itself is root ('/').
    For non-SAR system and other partitions (vendor, product, etc.), it is '/<part_name>'."""
    if is_system_as_root(src_dir, part_name):
        return "/"
    clean_part = part_name.strip("/").removesuffix("_a").removesuffix("_b")
    return f"/{clean_part}" if clean_part else "/"


def sanitize_fs_config_entry(
    entry: FsConfigEntry,
    is_sar: bool = False,
    root_dir: Path | str | None = None,
) -> FsConfigEntry:
    """Sanitize UID/GID and mode for Android filesystem entries.
    Host Linux desktop users typically have UID/GID >= 1000, which must be mapped to
    Android AID_ROOT (0) or AID_SHELL (2000). Also fixes SAR double-prefix issues."""
    path = entry.path.strip("/")

    # In SAR, fix erroneous double-prefixes (e.g. 'system/system/...' -> 'system/...', or 'system/init' -> 'init')
    if is_sar:
        if path.startswith("system/system/"):
            path = path[7:]
        elif root_dir and path.startswith("system/"):
            sub = path[7:]
            if os.path.lexists(Path(root_dir) / sub) and not os.path.lexists(Path(root_dir) / path):
                path = sub

    # UID sanitization: Host user (>= 1000) maps to Android root (0)
    uid = 0 if entry.uid >= 1000 else entry.uid

    # GID sanitization: Host group (>= 1000) maps to Android shell (2000) for bin executables, else root (0)
    is_bin = ("bin/" in path or path.startswith("bin/")) and "init" not in path
    if entry.gid >= 1000:
        gid = 2000 if is_bin else 0
    else:
        gid = entry.gid

    # Mode and permission sanitization for critical Android binaries
    mode = entry.mode
    if path in ("init", "system/bin/init", "bin/init"):
        uid = 0
        gid = 0
        mode = "755"
    elif path.endswith("run-as"):
        uid = 0
        gid = 2000
        mode = "4750"
    elif path == "lost+found":
        uid = 0
        gid = 0
        mode = "700"
    elif path in ("/", "system"):
        uid = 0
        gid = 0
        mode = "755"

    return FsConfigEntry(path=path or "/", uid=uid, gid=gid, mode=mode, capabilities=entry.capabilities)


def get_fallback_file_contexts(part_name: str = "system", is_sar: bool = False) -> list[tuple[str, str]]:
    """Return standard authoritative fallback SELinux file contexts for partitions."""
    clean_part = part_name.strip("/").removesuffix("_a").removesuffix("_b").lower()
    if clean_part == "system" or is_sar:
        return [
            ("/", "u:object_r:rootfs:s0"),
            (r"/lost\+found", "u:object_r:rootfs:s0"),
            ("/init", "u:object_r:init_exec:s0"),
            ("/system/bin/init", "u:object_r:init_exec:s0"),
            ("/system/bin/sh", "u:object_r:shell_exec:s0"),
            (r"/system/bin/toolbox.*", "u:object_r:toolbox_exec:s0"),
            (r"/system/bin/toybox.*", "u:object_r:toolbox_exec:s0"),
            ("/system/bin/secilc", "u:object_r:secilc_exec:s0"),
            ("/system/bin/servicemanager", "u:object_r:servicemanager_exec:s0"),
            ("/system/bin/vold", "u:object_r:vold_exec:s0"),
            ("/system/bin/netd", "u:object_r:netd_exec:s0"),
            (r"/system/bin/linker(64)?", "u:object_r:system_linker_exec:s0"),
            (r"/system/bin/bootstrap/linker(64)?", "u:object_r:system_bootstrap_lib_file:s0"),
            (r"/system/lib(64)?(/.*)?", "u:object_r:system_lib_file:s0"),
            (r"/system/etc/selinux(/.*)?", "u:object_r:sepolicy_file:s0"),
            (r"/apex(/.*)?", "u:object_r:apex_mnt_dir:s0"),
            (r"/system(/.*)?", "u:object_r:system_file:s0"),
            (r"/(.*)?", "u:object_r:rootfs:s0"),
        ]

    default_label = "u:object_r:vendor_file:s0" if clean_part in ("vendor", "odm") else f"u:object_r:{clean_part}_file:s0"
    entries = [
        (rf"/{clean_part}/lost\+found", "u:object_r:rootfs:s0"),
    ]
    if clean_part == "vendor":
        entries.extend([
            (r"/vendor/bin/hw/.*", "u:object_r:hal_generic_exec:s0"),
            (r"/vendor/etc/selinux(/.*)?", "u:object_r:vendor_configs_file:s0"),
        ])
    elif clean_part in ("product", "system_ext"):
        entries.append((rf"/{clean_part}/etc/selinux(/.*)?", "u:object_r:system_file:s0"))

    entries.append((rf"/{clean_part}(/.*)?", default_label))
    return entries


def harvest_partition_file_contexts(
    root_dir: Path | str,
    part_name: str = "system",
    is_sar: bool = False,
) -> list[tuple[str, str]]:
    """Discover and parse canonical SELinux file_contexts within an extracted partition tree.
    Reads official plat_file_contexts, vendor_file_contexts, etc. to guarantee exact SELinux labels."""
    root = Path(root_dir).resolve()
    clean_part = part_name.strip("/").removesuffix("_a").removesuffix("_b").lower()

    candidates: list[Path] = []
    if clean_part == "system" or is_sar:
        candidates.extend([
            root / "system" / "etc" / "selinux" / "plat_file_contexts",
            root / "etc" / "selinux" / "plat_file_contexts",
            root / "system" / "etc" / "selinux" / "system_file_contexts",
            root / "etc" / "selinux" / "system_file_contexts",
            root / "plat_file_contexts",
        ])
    else:
        candidates.extend([
            root / "etc" / "selinux" / f"{clean_part}_file_contexts",
            root / clean_part / "etc" / "selinux" / f"{clean_part}_file_contexts",
            root / "etc" / "selinux" / "nonplat_file_contexts",
            root / f"{clean_part}_file_contexts",
        ])

    for cand in candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            parsed = parse_raw_file_contexts(cand.read_text(encoding="utf-8", errors="replace"), is_sar=is_sar, part_name=clean_part)
            if parsed:
                return parsed

    # Recursive search for *file_contexts in etc/selinux
    try:
        for fc_path in root.glob("**/etc/selinux/*file_contexts"):
            if fc_path.is_file() and fc_path.stat().st_size > 0:
                if clean_part in fc_path.name or (clean_part == "system" and "plat" in fc_path.name):
                    parsed = parse_raw_file_contexts(fc_path.read_text(encoding="utf-8", errors="replace"), is_sar=is_sar, part_name=clean_part)
                    if parsed:
                        return parsed
    except OSError:
        pass

    return get_fallback_file_contexts(part_name=clean_part, is_sar=is_sar)


def parse_raw_file_contexts(content: str, is_sar: bool = False, part_name: str = "system") -> list[tuple[str, str]]:
    """Parse raw file_contexts text into normalized (pattern, context) pairs."""
    entries: list[tuple[str, str]] = []
    has_lost_found = False
    has_root_fallback = False
    clean_part = part_name.strip("/").removesuffix("_a").removesuffix("_b").lower()
    fallback_pat = rf"/{clean_part}(/.*)?" if not is_sar else r"/(.*)?"

    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) >= 2:
            # Pattern may have file type modifier e.g. "/system/bin/toolbox -- u:object_r:toolbox_exec:s0"
            if len(parts) == 3 and parts[1].startswith("-"):
                pat = f"{parts[0]}\t{parts[1]}"
                ctx = parts[2]
            else:
                pat = parts[0]
                ctx = parts[-1]

            if "lost+found" in pat or r"lost\+found" in pat:
                has_lost_found = True
            if pat == fallback_pat or pat == f"/{clean_part}(/.*)?":
                has_root_fallback = True

            entries.append((pat, ctx))

    # Guarantee critical e2fsdroid requirements
    if not has_lost_found:
        lf_pat = r"/lost\+found" if (is_sar or not clean_part) else rf"/{clean_part}/lost\+found"
        entries.insert(0, (lf_pat, "u:object_r:rootfs:s0"))

    if not has_root_fallback:
        def_label = "u:object_r:system_file:s0" if clean_part == "system" else f"u:object_r:{clean_part}_file:s0"
        entries.append((fallback_pat, def_label))

    return entries


def scan_directory_fs_metadata(
    root_dir: Path | str,
    mount_point: str = "system",
) -> tuple[list[FsConfigEntry], list[tuple[str, str]]]:
    """Scan an extracted directory tree and generate fs_config and file_contexts entries."""
    root = Path(root_dir).resolve()
    clean_mount = mount_point.strip("/")
    is_sar = is_system_as_root(root, clean_mount)
    if is_sar:
        clean_mount = ""

    # 1. Harvest canonical SELinux file contexts
    fc_entries = harvest_partition_file_contexts(root, part_name=mount_point, is_sar=is_sar)

    # 2. Collect fs_config entries via C++ if available or Python fallback
    fs_entries: list[FsConfigEntry] = []

    if _HAVE_CPP:
        try:
            cpp_res = dna_core_cpp.scan_directory_fs_metadata(str(root), clean_mount)
            fs_entries = [
                sanitize_fs_config_entry(
                    FsConfigEntry(path=e.path, uid=e.uid, gid=e.gid, mode=e.mode, capabilities=e.capabilities or None),
                    is_sar=is_sar,
                    root_dir=root,
                )
                for e in cpp_res.fs_entries
            ]
            return fs_entries, fc_entries
        except Exception:
            pass

    # Root filesystem entries for e2fsdroid
    fs_entries.append(FsConfigEntry(path="/", uid=0, gid=0, mode="755"))
    if clean_mount:
        fs_entries.append(FsConfigEntry(path=clean_mount, uid=0, gid=0, mode="755"))

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if str(rel_dir) != ".":
            prefix = f"{clean_mount}/{rel_dir}" if clean_mount else str(rel_dir)
        else:
            prefix = clean_mount

        # Entries for directories
        for d in sorted(dirnames):
            d_path = Path(dirpath) / d
            d_rel = f"{prefix}/{d}" if prefix else d
            try:
                st = os.lstat(d_path)
                mode_octal = oct(st.st_mode & 0o7777)[2:]
                entry = FsConfigEntry(path=d_rel, uid=st.st_uid, gid=st.st_gid, mode=mode_octal)
            except OSError:
                entry = FsConfigEntry(path=d_rel, uid=0, gid=0, mode="755")
            fs_entries.append(sanitize_fs_config_entry(entry, is_sar=is_sar, root_dir=root))

        # Entries for files
        for f in sorted(filenames):
            f_path = Path(dirpath) / f
            f_rel = f"{prefix}/{f}" if prefix else f
            try:
                st = os.lstat(f_path)
                mode_octal = oct(st.st_mode & 0o7777)[2:]
                entry = FsConfigEntry(path=f_rel, uid=st.st_uid, gid=st.st_gid, mode=mode_octal)
            except OSError:
                entry = FsConfigEntry(path=f_rel, uid=0, gid=0, mode="644")
            fs_entries.append(sanitize_fs_config_entry(entry, is_sar=is_sar, root_dir=root))

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
    """Ensure canned fs_config covers all files currently in root_dir tree, sanitizing UIDs/GIDs and fixing paths."""
    target = Path(fs_file).resolve()
    root = Path(root_dir).resolve()
    is_sar = is_system_as_root(root, mount_point)
    clean_mount = "" if is_sar else mount_point.strip("/")

    if not target.is_file():
        entries, _ = scan_directory_fs_metadata(root, mount_point)
        return write_fs_config_file(entries, target)

    existing_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    existing_paths: set[str] = set()
    cleaned_entries: list[FsConfigEntry] = []
    has_modifications = False

    for line in existing_lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 4:
            has_modifications = True
            continue
        path_str = parts[0]
        if ".." in path_str:
            has_modifications = True
            continue

        try:
            uid = int(parts[1])
            gid = int(parts[2])
            mode = parts[3]
            caps = parts[4].split("=")[-1] if len(parts) > 4 and "capabilities=" in parts[4] else None
            raw_entry = FsConfigEntry(path=path_str, uid=uid, gid=gid, mode=mode, capabilities=caps)
            sanitized = sanitize_fs_config_entry(raw_entry, is_sar=is_sar, root_dir=root)
            if sanitized.path != raw_entry.path or sanitized.uid != raw_entry.uid or sanitized.gid != raw_entry.gid or sanitized.mode != raw_entry.mode:
                has_modifications = True

            if sanitized.path not in existing_paths:
                existing_paths.add(sanitized.path)
                cleaned_entries.append(sanitized)
            else:
                has_modifications = True
        except ValueError:
            has_modifications = True

    # Scan current filesystem tree to find any missing entries
    scanned_entries, _ = scan_directory_fs_metadata(root, mount_point)
    added_count = 0
    for entry in scanned_entries:
        if entry.path not in existing_paths:
            cleaned_entries.append(entry)
            existing_paths.add(entry.path)
            added_count += 1

    if has_modifications or added_count > 0:
        write_fs_config_file(cleaned_entries, target)
        if added_count > 0:
            print(f"> Synchronized canned fs_config: added {added_count} missing entries to {target.name}")
        if has_modifications:
            print(f"> Sanitized Android UIDs, GIDs, and path hierarchies in {target.name}")

    return target


def sync_file_contexts_file(
    mount_point: str,
    fc_file: Path | str,
    root_dir: Path | str | None = None,
) -> Path:
    """Ensure canned file_contexts is complete, authoritatively labeled, and free of corrupted paths."""
    target = Path(fc_file).resolve()
    is_sar = is_system_as_root(root_dir, mount_point) if root_dir else False
    clean_mount = "" if is_sar else mount_point.strip("/")

    canonical_entries: list[tuple[str, str]] = []
    if root_dir:
        canonical_entries = harvest_partition_file_contexts(root_dir, part_name=mount_point, is_sar=is_sar)

    if not target.is_file():
        entries = canonical_entries or get_fallback_file_contexts(part_name=mount_point, is_sar=is_sar)
        return write_file_contexts_file(entries, target)

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    cleaned_entries: list[tuple[str, str]] = []
    existing_patterns: set[str] = set()
    has_init_exec = False
    has_lost_found = False

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2 or ".." in parts[0]:
            continue

        if len(parts) == 3 and parts[1].startswith("-"):
            pat = f"{parts[0]}\t{parts[1]}"
            ctx = parts[2]
        else:
            pat = parts[0]
            ctx = parts[-1]

        pat = re.sub(r"^/+", "/", pat)

        if "init_exec" in ctx:
            has_init_exec = True
        if "lost+found" in pat or r"lost\+found" in pat:
            has_lost_found = True

        if pat not in existing_patterns:
            existing_patterns.add(pat)
            cleaned_entries.append((pat, ctx))

    # If the file lacks critical labels or only has stub lines, merge canonical contexts
    needs_enrichment = not has_init_exec if (is_sar or clean_mount == "system") else len(cleaned_entries) < 3
    if needs_enrichment and canonical_entries:
        merged_count = 0
        for pat, ctx in canonical_entries:
            if pat not in existing_patterns:
                cleaned_entries.append((pat, ctx))
                existing_patterns.add(pat)
                merged_count += 1
        if merged_count > 0:
            print(f"> Enriched file_contexts with {merged_count} authoritative rules from partition tree ({target.name})")

    # Guarantee lost+found and root fallback
    if not has_lost_found:
        lf_pat = r"/lost\+found" if (is_sar or not clean_mount) else rf"/{clean_mount}/lost\+found"
        cleaned_entries.insert(0, (lf_pat, "u:object_r:rootfs:s0"))

    fallback_pat = rf"/{clean_mount}(/.*)?" if clean_mount else r"/(.*)?"
    if fallback_pat not in existing_patterns:
        def_label = "u:object_r:system_file:s0" if (clean_mount in ("", "system")) else f"u:object_r:{clean_mount}_file:s0"
        cleaned_entries.append((fallback_pat, def_label))

    write_file_contexts_file(cleaned_entries, target)
    return target
