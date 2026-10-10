"""Unit tests for lossless build.prop parser and editor."""

import tempfile
import unittest
from pathlib import Path

from dna_core.prop import PropFile, find_prop_files


SAMPLE_BUILD_PROP = """#
# ADDITIONAL_BUILD_PROPERTIES
#
ro.build.id=UKQ1.231003.002
ro.build.display.id=HyperOS 1.0.4.0

# Security patch
ro.build.version.security_patch=2024-05-01
ro.build.fingerprint=Xiaomi/tanzanite/tanzanite:14/UKQ1.231003.002/OS1.0.4.0:user/release-keys

# Priv-app permissions
ro.control_privapp_permissions=enforce
ro.product.model=Redmi Note 13 Pro 4G
"""


class TestPropFile(unittest.TestCase):
    def test_parse_and_get(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        self.assertTrue(prop.has_key("ro.build.id"))
        self.assertEqual(prop.get("ro.build.id"), "UKQ1.231003.002")
        self.assertEqual(prop.get("ro.product.model"), "Redmi Note 13 Pro 4G")
        self.assertIsNone(prop.get("non_existent_key"))
        self.assertEqual(prop.get("non_existent_key", "default_val"), "default_val")

    def test_preserve_comments_and_format(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        rendered = prop.to_text()
        self.assertEqual(rendered, SAMPLE_BUILD_PROP)

    def test_update_existing_in_place(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        prop.set("ro.build.id", "NEW_BUILD_ID")
        self.assertEqual(prop.get("ro.build.id"), "NEW_BUILD_ID")

        text = prop.to_text()
        self.assertIn("ro.build.id=NEW_BUILD_ID\n", text)
        # Verify comment above it is still intact
        self.assertIn("# ADDITIONAL_BUILD_PROPERTIES\n", text)
        # Verify position is preserved (before ro.build.display.id)
        idx_id = text.index("ro.build.id=NEW_BUILD_ID")
        idx_display = text.index("ro.build.display.id")
        self.assertLess(idx_id, idx_display)

    def test_append_new_key(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        prop.set("custom.dna.tweaked", "true")
        self.assertTrue(prop.has_key("custom.dna.tweaked"))
        self.assertEqual(prop.get("custom.dna.tweaked"), "true")

        text = prop.to_text()
        self.assertTrue(text.endswith("custom.dna.tweaked=true\n"))

    def test_delete_key(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        self.assertTrue(prop.has_key("ro.control_privapp_permissions"))
        deleted = prop.delete("ro.control_privapp_permissions")
        self.assertTrue(deleted)
        self.assertFalse(prop.has_key("ro.control_privapp_permissions"))

        # Check comment before it is still there
        text = prop.to_text()
        self.assertIn("# Priv-app permissions\n", text)
        self.assertNotIn("ro.control_privapp_permissions", text)

        # Deleting non-existent key returns False
        self.assertFalse(prop.delete("non_existent"))

    def test_keys_and_items(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        keys = prop.keys()
        self.assertIn("ro.build.id", keys)
        self.assertIn("ro.build.fingerprint", keys)
        self.assertEqual(len(keys), 6)

        d = prop.to_dict()
        self.assertEqual(d["ro.product.model"], "Redmi Note 13 Pro 4G")

    def test_search(self):
        prop = PropFile.from_text(SAMPLE_BUILD_PROP)
        matches = prop.search(r"fingerprint|security_patch")
        self.assertEqual(len(matches), 2)
        match_keys = [k for k, v in matches]
        self.assertIn("ro.build.fingerprint", match_keys)
        self.assertIn("ro.build.version.security_patch", match_keys)

    def test_file_load_and_save(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "vendor" / "build.prop"
            f.parent.mkdir(parents=True)
            f.write_text(SAMPLE_BUILD_PROP, encoding="utf-8")

            prop = PropFile.load(f)
            self.assertEqual(prop.get("ro.build.id"), "UKQ1.231003.002")

            prop.set("ro.build.id", "MODIFIED_ID")
            prop.save()

            reloaded = PropFile.load(f)
            self.assertEqual(reloaded.get("ro.build.id"), "MODIFIED_ID")

    def test_find_prop_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "system").mkdir()
            (root / "system" / "build.prop").write_text("ro.test=1")
            (root / "vendor").mkdir()
            (root / "vendor" / "build.prop").write_text("ro.test=2")
            (root / "product").mkdir()
            (root / "product" / "default.prop").write_text("ro.test=3")

            found = find_prop_files(root)
            self.assertEqual(len(found), 3)


if __name__ == "__main__":
    unittest.main()
