"""Native Linux tool detection, abstraction, and execution registry for DNA-Linux."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolDefinition:
    """Definition and package metadata for an external native tool."""

    name: str
    category: str
    description: str
    required: bool
    arch_package: str
    debian_package: str
    version_arg: str = "--version"
    version_regex: str = r"(\d+\.[\d\.]+\w*)"


@dataclass
class ToolStatus:
    """Runtime availability status of a tool."""

    definition: ToolDefinition
    installed: bool
    path: Path | None
    version: str | None


KNOWN_TOOLS: list[ToolDefinition] = [
    # Partition & Super image tools
    ToolDefinition(
        name="lpunpack",
        category="Partition & Super",
        description="Unpack partition images from dynamic super.img",
        required=True,
        arch_package="android-tools",
        debian_package="android-sdk-platform-tools",
    ),
    ToolDefinition(
        name="lpmake",
        category="Partition & Super",
        description="Repack partition images into dynamic super.img",
        required=True,
        arch_package="android-tools",
        debian_package="android-sdk-platform-tools",
    ),
    ToolDefinition(
        name="simg2img",
        category="Partition & Super",
        description="Convert sparse Android images to raw images",
        required=True,
        arch_package="android-tools",
        debian_package="android-sdk-libsparse-utils",
    ),
    ToolDefinition(
        name="img2simg",
        category="Partition & Super",
        description="Convert raw filesystem images to sparse images",
        required=True,
        arch_package="android-tools",
        debian_package="android-sdk-libsparse-utils",
    ),
    ToolDefinition(
        name="avbtool",
        category="Partition & Super",
        description="Android Verified Boot (AVB/vbmeta) verification tool",
        required=False,
        arch_package="android-tools",
        debian_package="android-sdk-platform-tools",
    ),
    # Ext4 filesystem tools
    ToolDefinition(
        name="mke2fs",
        category="Ext4 Filesystem",
        description="Format and create ext4 filesystem images",
        required=True,
        arch_package="e2fsprogs",
        debian_package="e2fsprogs",
        version_arg="-V",
    ),
    ToolDefinition(
        name="e2fsdroid",
        category="Ext4 Filesystem",
        description="Inject SELinux contexts and permissions into ext4 image",
        required=True,
        arch_package="e2fsprogs",
        debian_package="e2fsprogs",
        version_arg="-V",
    ),
    ToolDefinition(
        name="resize2fs",
        category="Ext4 Filesystem",
        description="Resize ext4 filesystem partitions",
        required=True,
        arch_package="e2fsprogs",
        debian_package="e2fsprogs",
        version_arg="-V",
    ),
    ToolDefinition(
        name="e2fsck",
        category="Ext4 Filesystem",
        description="Check and repair ext4 filesystem integrity",
        required=True,
        arch_package="e2fsprogs",
        debian_package="e2fsprogs",
        version_arg="-V",
    ),
    ToolDefinition(
        name="debugfs",
        category="Ext4 Filesystem",
        description="Extract files and SELinux attributes without root",
        required=False,
        arch_package="e2fsprogs",
        debian_package="e2fsprogs",
        version_arg="-V",
    ),
    # EROFS filesystem tools
    ToolDefinition(
        name="fsck.erofs",
        category="EROFS Filesystem",
        description="Extract EROFS images without root privilege",
        required=True,
        arch_package="erofs-utils",
        debian_package="erofs-utils",
        version_arg="-V",
    ),
    ToolDefinition(
        name="mkfs.erofs",
        category="EROFS Filesystem",
        description="Create compressed EROFS partition images",
        required=True,
        arch_package="erofs-utils",
        debian_package="erofs-utils",
        version_arg="-V",
    ),
    # F2FS filesystem tools
    ToolDefinition(
        name="mkfs.f2fs",
        category="F2FS Filesystem",
        description="Format F2FS filesystem partitions",
        required=False,
        arch_package="f2fs-tools",
        debian_package="f2fs-tools",
        version_arg="-V",
    ),
    ToolDefinition(
        name="extract.f2fs",
        category="F2FS Filesystem",
        description="Extract F2FS partition contents without root",
        required=False,
        arch_package="f2fs-tools",
        debian_package="f2fs-tools",
        version_arg="-V",
    ),
    ToolDefinition(
        name="sload_f2fs",
        category="F2FS Filesystem",
        description="Inject SELinux contexts into F2FS image",
        required=False,
        arch_package="f2fs-tools",
        debian_package="f2fs-tools",
        version_arg="-V",
    ),
    # Compression tools
    ToolDefinition(
        name="brotli",
        category="Compression",
        description="Decompress and compress brotli (.br) images",
        required=True,
        arch_package="brotli",
        debian_package="brotli",
    ),
    ToolDefinition(
        name="zstd",
        category="Compression",
        description="Decompress and compress Zstandard (.zst) images",
        required=True,
        arch_package="zstd",
        debian_package="zstd",
    ),
    ToolDefinition(
        name="unzip",
        category="Compression",
        description="Fast extraction of ZIP archives",
        required=True,
        arch_package="unzip",
        debian_package="unzip",
        version_arg="-v",
    ),
    # Framework & OTA tools
    ToolDefinition(
        name="java",
        category="Framework & Patch",
        description="Java Runtime Environment (JDK 17+) for APK/JAR patching",
        required=False,
        arch_package="jdk-openjdk",
        debian_package="default-jre",
    ),
    ToolDefinition(
        name="apktool",
        category="Framework & Patch",
        description="Decompile and reassemble Android APKs and JARs",
        required=False,
        arch_package="apktool",
        debian_package="apktool",
    ),
    ToolDefinition(
        name="payload-dumper-go",
        category="OTA Dumper",
        description="Extract partitions from OTA payload.bin",
        required=False,
        arch_package="payload-dumper-go",
        debian_package="payload-dumper-go",
    ),
]


def detect_distribution() -> str:
    """Detect current Linux distribution ('arch', 'debian', 'ubuntu', 'fedora', 'other')."""
    os_release = Path("/etc/os-release")
    if not os_release.is_file():
        return "other"

    try:
        content = os_release.read_text(encoding="utf-8").lower()
        if "id=arch" in content or "id_like=arch" in content:
            return "arch"
        if "id=ubuntu" in content or "id_like=ubuntu" in content:
            return "ubuntu"
        if "id=debian" in content or "id_like=debian" in content:
            return "debian"
        if "id=fedora" in content:
            return "fedora"
    except Exception:
        pass
    return "other"


def probe_tool_version(executable: Path, version_arg: str, regex: str) -> str | None:
    """Attempt to extract the version string from an executable."""
    try:
        proc = subprocess.run(
            [str(executable), version_arg],
            capture_output=True,
            text=True,
            timeout=3,
        )
        combined = (proc.stdout + " " + proc.stderr).strip()
        match = re.search(regex, combined)
        if match:
            return match.group(1)
        # If it returned usage or unrecognized option, it is still an installed binary
        if any(w in combined.lower() for w in ["unrecognized", "invalid option", "usage:"]):
            return "installed"
        first_line = combined.splitlines()[0] if combined else ""
        return first_line[:30] if first_line else "installed"
    except Exception:
        return "installed"


def check_tool(defn: ToolDefinition, custom_path: str | None = None) -> ToolStatus:
    """Check if a specific tool is installed and probe its version."""
    if custom_path:
        cand = Path(custom_path)
        if cand.is_file() and os.access(cand, os.X_OK):
            version = probe_tool_version(cand, defn.version_arg, defn.version_regex)
            return ToolStatus(definition=defn, installed=True, path=cand, version=version)

    which_path = shutil.which(defn.name)
    if which_path:
        p = Path(which_path)
        version = probe_tool_version(p, defn.version_arg, defn.version_regex)
        return ToolStatus(definition=defn, installed=True, path=p, version=version)

    return ToolStatus(definition=defn, installed=False, path=None, version=None)


def check_all_tools(tool_overrides: dict[str, str] | None = None) -> list[ToolStatus]:
    """Check all known tools against the host system."""
    overrides = tool_overrides or {}
    return [check_tool(defn, overrides.get(defn.name)) for defn in KNOWN_TOOLS]


def get_install_command(missing_tools: list[ToolDefinition], distro: str | None = None) -> str:
    """Generate distro-specific package installation commands for missing tools."""
    current_distro = distro or detect_distribution()

    if current_distro in ("arch",):
        packages = sorted({t.arch_package for t in missing_tools if t.arch_package})
        return f"sudo pacman -S {' '.join(packages)}"
    elif current_distro in ("debian", "ubuntu"):
        packages = sorted({t.debian_package for t in missing_tools if t.debian_package})
        return f"sudo apt-get update && sudo apt-get install -y {' '.join(packages)}"
    else:
        arch_pkgs = sorted({t.arch_package for t in missing_tools if t.arch_package})
        deb_pkgs = sorted({t.debian_package for t in missing_tools if t.debian_package})
        return f"Arch: sudo pacman -S {' '.join(arch_pkgs)}\nDebian/Ubuntu: sudo apt-get install {' '.join(deb_pkgs)}"


def resolve_tool_path(name: str, tool_overrides: dict[str, str] | None = None) -> Path:
    """Resolve the executable path for a tool name, or raise FileNotFoundError."""
    overrides = tool_overrides or {}
    if name in overrides:
        cand = Path(overrides[name])
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand

    which_path = shutil.which(name)
    if which_path:
        return Path(which_path)

    raise FileNotFoundError(
        f"Required native tool '{name}' was not found on this system. Run 'dna doctor' to view install hints."
    )


def run_tool(
    name: str,
    args: list[str],
    cwd: Path | None = None,
    tool_overrides: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a native tool command line securely."""
    tool_path = resolve_tool_path(name, tool_overrides)
    cmd = [str(tool_path)] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=capture_output,
        text=True,
    )
