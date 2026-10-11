"""Unit tests for configuration manager and CLI config commands."""

import tempfile
import unittest
from pathlib import Path
from click.testing import CliRunner

from dna_cli.main import cli
from dna_core.config import (
    GlobalConfig,
    get_active_project_path,
    get_workspace_roots,
    reset_workspace_roots,
    set_workspace_roots,
)


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

    def test_workspace_roots_helpers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "config.toml"
            custom_io = Path(tmpdir) / "my_io"
            custom_work = Path(tmpdir) / "my_work"

            cfg = set_workspace_roots(io_root=custom_io, work_root=custom_work, config_path=cfg_file)
            self.assertEqual(cfg.io_root, str(custom_io.resolve()))
            self.assertEqual(cfg.work_root, str(custom_work.resolve()))
            self.assertTrue(custom_io.is_dir())
            self.assertTrue(custom_work.is_dir())

            io_r, work_r = get_workspace_roots(cfg)
            self.assertEqual(io_r, custom_io.resolve())
            self.assertEqual(work_r, custom_work.resolve())

            reset_cfg = reset_workspace_roots(config_path=cfg_file)
            from dna_core.paths import get_default_io_root, get_default_work_root
            self.assertEqual(reset_cfg.io_root, str(get_default_io_root()))
            self.assertEqual(reset_cfg.work_root, str(get_default_work_root()))

    def test_cli_config_commands(self):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = str(Path(tmpdir).resolve())

            # 1. Config show
            res_show = runner.invoke(cli, ["config", "show"])
            self.assertEqual(res_show.exit_code, 0)
            self.assertIn("io_root", res_show.output)
            self.assertIn("work_root", res_show.output)

            # 2. Config set io_root
            res_set = runner.invoke(cli, ["config", "set", "io_root", custom_path])
            self.assertEqual(res_set.exit_code, 0)
            self.assertIn("Updated io_root", res_set.output)

            # 3. Config get io_root
            res_get = runner.invoke(cli, ["config", "get", "io_root"])
            self.assertEqual(res_get.exit_code, 0)
            self.assertIn(custom_path, res_get.output)

            # 4. Project roots
            res_roots = runner.invoke(cli, ["project", "roots"])
            self.assertEqual(res_roots.exit_code, 0)
            self.assertIn("Current Workspace Roots", res_roots.output)
            self.assertIn(custom_path, res_roots.output)

            # 5. Config reset
            res_reset = runner.invoke(cli, ["config", "reset"])
            self.assertEqual(res_reset.exit_code, 0)
            self.assertIn("Reset workspace roots", res_reset.output)

    def test_cli_project_create_with_custom_roots(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_io, tempfile.TemporaryDirectory() as tmp_work:
            io_p = Path(tmp_io)
            work_p = Path(tmp_work)

            res = runner.invoke(
                cli,
                [
                    "project",
                    "create",
                    "custom_cli_rom",
                    "--io-root",
                    str(io_p),
                    "--work-root",
                    str(work_p),
                ],
            )
            self.assertEqual(res.exit_code, 0)
            self.assertTrue((io_p / "DNA_custom_cli_rom").is_dir())
            self.assertTrue((io_p / "DNA_custom_cli_rom" / "out").is_dir())
            self.assertTrue((work_p / "DNA_custom_cli_rom").is_dir())
            self.assertTrue((work_p / "DNA_custom_cli_rom" / "config").is_dir())


if __name__ == "__main__":
    unittest.main()
