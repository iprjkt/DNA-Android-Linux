"""Unit tests for path management and safety."""

import os
import tempfile
import unittest
from pathlib import Path

from dna_core.paths import (
    ProjectPaths,
    get_default_io_root,
    get_default_work_root,
    get_default_workspace_root,
    get_global_config_dir,
    normalize_project_name,
)


class TestPaths(unittest.TestCase):
    def test_normalize_project_name(self):
        self.assertEqual(normalize_project_name("my_rom"), "my_rom")
        self.assertEqual(normalize_project_name("DNA_my_rom"), "my_rom")
        self.assertEqual(normalize_project_name("HyperOS-2.0"), "HyperOS-2.0")

        with self.assertRaises(ValueError):
            normalize_project_name("")

        with self.assertRaises(ValueError):
            normalize_project_name("project/with/slashes")

        with self.assertRaises(ValueError):
            normalize_project_name("bad name with spaces")

    def test_project_paths_layout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proj_paths = ProjectPaths.from_name("test_proj", root_dir=root)

            self.assertEqual(proj_paths.project_name, "test_proj")
            self.assertEqual(proj_paths.project_dir, root / "DNA_test_proj")
            self.assertEqual(proj_paths.rom_dir, root / "DNA_test_proj" / "rom")
            self.assertEqual(proj_paths.images_dir, root / "DNA_test_proj" / "images")
            self.assertEqual(proj_paths.unpacked_dir, root / "DNA_test_proj" / "unpacked")
            self.assertEqual(proj_paths.config_dir, root / "DNA_test_proj" / "config")
            self.assertEqual(proj_paths.out_dir, root / "DNA_test_proj" / "out")
            self.assertEqual(proj_paths.logs_dir, root / "DNA_test_proj" / "logs")

            # Test ensure_layout
            proj_paths.ensure_layout()
            self.assertTrue(proj_paths.rom_dir.is_dir())
            self.assertTrue(proj_paths.images_dir.is_dir())
            self.assertTrue(proj_paths.unpacked_dir.is_dir())
            self.assertTrue(proj_paths.config_dir.is_dir())
            self.assertTrue(proj_paths.out_dir.is_dir())
            self.assertTrue(proj_paths.logs_dir.is_dir())

    def test_safe_subpath_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proj_paths = ProjectPaths.from_name("test_proj", root_dir=root)
            proj_paths.ensure_layout()

            # Valid subpaths
            valid_file = proj_paths.rom_dir / "system.img"
            self.assertTrue(proj_paths.is_safe_subpath(valid_file))
            self.assertEqual(proj_paths.validate_safe_subpath(valid_file), valid_file.resolve())

            # Path traversal attempt outside project
            unsafe_file = root / "evil.txt"
            self.assertFalse(proj_paths.is_safe_subpath(unsafe_file))
            with self.assertRaises(PermissionError):
                proj_paths.validate_safe_subpath(unsafe_file)

    def test_split_io_and_work_paths(self):
        with tempfile.TemporaryDirectory() as tmp_io, tempfile.TemporaryDirectory() as tmp_work:
            io_root = Path(tmp_io)
            work_root = Path(tmp_work)

            proj = ProjectPaths.from_name("custom_rom", io_root=io_root, work_root=work_root)

            self.assertEqual(proj.project_name, "custom_rom")
            self.assertEqual(proj.io_dir, io_root / "DNA_custom_rom")
            self.assertEqual(proj.work_dir, work_root / "DNA_custom_rom")
            self.assertEqual(proj.out_dir, io_root / "DNA_custom_rom" / "out")
            self.assertEqual(proj.config_dir, work_root / "DNA_custom_rom" / "config")
            # In split layout, partitions are directly inside work_dir (MT Manager layout)
            self.assertEqual(proj.unpacked_dir, work_root / "DNA_custom_rom")

            proj.ensure_layout()

            self.assertTrue(proj.io_dir.is_dir())
            self.assertTrue(proj.out_dir.is_dir())
            self.assertTrue(proj.work_dir.is_dir())
            self.assertTrue(proj.config_dir.is_dir())
            self.assertTrue(proj.plugins_dir.is_dir())
            self.assertTrue(proj.logs_dir.is_dir())

            # Subpaths safety in both io_dir and work_dir
            io_file = proj.out_dir / "super.img"
            work_file = proj.work_dir / "product" / "build.prop"
            self.assertTrue(proj.is_safe_subpath(io_file))
            self.assertTrue(proj.is_safe_subpath(work_file))

            outside_file = io_root / "outside.txt"
            self.assertFalse(proj.is_safe_subpath(outside_file))

    def test_default_roots_environment_override(self):
        with tempfile.TemporaryDirectory() as tmp_io, tempfile.TemporaryDirectory() as tmp_work:
            old_io = os.environ.get("DNA_IO_ROOT")
            old_work = os.environ.get("DNA_WORK_ROOT")
            try:
                os.environ["DNA_IO_ROOT"] = tmp_io
                os.environ["DNA_WORK_ROOT"] = tmp_work
                self.assertEqual(get_default_io_root(), Path(tmp_io).resolve())
                self.assertEqual(get_default_work_root(), Path(tmp_work).resolve())
            finally:
                if old_io is not None:
                    os.environ["DNA_IO_ROOT"] = old_io
                else:
                    os.environ.pop("DNA_IO_ROOT", None)
                if old_work is not None:
                    os.environ["DNA_WORK_ROOT"] = old_work
                else:
                    os.environ.pop("DNA_WORK_ROOT", None)


if __name__ == "__main__":
    unittest.main()
