"""Unit tests for configuration manager."""

import tempfile
import unittest
from pathlib import Path

from dna_core.config import GlobalConfig, get_active_project_path


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = GlobalConfig()
        self.assertIsNotNone(cfg.workspace_root)
        self.assertIsNone(cfg.active_project)
        self.assertFalse(cfg.auto_confirm)
        self.assertFalse(cfg.verbose)

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "config.toml"
            cfg = GlobalConfig(
                workspace_root="/tmp/dna_test_root",
                active_project="my_project",
                auto_confirm=True,
                verbose=True,
                background_image="/tmp/wallpaper.jpg",
                tool_overrides={"mke2fs": "/custom/bin/mke2fs"},
            )
            saved_path = cfg.save(cfg_file)
            self.assertEqual(saved_path, cfg_file)
            self.assertTrue(cfg_file.is_file())

            loaded = GlobalConfig.load(cfg_file)
            self.assertEqual(loaded.workspace_root, "/tmp/dna_test_root")
            self.assertEqual(loaded.active_project, "my_project")
            self.assertTrue(loaded.auto_confirm)
            self.assertTrue(loaded.verbose)
            self.assertEqual(loaded.background_image, "/tmp/wallpaper.jpg")
            self.assertEqual(loaded.tool_overrides.get("mke2fs"), "/custom/bin/mke2fs")

    def test_get_active_project_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proj_dir = root / "DNA_test_rom"
            proj_dir.mkdir(parents=True)

            cfg = GlobalConfig(
                workspace_root=str(root),
                active_project="test_rom",
            )
            resolved = get_active_project_path(cfg)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, proj_dir.resolve())


if __name__ == "__main__":
    unittest.main()
