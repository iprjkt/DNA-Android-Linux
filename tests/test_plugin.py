"""Unit tests for Phase 6 Plugin management and sandboxed runner."""

import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from dna_core.paths import ProjectPaths
from dna_core.plugin import (
    PluginMetadata,
    delete_plugin,
    get_plugin,
    import_plugin,
    list_plugins,
    load_plugin_manifest,
    run_plugin,
)


class TestPluginSystem(unittest.TestCase):
    def test_load_plugin_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "plugin.toml").write_text(
                '[plugin]\nid = "test-plugin"\nname = "Test Plugin"\nversion = "2.1.0"\nentrypoint = "main.py"\n',
                encoding="utf-8",
            )
            (pdir / "main.py").write_text("print('hello')", encoding="utf-8")

            meta = load_plugin_manifest(pdir)
            self.assertEqual(meta.id, "test-plugin")
            self.assertEqual(meta.name, "Test Plugin")
            self.assertEqual(meta.version, "2.1.0")
            self.assertEqual(meta.entrypoint, "main.py")

    def test_load_plugin_missing_entrypoint(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "plugin.toml").write_text(
                '[plugin]\nid = "test-plugin"\nname = "Test"\nentrypoint = "missing.sh"\n',
                encoding="utf-8",
            )
            with self.assertRaises(FileNotFoundError):
                load_plugin_manifest(pdir)

    def test_load_plugin_invalid_id(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "plugin.toml").write_text(
                '[plugin]\nid = "invalid id with spaces!"\nname = "Test"\nentrypoint = "run.sh"\n',
                encoding="utf-8",
            )
            (pdir / "run.sh").write_text("echo hi", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_plugin_manifest(pdir)

    def test_import_and_list_plugin(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zip_path = root / "sample.zip"
            target_plugins_dir = root / "plugins"

            # Create a sample plugin ZIP archive
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr(
                    "plugin.toml",
                    '[plugin]\nid = "zip-plugin"\nname = "ZIP Plugin"\nentrypoint = "run.sh"\n',
                )
                zf.writestr("run.sh", "#!/bin/bash\necho 'running from zip'\n")

            meta = import_plugin(zip_path, target_plugins_dir)
            self.assertEqual(meta.id, "zip-plugin")
            self.assertTrue((target_plugins_dir / "zip-plugin" / "run.sh").is_file())

            # Verify listed
            plugins = list_plugins(project_plugins_dir=target_plugins_dir, include_global=False)
            self.assertEqual(len(plugins), 1)
            self.assertEqual(plugins[0].id, "zip-plugin")

            # Duplicate import without overwrite raises error
            with self.assertRaises(FileExistsError):
                import_plugin(zip_path, target_plugins_dir, overwrite=False)

            # With overwrite succeeds
            meta_re = import_plugin(zip_path, target_plugins_dir, overwrite=True)
            self.assertEqual(meta_re.id, "zip-plugin")

    def test_zip_slip_prevention(self):
        """Verify that archives with path traversal are rejected."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evil_zip = root / "evil.zip"
            target_plugins_dir = root / "plugins"

            with zipfile.ZipFile(evil_zip, "w") as zf:
                zf.writestr("../../evil.txt", "malicious payload")
                zf.writestr("plugin.toml", '[plugin]\nid = "evil"\nname = "Evil"\nentrypoint = "run.sh"\n')
                zf.writestr("run.sh", "echo evil")

            with self.assertRaises(PermissionError):
                import_plugin(evil_zip, target_plugins_dir)

    def test_run_plugin_sandbox(self):
        """Verify environment variable injection and working directory containment."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "DNA_test_project"
            paths = ProjectPaths(project_dir=project_dir)
            paths.ensure_layout()

            # Create a test python plugin that dumps environment variables
            plugin_dir = paths.plugins_dir / "env-test"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.toml").write_text(
                '[plugin]\nid = "env-test"\nname = "Env Test"\nentrypoint = "test_env.py"\n',
                encoding="utf-8",
            )
            script = """
import os, sys
print("PROJECT_NAME=" + os.environ.get("DNA_PROJECT_NAME", ""))
print("UNPACKED=" + os.environ.get("DNA_UNPACKED", ""))
print("CWD=" + os.getcwd())
print("ARG=" + sys.argv[1] if len(sys.argv) > 1 else "NO_ARG")
"""
            (plugin_dir / "test_env.py").write_text(script, encoding="utf-8")

            meta = load_plugin_manifest(plugin_dir)
            res = run_plugin(meta, paths, args=["test_argument"])
            self.assertEqual(res.returncode, 0)
            stdout = res.stdout

            self.assertIn("PROJECT_NAME=test_project", stdout)
            self.assertIn("UNPACKED=" + str(paths.unpacked_dir), stdout)
            self.assertIn("CWD=" + str(project_dir), stdout)
            self.assertIn("ARG=test_argument", stdout)

            # Verify log file created
            log_files = list(paths.logs_dir.glob("plugin_env-test_*.log"))
            self.assertEqual(len(log_files), 1)

    def test_delete_plugin(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td) / "to_delete"
            pdir.mkdir()
            (pdir / "plugin.toml").write_text(
                '[plugin]\nid = "del"\nname = "Del"\nentrypoint = "run.sh"\n',
                encoding="utf-8",
            )
            (pdir / "run.sh").write_text("echo", encoding="utf-8")

            meta = load_plugin_manifest(pdir)
            self.assertTrue(delete_plugin(meta))
            self.assertFalse(pdir.exists())


if __name__ == "__main__":
    unittest.main()
