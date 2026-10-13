"""Unit tests verifying native C++ backend (dna_core_cpp) functionality and speed."""

import tempfile
import unittest
from pathlib import Path

from dna_core import dna_core_cpp


class TestCppBackend(unittest.TestCase):
    def test_cpp_module_loaded(self):
        self.assertIsNotNone(dna_core_cpp)
        self.assertTrue(hasattr(dna_core_cpp, "detect_image_type"))
        self.assertTrue(hasattr(dna_core_cpp, "PropFile"))
        self.assertTrue(hasattr(dna_core_cpp, "is_sparse_image"))
        self.assertTrue(hasattr(dna_core_cpp, "scan_directory_fs_metadata"))

    def test_cpp_prop_file(self):
        sample = (
            "# System Build Properties\n"
            "ro.build.version.release=14\n"
            "ro.product.model=Pixel 7 Pro\n"
            "ro.product.brand=google\n"
        )
        prop = dna_core_cpp.PropFile.from_text(sample)
        self.assertTrue(prop.has_key("ro.product.model"))
        self.assertEqual(prop.get("ro.product.model"), "Pixel 7 Pro")
        self.assertEqual(prop.get("non_existent", "default"), "default")

        # Mutate
        prop.set("ro.product.model", "Pixel 9 Pro")
        self.assertEqual(prop.get("ro.product.model"), "Pixel 9 Pro")

        # Delete
        self.assertTrue(prop.delete("ro.product.brand"))
        self.assertFalse(prop.has_key("ro.product.brand"))
        self.assertIn("ro.product.model=Pixel 9 Pro", prop.to_text())
        self.assertNotIn("ro.product.brand", prop.to_text())

    def test_cpp_detection_magic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            sparse_img = p / "test_sparse.img"
            sparse_img.write_bytes(b"\x3a\xff\x26\xed" + b"\x00" * 100)
            self.assertEqual(dna_core_cpp.detect_image_type(str(sparse_img)), dna_core_cpp.ImageType.SPARSE)
            self.assertTrue(dna_core_cpp.is_sparse_image(str(sparse_img)))

            info = dna_core_cpp.inspect_image(str(sparse_img))
            self.assertTrue(info.is_sparse)
            self.assertEqual(info.size_bytes, 104)

            # Test Ext4 magic at offset 1080 (0x438)
            ext4_img = p / "test_ext4.img"
            ext4_data = bytearray(2048)
            ext4_data[1080:1082] = b"\x53\xef"
            ext4_img.write_bytes(ext4_data)
            self.assertEqual(dna_core_cpp.detect_image_type(str(ext4_img)), dna_core_cpp.ImageType.EXT4)

    def test_cpp_fs_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "bin").mkdir()
            (p / "bin" / "sh").write_bytes(b"#!/bin/sh\n")
            (p / "etc").mkdir()
            (p / "etc" / "hosts").write_bytes(b"127.0.0.1 localhost\n")

            res = dna_core_cpp.scan_directory_fs_metadata(str(p), "system")
            paths = [e.path for e in res.fs_entries]
            self.assertIn("/", paths)
            self.assertIn("system", paths)
            self.assertIn("system/bin", paths)
            self.assertIn("system/bin/sh", paths)

    def test_cpp_split_and_merge_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            raw = p / "test_raw.bin"
            raw.write_bytes(b"A" * 65536)

            chunks = dna_core_cpp.split_sparse_image(str(raw), str(p / "chunks"), 4, "chunk")
            self.assertGreaterEqual(len(chunks), 2)

            merged = p / "merged.bin"
            dna_core_cpp.merge_sparse_chunks(chunks, str(merged))
            self.assertEqual(merged.read_bytes(), raw.read_bytes())


if __name__ == "__main__":
    unittest.main()
