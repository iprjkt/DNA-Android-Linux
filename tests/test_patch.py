"""Unit tests for Phase 4 Patch Menu engine."""

import struct
import tempfile
import unittest
from pathlib import Path

from dna_core.patch import (
    AVB_FLAG_HASHTREE_DISABLED,
    AVB_FLAG_VERIFICATION_DISABLED,
    AVB_MAGIC,
    patch_disable_ota,
    patch_disable_xiaomi_services,
    patch_integrity_fix,
    patch_privapp_permissions,
    patch_safetycore,
    patch_vbmeta,
)
from dna_core.prop import PropFile


def create_mock_vbmeta(path: Path, flags: int = 0) -> Path:
    """Create a minimal 256-byte mock AVB vbmeta image."""
    data = bytearray(256)
    data[:4] = AVB_MAGIC
    # Write big-endian flags at offset 120
    data[120:124] = struct.pack(">I", flags)
    path.write_bytes(bytes(data))
    return path


class TestPatchVBMeta(unittest.TestCase):
    def test_patch_vbmeta_modes(self):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "vbmeta.img"
            create_mock_vbmeta(img, flags=0)

            # 1. Patch verity (flag bit 0 = 1)
            res1 = patch_vbmeta(img, mode="verity")
            self.assertEqual(res1["old_flags"], 0)
            self.assertEqual(res1["new_flags"], AVB_FLAG_HASHTREE_DISABLED)
            self.assertTrue(res1["modified"])

            # Verify in file
            flags_read = struct.unpack(">I", img.read_bytes()[120:124])[0]
            self.assertEqual(flags_read, 1)

            # 2. Patch verification (flag bit 1 = 2)
            res2 = patch_vbmeta(img, mode="verification")
            self.assertEqual(res2["new_flags"], 1 | 2)

            # 3. Patch both
            create_mock_vbmeta(img, flags=0)
            res3 = patch_vbmeta(img, mode="both")
            self.assertEqual(res3["new_flags"], 3)
            flags_read = struct.unpack(">I", img.read_bytes()[120:124])[0]
            self.assertEqual(flags_read, 3)

            # 4. Patch enable (restore 0)
            res4 = patch_vbmeta(img, mode="enable")
            self.assertEqual(res4["new_flags"], 0)
            flags_read = struct.unpack(">I", img.read_bytes()[120:124])[0]
            self.assertEqual(flags_read, 0)

    def test_patch_vbmeta_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "vbmeta.img"
            create_mock_vbmeta(img, flags=0)

            res = patch_vbmeta(img, mode="both", dry_run=True)
            self.assertEqual(res["new_flags"], 3)
            self.assertTrue(res["dry_run"])

            # File must remain untouched
            flags_read = struct.unpack(">I", img.read_bytes()[120:124])[0]
            self.assertEqual(flags_read, 0)

    def test_patch_vbmeta_invalid_magic(self):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "invalid.img"
            img.write_bytes(b"NOT_AVB" + b"\x00" * 200)

            with self.assertRaises(ValueError):
                patch_vbmeta(img, mode="both")

    def test_patch_vbmeta_not_found(self):
        with self.assertRaises(FileNotFoundError):
            patch_vbmeta(Path("/non/existent/vbmeta.img"), mode="both")


class TestPatchIntegrityFix(unittest.TestCase):
    def test_integrity_fix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sys_dir = root / "system"
            sys_dir.mkdir()
            (sys_dir / "build.prop").write_text(
                "ro.build.fingerprint=old/fingerprint/here\nro.product.model=OldModel\n",
                encoding="utf-8",
            )

            res = patch_integrity_fix(root)
            self.assertEqual(len(res["modified_files"]), 1)

            # Verify modified properties
            prop = PropFile.load(sys_dir / "build.prop")
            self.assertIn("cheetah", prop.get("ro.build.fingerprint"))
            self.assertEqual(prop.get("ro.product.model"), "Pixel 7 Pro")

    def test_integrity_fix_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sys_dir = root / "system"
            sys_dir.mkdir()
            (sys_dir / "build.prop").write_text(
                "ro.build.fingerprint=old_fp\n",
                encoding="utf-8",
            )

            res = patch_integrity_fix(root, dry_run=True)
            self.assertEqual(len(res["modified_files"]), 1)

            # File not changed
            prop = PropFile.load(sys_dir / "build.prop")
            self.assertEqual(prop.get("ro.build.fingerprint"), "old_fp")


