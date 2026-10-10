"""Unit tests for remove-oat, make-rw, and decrypt ROM tweaks."""

import tempfile
import unittest
from pathlib import Path

from dna_core.rom_tweaks import (
    decrypt_rom,
    make_rom_rw,
    remove_oat_directories,
)


class TestRomTweaks(unittest.TestCase):
    def test_remove_oat_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            oat1 = root / "system" / "app" / "Calculator" / "oat" / "arm64"
            oat1.mkdir(parents=True)
            (oat1 / "Calculator.odex").write_bytes(b"ODEX_DATA" * 50)

            oat2 = root / "system" / "framework" / "oat"
            oat2.mkdir(parents=True)
            (oat2 / "boot.art").write_bytes(b"BOOT_ART" * 50)

            # 1. Dry run
            removed_dry, freed_dry = remove_oat_directories(root, dry_run=True)
            self.assertEqual(len(removed_dry), 2)
            self.assertGreater(freed_dry, 0)
            self.assertTrue(oat1.exists())

            # 2. Actual run
            removed, freed = remove_oat_directories(root, dry_run=False)
            self.assertEqual(len(removed), 2)
            self.assertFalse((root / "system" / "app" / "Calculator" / "oat").exists())
            self.assertFalse(oat2.exists())

    def test_make_rom_rw(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fstab_dir = root / "vendor" / "etc"
            fstab_dir.mkdir(parents=True)
            fstab = fstab_dir / "fstab.qcom"

            fstab_content = (
                "/dev/block/by-name/boot /boot emmc defaults defaults\n"
                "overlay /system/app/MiuiCamera overlay defaults defaults\n"
                "/dev/block/by-name/userdata /data f2fs defaults defaults\n"
            )
            fstab.write_text(fstab_content, encoding="utf-8")

            init_dir = root / "mi_ext" / "etc" / "init"
            init_dir.mkdir(parents=True)
            init_rc = init_dir / "init.miui.mi_ext.rc"
            init_rc.write_text("on post-fs-data\n    mount overlay ...", encoding="utf-8")

            res = make_rom_rw(root, dry_run=False)
            self.assertEqual(len(res.fstab_files_modified), 1)
            self.assertEqual(res.overlay_lines_removed, 1)
            self.assertEqual(len(res.init_scripts_removed), 1)

            new_fstab = fstab.read_text(encoding="utf-8")
            self.assertNotIn("overlay /system/app/MiuiCamera", new_fstab)
            self.assertIn("/dev/block/by-name/boot", new_fstab)
            self.assertFalse(init_rc.exists())

    def test_decrypt_rom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fstab_dir = root / "vendor" / "etc"
            fstab_dir.mkdir(parents=True)
            fstab = fstab_dir / "fstab.qcom"

            fstab_content = (
                "/dev/block/by-name/userdata /data f2fs noatime,nosuid fileencryption=aes-256-xts:aes-256-cts:v2,keydirectory=/data/unencrypted/key\n"
            )
            fstab.write_text(fstab_content, encoding="utf-8")

            res = decrypt_rom(root, dry_run=False)
            self.assertEqual(len(res.fstab_files_modified), 1)
            self.assertEqual(res.lines_modified, 1)

            updated = fstab.read_text(encoding="utf-8")
            self.assertNotIn("fileencryption=", updated)
            self.assertIn("fileencryptable", updated)


if __name__ == "__main__":
    unittest.main()
