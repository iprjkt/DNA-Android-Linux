"""Unit tests for sdat2img and img2sdat round-trip conversions."""

import tempfile
import unittest
from pathlib import Path

from dna_core.sdat import (
    format_rangeset,
    img2sdat,
    parse_rangeset,
    sdat2img,
)


class TestSdat(unittest.TestCase):
    def test_parse_and_format_rangeset(self):
        ranges = parse_rangeset("4,0,10,20,30")
        self.assertEqual(ranges, [(0, 10), (20, 30)])

        formatted = format_rangeset([(0, 10), (20, 30)])
        self.assertEqual(formatted, "4,0,10,20,30")

    def test_img2sdat_sdat2img_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            orig_img = td / "test.img"
            restored_img = td / "restored.img"

            # Create synthetic raw 64KB image (16 blocks of 4096 bytes)
            BLOCK_SIZE = 4096
            content = bytearray(16 * BLOCK_SIZE)
            content[0:len(b"SUPERBLOCK_EXT4_HEADER")] = b"SUPERBLOCK_EXT4_HEADER"
            content[4096:4096 + len(b"SYSTEM_BIN_SH_EXECUTABLE")] = b"SYSTEM_BIN_SH_EXECUTABLE"
            content[8192:8192 + len(b"BUILD_PROP_DATA")] = b"BUILD_PROP_DATA"

            orig_img.write_bytes(content)

            # Convert img -> transfer.list + new.dat
            trans_file, dat_file = img2sdat(orig_img, td, partition_name="test")
            self.assertTrue(trans_file.is_file())
            self.assertTrue(dat_file.is_file())

            # Convert transfer.list + new.dat -> restored.img
            sdat2img(trans_file, dat_file, restored_img)
            self.assertTrue(restored_img.is_file())

            # Verify contents match exactly
            self.assertEqual(orig_img.read_bytes(), restored_img.read_bytes())


if __name__ == "__main__":
    unittest.main()
