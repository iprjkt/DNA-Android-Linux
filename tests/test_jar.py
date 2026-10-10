"""Unit tests for Phase 5 Jar Menu smali patching engine."""

import tempfile
import unittest
from pathlib import Path

from dna_core.jar import (
    find_services_jar,
    patch_apk_protection_smali,
    patch_disable_invoke_custom_smali,
    patch_dss_smali,
    patch_dsv_smali,
    replace_smali_method,
)


SAMPLE_WINDOW_STATE_SMALI = """
.class public Lcom/android/server/wm/WindowState;
.super Lcom/android/server/wm/WindowContainer;

# virtual methods
.method isSecureLocked()Z
    .locals 7
    .line 5000
    iget-object v0, p0, Lcom/android/server/wm/WindowState;->mAttrs:Landroid/view/WindowManager$LayoutParams;
    iget v0, v0, Landroid/view/WindowManager$LayoutParams;->flags:I
    and-int/lit16 v0, v0, 0x2000
    if-eqz v0, :cond_0
    const/4 v0, 0x1
    return v0
    :cond_0
    const/4 v0, 0x0
    return v0
.end method

.method isVisible()Z
    .locals 1
    const/4 v0, 0x1
    return v0
.end method
"""

SAMPLE_POLICY_ENFORCER_A17 = """
.class public Lcom/android/server/devicepolicy/PolicyEnforcerCallbacks;
.super Ljava/lang/Object;

.method static setScreenCaptureDisabled(Ljava/lang/Boolean;Landroid/content/Context;ILandroid/app/admin/PolicyKey;)Ljava/util/concurrent/CompletableFuture;
    .locals 1
    .param p0, "disabled"
    new-instance v0, Lcom/android/server/devicepolicy/PolicyEnforcerCallbacks$$ExternalSyntheticLambda6;
    invoke-direct {v0, p3, p0, p2}, Lcom/android/server/devicepolicy/PolicyEnforcerCallbacks$$ExternalSyntheticLambda6;-><init>(Landroid/app/admin/PolicyKey;Ljava/lang/Boolean;I)V
    invoke-static {v0}, Landroid/os/Binder;->withCleanCallingIdentity(Lcom/android/internal/util/FunctionalUtils$ThrowingSupplier;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Ljava/util/concurrent/CompletableFuture;
    return-object v0
.end method
"""

SAMPLE_PMS_UTILS_SMALI = """
.class public Lcom/android/server/pm/PackageManagerServiceUtils;
.super Ljava/lang/Object;

.method public static compareSignatures(Landroid/content/pm/SigningDetails;Landroid/content/pm/SigningDetails;)I
    .locals 6
    if-eqz p0, :cond_0
    const/4 v0, -0x3
    return v0
    :cond_0
    const/4 v0, 0x0
    return v0
.end method

.method public static compareSignatures([Landroid/content/pm/Signature;[Landroid/content/pm/Signature;)I
    .locals 2
    const/4 v0, -0x1
    return v0
.end method

.method public static verifySignatures(Lcom/android/server/pm/PackageSetting;Lcom/android/server/pm/pkg/AndroidPackage;)Z
    .locals 1
    const/4 v0, 0x0
    return v0
.end method
"""

SAMPLE_INSTALL_HELPER_SMALI = """
.class public Lcom/android/server/pm/InstallPackageHelper;
.super Ljava/lang/Object;

.method checkDowngrade(Lcom/android/server/pm/pkg/AndroidPackage;Landroid/content/pm/PackageInfoLite;)V
    .locals 2
    new-instance v0, Lcom/android/server/pm/PackageManagerException;
    const-string v1, "Downgrade not permitted"
    invoke-direct {v0, v1}, Lcom/android/server/pm/PackageManagerException;-><init>(Ljava/lang/String;)V
    throw v0
.end method
"""


