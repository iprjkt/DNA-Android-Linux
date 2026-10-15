"""Setup mode and external dependency installer for DNA-Linux.

Manages optional heavy/external tools that are not bundled directly into the base package:
  - java (OpenJDK Runtime Environment)
  - apktool (APK/JAR bytecode decompiler and recompiler)
  - payload-dumper-go (OTA payload.bin extractor)
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Callable

from dna_core.tools import (
    check_tool,
    detect_distribution,
    get_external_tools_dir,
    KNOWN_TOOLS,
)

APKTOOL_URL = "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar"
APKTOOL_FALLBACK_URL = "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.10.0.jar"

PAYLOAD_DUMPER_URL = "https://github.com/ssut/payload-dumper-go/releases/download/2.1.0/payload-dumper-go_2.1.0_linux_amd64.tar.gz"
PAYLOAD_DUMPER_FALLBACK_URL = "https://github.com/ssut/payload-dumper-go/releases/download/1.2.2/payload-dumper-go_1.2.2_linux_amd64.tar.gz"


def _log(callback: Callable[[str], None] | None, msg: str) -> None:
    if callback:
        callback(msg)
    else:
        print(msg)


def _download_file(url: str, dest: Path, fallback_url: str | None = None) -> None:
    """Download a file over HTTP/HTTPS with an optional fallback URL."""
    headers = {"User-Agent": "DNA-Linux-Setup/1.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as out_f:
            shutil.copyfileobj(resp, out_f)
    except Exception as e:
        if fallback_url:
            fb_req = urllib.request.Request(fallback_url, headers=headers)
            with urllib.request.urlopen(fb_req, timeout=30) as resp, open(dest, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)
        else:
            raise e


def get_setup_tools_status() -> dict[str, dict[str, Any]]:
    """Return runtime installation and availability status for external setup tools."""
    results: dict[str, dict[str, Any]] = {}
    setup_names = {"java", "apktool", "payload-dumper-go"}

    for defn in KNOWN_TOOLS:
        if defn.name in setup_names:
            status = check_tool(defn)
            results[defn.name] = {
                "name": defn.name,
                "description": defn.description,
                "installed": status.installed,
                "source": status.source,
                "path": str(status.path) if status.path else None,
                "version": status.version,
                "category": defn.category,
            }

    return results


def install_apktool(callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Download and configure apktool in the external tools directory."""
    ext_dir = get_external_tools_dir()
    jar_path = ext_dir / "apktool.jar"
    wrapper_path = ext_dir / "apktool"

    _log(callback, f">> Downloading apktool from {APKTOOL_URL}...")
    try:
        _download_file(APKTOOL_URL, jar_path, fallback_url=APKTOOL_FALLBACK_URL)
    except Exception as e:
        return False, f"Failed to download apktool: {e}"

    _log(callback, ">> Generating apktool executable launcher...")
    wrapper_content = (
        "#!/usr/bin/env bash\n"
        "DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
        "exec java -jar \"${DIR}/apktool.jar\" \"$@\"\n"
    )
    wrapper_path.write_text(wrapper_content, encoding="utf-8")
    wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Verify execution
    try:
        proc = subprocess.run([str(wrapper_path), "--version"], capture_output=True, text=True, timeout=5)
        ver = proc.stdout.strip() or proc.stderr.strip() or "installed"
        _log(callback, f"✓ apktool installed successfully ({ver}) at {wrapper_path}")
        return True, f"Installed apktool ({ver}) to {wrapper_path}"
    except Exception:
        # If java is not installed yet, wrapper is still valid
        _log(callback, f"✓ apktool binary ready at {wrapper_path} (requires Java to run)")
        return True, f"apktool ready at {wrapper_path}"


def install_payload_dumper_go(callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Download and extract payload-dumper-go into external tools directory."""
    ext_dir = get_external_tools_dir()
    tar_path = ext_dir / "payload-dumper-go.tar.gz"
    bin_path = ext_dir / "payload-dumper-go"

    _log(callback, f">> Downloading payload-dumper-go from {PAYLOAD_DUMPER_URL}...")
    try:
        _download_file(PAYLOAD_DUMPER_URL, tar_path, fallback_url=PAYLOAD_DUMPER_FALLBACK_URL)
    except Exception as e:
        return False, f"Failed to download payload-dumper-go: {e}"

    _log(callback, ">> Extracting payload-dumper-go binary...")
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("payload-dumper-go") or member.name == "payload-dumper-go":
                    extracted = tar.extractfile(member)
                    if extracted:
                        with open(bin_path, "wb") as f_out:
                            shutil.copyfileobj(extracted, f_out)
                        break
        if tar_path.exists():
            tar_path.unlink()
    except Exception as e:
        return False, f"Failed to extract payload-dumper-go: {e}"

    if not bin_path.exists():
        return False, "Extraction failed: payload-dumper-go binary not found in archive"

    bin_path.chmod(bin_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    try:
        proc = subprocess.run([str(bin_path), "--version"], capture_output=True, text=True, timeout=5)
        ver = proc.stdout.strip() or "installed"
        _log(callback, f"✓ payload-dumper-go installed successfully ({ver}) at {bin_path}")
        return True, f"Installed payload-dumper-go ({ver}) to {bin_path}"
    except Exception:
        _log(callback, f"✓ payload-dumper-go installed at {bin_path}")
        return True, f"Installed payload-dumper-go to {bin_path}"


def install_java(interactive: bool = False, callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Check or trigger host system package manager installation for Java."""
    java_which = shutil.which("java")
    if java_which:
        try:
            proc = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
            ver = proc.stderr.splitlines()[0] if proc.stderr else "installed"
            return True, f"Java is already available: {java_which} ({ver})"
        except Exception:
            return True, f"Java is already available: {java_which}"

    distro = detect_distribution()
    if distro == "arch":
        cmd = "sudo pacman -S --noconfirm jdk-openjdk"
    elif distro in ("debian", "ubuntu"):
        cmd = "sudo apt-get update && sudo apt-get install -y default-jre"
    elif distro == "fedora":
        cmd = "sudo dnf install -y java-latest-openjdk"
    else:
        cmd = "Install OpenJDK (JRE 17+) using your distribution's package manager."

    if interactive and os.geteuid() == 0:
        _log(callback, f">> Running package manager to install Java ({cmd})...")
        try:
            subprocess.run(cmd, shell=True, check=True)
            return True, "Java installed successfully via package manager."
        except Exception as e:
            return False, f"Failed to run package manager: {e}"

    _log(callback, f"! Java is required for apktool. Run the following command to install:\n  {cmd}")
    return False, f"Java not installed. Run: {cmd}"


def setup_all(callback: Callable[[str], None] | None = None) -> dict[str, tuple[bool, str]]:
    """Execute setup for all external tools."""
    results: dict[str, tuple[bool, str]] = {}

    _log(callback, "=== DNA-Linux Setup Mode: Configuring External Tools ===")

    # 1. Java check/instructions
    results["java"] = install_java(interactive=False, callback=callback)

    # 2. apktool download & wrapper
    results["apktool"] = install_apktool(callback=callback)

    # 3. payload-dumper-go download & extraction
    results["payload-dumper-go"] = install_payload_dumper_go(callback=callback)

    _log(callback, "=== Setup Mode Completed ===")
    return results