class TestPatchSafetycore(unittest.TestCase):
    def test_safetycore_injection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "product" / "app").mkdir(parents=True)

            res = patch_safetycore(root)
            dest = Path(res["destination"])
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.name, "Safetycore.apk")
            self.assertEqual(dest.parent.name, "Safetycore")

    def test_safetycore_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "product" / "app").mkdir(parents=True)

            res = patch_safetycore(root, dry_run=True)
            dest = Path(res["destination"])
            self.assertFalse(dest.exists())


class TestPatchPrivappPermissions(unittest.TestCase):
    def test_remove_privapp_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vdir = root / "vendor"
            vdir.mkdir()
            (vdir / "build.prop").write_text(
                "# Header\nro.control_privapp_permissions=enforce\nro.vendor.test=1\n",
                encoding="utf-8",
            )

            res = patch_privapp_permissions(root)
            self.assertEqual(len(res["modified_files"]), 1)

            prop = PropFile.load(vdir / "build.prop")
            self.assertFalse(prop.has_key("ro.control_privapp_permissions"))
            self.assertTrue(prop.has_key("ro.vendor.test"))

    def test_remove_privapp_permissions_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vdir = root / "vendor"
            vdir.mkdir()
            (vdir / "build.prop").write_text(
                "ro.control_privapp_permissions=enforce\n",
                encoding="utf-8",
            )

            res = patch_privapp_permissions(root, dry_run=True)
            self.assertEqual(len(res["modified_files"]), 1)

            prop = PropFile.load(vdir / "build.prop")
            self.assertTrue(prop.has_key("ro.control_privapp_permissions"))


class TestPatchDisableOTA(unittest.TestCase):
    def test_disable_ota_xml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fdir = root / "product" / "etc" / "device_features"
            fdir.mkdir(parents=True)
            xml_file = fdir / "device.xml"
            xml_file.write_text(
                '<features>\n    <bool name="support_ota_validate">true</bool>\n</features>',
                encoding="utf-8",
            )

            res = patch_disable_ota(root)
            self.assertEqual(res["count"], 1)

            content = xml_file.read_text(encoding="utf-8")
            self.assertIn('<bool name="support_ota_validate">false</bool>', content)

    def test_disable_ota_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fdir = root / "product" / "etc" / "device_features"
            fdir.mkdir(parents=True)
            xml_file = fdir / "device.xml"
            xml_file.write_text(
                '<bool name="support_ota_validate">true</bool>',
                encoding="utf-8",
            )

            res = patch_disable_ota(root, dry_run=True)
            self.assertEqual(res["count"], 1)

            content = xml_file.read_text(encoding="utf-8")
            self.assertIn("true", content)


class TestPatchDisableXiaomiServices(unittest.TestCase):
    def test_disable_services(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv1 = root / "product" / "priv-app" / "MIUIAnalytics"
            srv1.mkdir(parents=True)
            (srv1 / "MIUIAnalytics.apk").write_bytes(b"A" * 1024)

            srv2 = root / "product" / "app" / "Joyose"
            srv2.mkdir(parents=True)
            (srv2 / "Joyose.apk").write_bytes(b"B" * 2048)

            res = patch_disable_xiaomi_services(root)
            self.assertEqual(res["total_removed"], 2)
            self.assertEqual(res["total_freed_bytes"], 3072)
            self.assertFalse(srv1.exists())
            self.assertFalse(srv2.exists())

    def test_disable_services_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv = root / "product" / "priv-app" / "MIUIAnalytics"
            srv.mkdir(parents=True)
            (srv / "test.apk").write_bytes(b"A" * 1024)

            res = patch_disable_xiaomi_services(root, dry_run=True)
            self.assertEqual(res["total_removed"], 1)
            self.assertTrue(srv.exists())


if __name__ == "__main__":
    unittest.main()
