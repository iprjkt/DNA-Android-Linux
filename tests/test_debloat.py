"""Unit tests for data-driven ROM debloater."""

import tempfile
import unittest
from pathlib import Path

from dna_core.debloat import load_debloat_preset, run_debloat


class TestDebloat(unittest.TestCase):
    def test_load_presets(self):
        global_preset = load_debloat_preset("global")
        self.assertEqual(global_preset.name, "global")
        self.assertGreater(len(global_preset.packages), 5)

        china_preset = load_debloat_preset("china")
        self.assertEqual(china_preset.name, "china")
        self.assertGreater(len(china_preset.packages), 5)

    def test_run_debloat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create synthetic bloat apps
            analytics_dir = root / "system" / "app" / "Analytics"
            analytics_dir.mkdir(parents=True)
            (analytics_dir / "Analytics.apk").write_bytes(b"ANALYTICS_DATA" * 50)

            yellow_dir = root / "product" / "priv-app" / "YellowPage"
            yellow_dir.mkdir(parents=True)
            (yellow_dir / "YellowPage.apk").write_bytes(b"YELLOW_PAGE_DATA" * 50)

            # Legitimate app that should NOT be deleted
            launcher_dir = root / "system" / "priv-app" / "MiuiHome"
            launcher_dir.mkdir(parents=True)
            (launcher_dir / "MiuiHome.apk").write_bytes(b"LAUNCHER_DATA" * 50)

            preset = load_debloat_preset("global")

            # 1. Test dry-run
            dry_res = run_debloat(root, preset, dry_run=True)
            self.assertTrue(dry_res.dry_run)
            self.assertEqual(len(dry_res.removed_directories), 2)
            self.assertTrue(analytics_dir.is_dir())
            self.assertTrue(yellow_dir.is_dir())

            # 2. Test actual run
            real_res = run_debloat(root, preset, dry_run=False)
            self.assertFalse(real_res.dry_run)
            self.assertFalse(analytics_dir.exists())
            self.assertFalse(yellow_dir.exists())
            self.assertTrue(launcher_dir.is_dir())
            self.assertIn("Analytics", real_res.packages_affected)
            self.assertIn("YellowPage", real_res.packages_affected)


if __name__ == "__main__":
    unittest.main()
