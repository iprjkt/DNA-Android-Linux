"""Unit tests for ROM zip extraction and integrity."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from dna_core.paths import ProjectPaths
from dna_core.project import Project
from dna_core.rom import unzip_rom


class TestRom(unittest.TestCase):
    def test_unzip_rom_standard_and_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proj_dir = root / "DNA_test_rom"
            paths = ProjectPaths(project_dir=proj_dir)
            paths.ensure_layout()
            proj = Project(paths=paths)

            # Create synthetic ROM zip
            zip_file = root / "fake_rom.zip"
            with zipfile.ZipFile(zip_file, "w") as zf:
                zf.writestr("boot.img", b"BOOT_IMAGE_DATA" * 50)
                zf.writestr("payload.bin", b"PAYLOAD_DATA" * 100)
                zf.writestr("META-INF/com/google/android/updater-script", b"# updater-script")

            # 1. Test dry-run
            dry_res = unzip_rom(zip_file, proj, dry_run=True)
            self.assertTrue(dry_res.dry_run)
            self.assertEqual(dry_res.total_files, 3)
            self.assertFalse((proj.paths.rom_dir / "boot.img").exists())

            # 2. Test actual extraction
            real_res = unzip_rom(zip_file, proj, dry_run=False, delete_source=False)
            self.assertFalse(real_res.dry_run)
            self.assertEqual(real_res.total_files, 3)
            self.assertTrue((proj.paths.rom_dir / "boot.img").is_file())
            self.assertTrue((proj.paths.rom_dir / "payload.bin").is_file())
            self.assertTrue((proj.paths.rom_dir / "META-INF/com/google/android/updater-script").is_file())
            self.assertTrue(zip_file.is_file())

            # 3. Test extraction with delete_source
            unzip_rom(zip_file, proj, dry_run=False, delete_source=True)
            self.assertFalse(zip_file.exists())

    def test_zip_slip_protection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proj_dir = root / "DNA_test_slip"
            paths = ProjectPaths(project_dir=proj_dir)
            paths.ensure_layout()
            proj = Project(paths=paths)

            # Create malicious zip with relative path traversal
            malicious_zip = root / "evil.zip"
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                zf.writestr("../evil_file.txt", b"evil content")

            with self.assertRaises(PermissionError):
                unzip_rom(malicious_zip, proj)


if __name__ == "__main__":
    unittest.main()