class TestJarSmaliPatching(unittest.TestCase):
    def test_replace_smali_method(self):
        text, count = replace_smali_method(
            SAMPLE_WINDOW_STATE_SMALI,
            "isSecureLocked",
            "    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0",
            return_type="Z",
        )
        self.assertEqual(count, 1)
        self.assertIn("const/4 v0, 0x0\n\n    return v0", text)
        self.assertNotIn("and-int/lit16", text)
        # Verify other method is untouched
        self.assertIn(".method isVisible()Z", text)

    def test_find_services_jar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fw_dir = root / "system" / "framework"
            fw_dir.mkdir(parents=True)
            jar_file = fw_dir / "services.jar"
            jar_file.write_bytes(b"PK\x03\x04mock")

            # Direct file
            self.assertEqual(find_services_jar(jar_file), jar_file)
            # Via system directory
            self.assertEqual(find_services_jar(root), jar_file)
            # Not found
            self.assertIsNone(find_services_jar(root / "nonexistent"))

    def test_patch_dss_android17_safeguard(self):
        """Test Disable Secure Screenshot fix for Android 17 CompletableFuture crash."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # 1. WindowState
            wm_dir = root / "smali_classes4" / "com" / "android" / "server" / "wm"
            wm_dir.mkdir(parents=True)
            ws_file = wm_dir / "WindowState.smali"
            ws_file.write_text(SAMPLE_WINDOW_STATE_SMALI, encoding="utf-8")

            # 2. PolicyEnforcerCallbacks (Android 17)
            dpm_dir = root / "smali_classes2" / "com" / "android" / "server" / "devicepolicy"
            dpm_dir.mkdir(parents=True)
            pe_file = dpm_dir / "PolicyEnforcerCallbacks.smali"
            pe_file.write_text(SAMPLE_POLICY_ENFORCER_A17, encoding="utf-8")

            res = patch_dss_smali(root)
            self.assertEqual(res["methods_patched"], 2)

            # Verify WindowState returns false
            ws_content = ws_file.read_text(encoding="utf-8")
            self.assertIn(".method isSecureLocked()Z", ws_content)
            self.assertIn("const/4 v0, 0x0\n\n    return v0", ws_content)

            # Verify PolicyEnforcerCallbacks returns CompletableFuture / AndroidFuture, NOT return-void!
            pe_content = pe_file.read_text(encoding="utf-8")
            self.assertIn("AndroidFuture;->completedFuture", pe_content)
            self.assertIn("return-object v0", pe_content)
            # CRITICAL: Verify return-void is NEVER present in CompletableFuture method
            self.assertNotIn("return-void", pe_content)

    def test_patch_dsv(self):
        """Test Core Patch DSV (signature verification bypass)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pm_dir = root / "smali_classes3" / "com" / "android" / "server" / "pm"
            pm_dir.mkdir(parents=True)
            pms_file = pm_dir / "PackageManagerServiceUtils.smali"
            pms_file.write_text(SAMPLE_PMS_UTILS_SMALI, encoding="utf-8")

            res = patch_dsv_smali(root)
            self.assertGreaterEqual(res["methods_patched"], 2)

            content = pms_file.read_text(encoding="utf-8")
            # compareSignatures must return 0 (SIGNATURE_MATCH)
            self.assertIn("const/4 v0, 0x0\n\n    return v0", content)
            self.assertNotIn("-0x3", content)
            self.assertNotIn("-0x1", content)

    def test_patch_apk_protection(self):
        """Test Remove APK Protection (downgrade exception bypass)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pm_dir = root / "smali_classes3" / "com" / "android" / "server" / "pm"
            pm_dir.mkdir(parents=True)
            helper_file = pm_dir / "InstallPackageHelper.smali"
            helper_file.write_text(SAMPLE_INSTALL_HELPER_SMALI, encoding="utf-8")

            res = patch_apk_protection_smali(root)
            self.assertEqual(res["methods_patched"], 1)

            content = helper_file.read_text(encoding="utf-8")
            self.assertIn("return-void", content)
            self.assertNotIn("PackageManagerException", content)

    def test_patch_disable_invoke_custom(self):
        """Test invoke-custom instruction cleanup."""
        sample_invoke_custom = """
.class public Lcom/test/RecordClass;
.super Ljava/lang/Object;

.method public toString()Ljava/lang/String;
    .locals 2
    invoke-custom {p0}, makeConcatWithConstants()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            test_file = root / "RecordClass.smali"
            test_file.write_text(sample_invoke_custom, encoding="utf-8")

            res = patch_disable_invoke_custom_smali(root)
            self.assertEqual(res["cleaned_count"], 1)

            content = test_file.read_text(encoding="utf-8")
            self.assertNotIn("invoke-custom", content)
            self.assertIn('const-string v0, ""', content)


if __name__ == "__main__":
    unittest.main()
