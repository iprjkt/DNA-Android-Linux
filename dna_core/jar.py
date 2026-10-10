"""Android services.jar and smali bytecode patching engine.

Implements native Linux equivalents for the DNA-Android Jar Menu:
- Core Patch DSV: Disables complete package signature verification.
- Remove APK Protection: Bypasses OEM/stock package installer restrictions.
- Disable Secure Screenshot (DSS): Overrides FLAG_SECURE checks with Android 17
  CompletableFuture safety safeguards.
- Invoke-custom cleanup: Disables invoke-custom instructions in smali methods.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dna_core.tools import resolve_tool_path


def find_services_jar(target: Path | str) -> Optional[Path]:
    """Find services.jar in a file path or directory tree."""
    p = Path(target)
    if p.is_file() and p.name.lower().endswith(".jar"):
        return p

    if not p.is_dir():
        return None

    # Priority search locations
    candidates = [
        p / "services.jar",
        p / "system" / "framework" / "services.jar",
        p / "system" / "system" / "framework" / "services.jar",
        p / "framework" / "services.jar",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand

    # Recursive fallback
    for found in p.rglob("services.jar"):
        if found.is_file():
            return found

    return None


def decompile_jar(jar_path: Path | str, output_dir: Path | str) -> Path:
    """Decompile a JAR file into smali directories using apktool."""
    jar = Path(jar_path)
    out = Path(output_dir)
    if not jar.is_file():
        raise FileNotFoundError(f"JAR file not found: {jar}")

    apktool_bin = resolve_tool_path("apktool")
    cmd = [apktool_bin, "d", str(jar), "-o", str(out), "-f"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"apktool decompilation failed: {res.stderr or res.stdout}")

    return out


def recompile_jar(decompiled_dir: Path | str, output_jar: Path | str) -> Path:
    """Recompile a smali tree into a JAR file using apktool."""
    decomp = Path(decompiled_dir)
    out_j = Path(output_jar)
    if not decomp.is_dir():
        raise FileNotFoundError(f"Decompiled directory not found: {decomp}")

    apktool_bin = resolve_tool_path("apktool")
    out_j.parent.mkdir(parents=True, exist_ok=True)
    cmd = [apktool_bin, "b", str(decomp), "-o", str(out_j)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"apktool compilation failed: {res.stderr or res.stdout}")

    return out_j


def replace_smali_method(
    smali_text: str,
    method_name: str,
    new_body: str,
    return_type: Optional[str] = None,
    param_pattern: Optional[str] = None,
) -> Tuple[str, int]:
    """Replace the body of a smali method matching name, params, and return type."""
    ret_part = rf"[^\n]*{re.escape(return_type)}" if return_type else r"[^\n]*"
    param_part = rf"\({param_pattern}\)" if param_pattern else r"\([^\n]*\)"

    pattern = (
        rf"(^[ \t]*\.method[^\n]*\b{re.escape(method_name)}{param_part}{ret_part}[ \t]*\n)"
        r"(.*?)"
        r"(^[ \t]*\.end method)"
    )

    def repl(m: re.Match) -> str:
        header = m.group(1)
        end = m.group(3)
        body = new_body.strip("\n")
        return f"{header}\n{body}\n{end}"

    new_text, count = re.subn(pattern, repl, smali_text, flags=re.DOTALL | re.MULTILINE)
    return new_text, count


def patch_dsv_smali(smali_root: Path | str) -> Dict[str, Any]:
    """Patch signature verification methods in decompiled smali tree.

    Patches:
    - PackageManagerServiceUtils.compareSignatures(...) -> return 0 (SIGNATURE_MATCH)
    - SigningDetails.checkCapability(...) -> return true
    - SigningDetails.hasAncestorOrSelf(...) -> return true
    """
    root = Path(smali_root)
    modified_files: List[str] = []
    total_methods_patched = 0

    # 1. Target: PackageManagerServiceUtils.smali
    for smali_file in root.rglob("PackageManagerServiceUtils.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        changed = False

        # compareSignatures(SigningDetails, SigningDetails)I
        content, c1 = replace_smali_method(
            content,
            "compareSignatures",
            "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0",
            return_type="I",
            param_pattern=r"Landroid/content/pm/SigningDetails;Landroid/content/pm/SigningDetails;",
        )
        if c1:
            total_methods_patched += c1
            changed = True

        # compareSignatures([Signature;, [Signature;)I
        content, c2 = replace_smali_method(
            content,
            "compareSignatures",
            "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0",
            return_type="I",
            param_pattern=r"\[Landroid/content/pm/Signature;\[Landroid/content/pm/Signature;",
        )
        if c2:
            total_methods_patched += c2
            changed = True

        # verifySignatures(...)
        content, c3 = replace_smali_method(
            content,
            "verifySignatures",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c3:
            total_methods_patched += c3
            changed = True

        if changed:
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    # 2. Target: SigningDetails.smali
    for smali_file in root.rglob("SigningDetails.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        changed = False

        content, c1 = replace_smali_method(
            content,
            "checkCapability",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c1:
            total_methods_patched += c1
            changed = True

        content, c2 = replace_smali_method(
            content,
            "hasAncestorOrSelf",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c2:
            total_methods_patched += c2
            changed = True

        if changed:
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    # 3. Target: KeySetManagerService.smali
    for smali_file in root.rglob("KeySetManagerService.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        content, c1 = replace_smali_method(
            content,
            "checkSigningKeySetLocked",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c1:
            total_methods_patched += c1
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    return {
        "patch": "core-patch-dsv",
        "modified_files": modified_files,
        "methods_patched": total_methods_patched,
    }


def patch_apk_protection_smali(smali_root: Path | str) -> Dict[str, Any]:
    """Patch package installation downgrade and OEM security verification checks."""
    root = Path(smali_root)
    modified_files: List[str] = []
    total_methods_patched = 0

    # 1. Target: InstallPackageHelper.smali (checkDowngrade)
    for smali_file in root.rglob("InstallPackageHelper.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        changed = False

        # checkDowngrade(...) -> return-void (bypass downgrade exception)
        content, c1 = replace_smali_method(
            content,
            "checkDowngrade",
            "    .locals 0\n\n    return-void",
            return_type="V",
        )
        if c1:
            total_methods_patched += c1
            changed = True

        if changed:
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    # 2. Target: ScanPackageUtils.smali (assertPackageIsValid)
    for smali_file in root.rglob("ScanPackageUtils.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        content, c1 = replace_smali_method(
            content,
            "assertPackageIsValid",
            "    .locals 0\n\n    return-void",
            return_type="V",
        )
        if c1:
            total_methods_patched += c1
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    # 3. Target: MiuiPackageInstallHelper / PackageInstallerSession (if OEM present)
    for smali_file in root.rglob("*PackageInstall*.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        changed = False

        content, c1 = replace_smali_method(
            content,
            "checkApkInstall",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c1:
            total_methods_patched += c1
            changed = True

        if changed:
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    return {
        "patch": "remove-apk-protection",
        "modified_files": modified_files,
        "methods_patched": total_methods_patched,
    }


def patch_dss_smali(smali_root: Path | str) -> Dict[str, Any]:
    """Disable secure screenshots with Android 17 CompletableFuture safety fix.

    Patches:
    1. WindowState.smali: isSecureLocked()Z -> return 0 (false)
    2. PolicyEnforcerCallbacks.smali: setScreenCaptureDisabled(...) ->
       If returns CompletableFuture: return AndroidFuture.completedFuture(Boolean.TRUE)
       If returns void: return-void
    """
    root = Path(smali_root)
    modified_files: List[str] = []
    total_methods_patched = 0

    # 1. Target: WindowState.smali -> isSecureLocked()Z
    for smali_file in root.rglob("WindowState.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        content, c = replace_smali_method(
            content,
            "isSecureLocked",
            "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0",
            return_type="Z",
        )
        if c:
            total_methods_patched += c
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    # 2. Target: PolicyEnforcerCallbacks.smali -> setScreenCaptureDisabled
    for smali_file in root.rglob("PolicyEnforcerCallbacks.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")

        # Check declared return type of setScreenCaptureDisabled
        # Android 14/15/16/17 returns CompletableFuture
        if re.search(r"\.method[^\n]*\bsetScreenCaptureDisabled\([^\n]*\)[^\n]*CompletableFuture", content):
            new_future_body = (
                "    .locals 1\n\n"
                "    const/4 v0, 0x1\n\n"
                "    invoke-static {v0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;\n\n"
                "    move-result-object v0\n\n"
                "    invoke-static {v0}, Lcom/android/internal/infra/AndroidFuture;->completedFuture(Ljava/lang/Object;)Lcom/android/internal/infra/AndroidFuture;\n\n"
                "    move-result-object v0\n\n"
                "    return-object v0"
            )
            content, c = replace_smali_method(
                content,
                "setScreenCaptureDisabled",
                new_future_body,
                return_type="Ljava/util/concurrent/CompletableFuture;",
            )
            if c:
                total_methods_patched += c
                smali_file.write_text(content, encoding="utf-8")
                modified_files.append(str(smali_file))
        elif re.search(r"\.method[^\n]*\bsetScreenCaptureDisabled\([^\n]*\)V", content):
            content, c = replace_smali_method(
                content,
                "setScreenCaptureDisabled",
                "    .locals 0\n\n    return-void",
                return_type="V",
            )
            if c:
                total_methods_patched += c
                smali_file.write_text(content, encoding="utf-8")
                modified_files.append(str(smali_file))

    # 3. Target: DevicePolicyCacheImpl.smali (isScreenCaptureAllowed -> return true)
    for smali_file in root.rglob("DevicePolicyCache*.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        content, c = replace_smali_method(
            content,
            "isScreenCaptureAllowed",
            "    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0",
            return_type="Z",
        )
        if c:
            total_methods_patched += c
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    return {
        "patch": "disable-secure-screenshot",
        "modified_files": modified_files,
        "methods_patched": total_methods_patched,
    }


def patch_disable_invoke_custom_smali(smali_root: Path | str) -> Dict[str, Any]:
    """Clean up invoke-custom instructions in equals, hashCode, and toString smali methods."""
    root = Path(smali_root)
    modified_files: List[str] = []
    total_cleaned = 0

    invoke_pattern = re.compile(r"^[ \t]*invoke-custom[^\n]*\n(?:[ \t]*move-result[^\n]*\n)?", re.MULTILINE)

    for smali_file in root.rglob("*.smali"):
        content = smali_file.read_text(encoding="utf-8", errors="replace")
        if "invoke-custom" not in content:
            continue

        changed = False
        # Remove invoke-custom in toString
        if re.search(r"\.method[^\n]*\btoString\(\)Ljava/lang/String;", content):
            content, c = replace_smali_method(
                content,
                "toString",
                "    .locals 1\n\n    const-string v0, \"\"\n\n    return-object v0",
                return_type="Ljava/lang/String;",
            )
            if c:
                total_cleaned += c
                changed = True

        # Remove invoke-custom in hashCode
        if re.search(r"\.method[^\n]*\bhashCode\(\)I", content):
            content, c = replace_smali_method(
                content,
                "hashCode",
                "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0",
                return_type="I",
            )
            if c:
                total_cleaned += c
                changed = True

        if changed:
            smali_file.write_text(content, encoding="utf-8")
            modified_files.append(str(smali_file))

    return {
        "patch": "disable-invoke-custom",
        "modified_files": modified_files,
        "cleaned_count": total_cleaned,
    }


def patch_services_jar(
    jar_path: Path | str,
    output_jar: Optional[Path | str] = None,
    patch_dsv: bool = False,
    patch_apk_protection: bool = False,
    patch_dss: bool = False,
    disable_invoke_custom: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute complete JAR decompile -> patch -> recompile pipeline."""
    target_jar = Path(jar_path)
    if not target_jar.is_file():
        raise FileNotFoundError(f"Target JAR file not found: {target_jar}")

    dest_jar = Path(output_jar) if output_jar is not None else target_jar

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td) / "decompiled"
        decompile_jar(target_jar, work_dir)

        patch_results = []

        if patch_dsv:
            res_dsv = patch_dsv_smali(work_dir)
            patch_results.append(res_dsv)

        if patch_apk_protection:
            res_prot = patch_apk_protection_smali(work_dir)
            patch_results.append(res_prot)

        if patch_dss:
            res_dss = patch_dss_smali(work_dir)
            patch_results.append(res_dss)

        if disable_invoke_custom:
            res_ic = patch_disable_invoke_custom_smali(work_dir)
            patch_results.append(res_ic)

        if not dry_run:
            # Backup original jar if updating in-place
            if dest_jar == target_jar:
                bak_path = target_jar.with_name(f"{target_jar.name}.bak")
                if not bak_path.exists():
                    shutil.copyfile(target_jar, bak_path)

            recompile_jar(work_dir, dest_jar)

    return {
        "jar_path": str(target_jar),
        "output_jar": str(dest_jar),
        "patches_applied": patch_results,
        "dry_run": dry_run,
    }


def patch_core_patch_dsv(
    jar_path: Path | str,
    output_jar: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply Core Patch DSV (bypass signature verification) to services.jar."""
    return patch_services_jar(jar_path, output_jar=output_jar, patch_dsv=True, dry_run=dry_run)


def patch_remove_apk_protection(
    jar_path: Path | str,
    output_jar: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply Remove APK Protection to services.jar."""
    return patch_services_jar(jar_path, output_jar=output_jar, patch_apk_protection=True, dry_run=dry_run)


def patch_disable_secure_screenshot(
    jar_path: Path | str,
    output_jar: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply Disable Secure Screenshot (with Android 17 CompletableFuture fix) to services.jar."""
    return patch_services_jar(jar_path, output_jar=output_jar, patch_dss=True, dry_run=dry_run)

