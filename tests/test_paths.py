"""Unit tests for path management and safety."""

import tempfile
import unittest
from pathlib import Path

from dna_core.paths import (
    ProjectPaths,
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


if __name__ == "__main__":
    unittest.main()
