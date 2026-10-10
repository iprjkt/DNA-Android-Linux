"""Unit tests for image and filesystem detection."""

import tempfile
import unittest
from pathlib import Path

from dna_core.detection import (
    EROFS_MAGIC,
    EXT4_MAGIC,
    LP_GEOMETRY_MAGIC,
    PAYLOAD_MAGIC,
    SPARSE_MAGIC,
    ZSTD_MAGIC,
    ImageType,
    detect_image_type,
    inspect_image,
)


class TestDetection(unittest.TestCase):
    def test_detect_sparse(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(SPARSE_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.SPARSE)

    def test_detect_payload_bin(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(PAYLOAD_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.PAYLOAD_BIN)

    def test_detect_zstd(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(ZSTD_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.ZSTD)

    def test_detect_super_lp(self):
        with tempfile.NamedTemporaryFile() as f:
            # 4096 padding + LP_GEOMETRY_MAGIC
            f.write(b"\x00" * 4096 + LP_GEOMETRY_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.SUPER_LP)

    def test_detect_ext4(self):
        with tempfile.NamedTemporaryFile() as f:
            # 1080 bytes padding + EXT4_MAGIC
            f.write(b"\x00" * 1080 + EXT4_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.EXT4)

    def test_detect_erofs(self):
        with tempfile.NamedTemporaryFile() as f:
            # 1024 bytes padding + EROFS_MAGIC
            f.write(b"\x00" * 1024 + EROFS_MAGIC + b"\x00" * 100)
            f.flush()
            self.assertEqual(detect_image_type(f.name), ImageType.EROFS)

    def test_inspect_image(self):
        with tempfile.NamedTemporaryFile(suffix=".img") as f:
            f.write(b"\x00" * 1080 + EXT4_MAGIC + b"\x00" * 100)
            f.flush()
            info = inspect_image(f.name)
            self.assertEqual(info.image_type, ImageType.EXT4)
            self.assertEqual(info.fs_type, "ext4")
            self.assertFalse(info.is_sparse)


if __name__ == "__main__":
    unittest.main()
