"""Unit tests for DNA setup mode and external tools installation."""

from __future__ import annotations

import stat
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dna_core.setup import (
    get_setup_tools_status,
    install_apktool,
    install_java,
    install_payload_dumper_go,
    setup_all,
)
from dna_core.tools import (
    KNOWN_TOOLS,
    check_tool,
    get_bundled_tools_dir,
    get_external_tools_dir,
)


class TestSetup(unittest.TestCase):
    def test_setup_tools_status(self):
        statuses = get_setup_tools_status()
        self.assertIn("java", statuses)
        self.assertIn("apktool", statuses)
        self.assertIn("payload-dumper-go", statuses)

        for name, item in statuses.items():
            self.assertEqual(item["name"], name)
            self.assertIn("installed", item)
            self.assertIn("source", item)
            self.assertIn("category", item)

    def test_bundled_tools_exist_and_resolved(self):
        bundled_dir = get_bundled_tools_dir()
        self.assertTrue(bundled_dir.exists())

        # Check a few bundled tools
        for tool_name in ["mke2fs", "simg2img", "lpunpack", "fsck.erofs"]:
            defn = next((t for t in KNOWN_TOOLS if t.name == tool_name), None)
            self.assertIsNotNone(defn)
            self.assertTrue(defn.is_bundled)

            status = check_tool(defn)
            self.assertTrue(status.installed)
            # Should resolve from bundled dir or system/override
            self.assertIn(status.source, ("bundled", "system", "override"))

    @patch("shutil.which", return_value="/usr/bin/java")
    @patch("subprocess.run")
    def test_install_java_already_present(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stderr="openjdk version \"17.0.1\"")
        ok, msg = install_java()
        self.assertTrue(ok)
        self.assertIn("already available", msg)

    @patch("shutil.which", return_value=None)
    @patch("dna_core.setup.detect_distribution", return_value="arch")
    def test_install_java_missing_arch(self, mock_distro, mock_which):
        ok, msg = install_java(interactive=False)
        self.assertFalse(ok)
        self.assertIn("pacman", msg)

    @patch("dna_core.setup._download_file")
    @patch("subprocess.run")
    def test_install_apktool(self, mock_run, mock_dl):
        mock_run.return_value = MagicMock(returncode=0, stdout="3.0.3", stderr="")
        with patch("dna_core.setup.get_external_tools_dir") as mock_dir:
            test_dir = Path("/tmp/dna_test_setup_apktool")
            test_dir.mkdir(parents=True, exist_ok=True)
            mock_dir.return_value = test_dir

            ok, msg = install_apktool()
            self.assertTrue(ok)
            self.assertTrue((test_dir / "apktool").exists())

            # Cleanup
            if (test_dir / "apktool").exists():
                (test_dir / "apktool").unlink()
            if (test_dir / "apktool.jar").exists():
                (test_dir / "apktool.jar").unlink()
            test_dir.rmdir()

    @patch("dna_core.setup._download_file")
    @patch("subprocess.run")
    def test_install_payload_dumper_go(self, mock_run, mock_dl):
        import io
        import tarfile

        mock_run.return_value = MagicMock(returncode=0, stdout="payload-dumper-go 2.1.0")

        with patch("dna_core.setup.get_external_tools_dir") as mock_dir:
            test_dir = Path("/tmp/dna_test_setup_pdg")
            test_dir.mkdir(parents=True, exist_ok=True)
            mock_dir.return_value = test_dir

            # Create a mock tar.gz containing payload-dumper-go
            tar_path = test_dir / "payload-dumper-go.tar.gz"

            def fake_download(url, dest, fallback_url=None):
                bio = io.BytesIO()
                with tarfile.open(fileobj=bio, mode="w:gz") as tar:
                    data = b"#!/bin/sh\necho payload-dumper-go"
                    ti = tarfile.TarInfo(name="payload-dumper-go")
                    ti.size = len(data)
                    ti.mode = 0o755
                    tar.addfile(ti, io.BytesIO(data))
                dest.write_bytes(bio.getvalue())

            mock_dl.side_effect = fake_download

            ok, msg = install_payload_dumper_go()
            self.assertTrue(ok)
            self.assertTrue((test_dir / "payload-dumper-go").exists())

            # Cleanup
            if (test_dir / "payload-dumper-go").exists():
                (test_dir / "payload-dumper-go").unlink()
            test_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
