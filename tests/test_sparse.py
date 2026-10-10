"""Unit tests for sparse image conversions, splitting, and merging."""

import tempfile
import unittest
from pathlib import Path

from dna_core.sparse import (
    is_sparse_image,
    merge_sparse_chunks,
    raw_to_sparse,
    sparse_to_raw,
    split_sparse_image,
)


class TestSparse(unittest.TestCase):
    def test_sparse_raw_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            raw_orig = td / "orig.raw"
            sparse_file = td / "out.simg"
            raw_restored = td / "restored.raw"

            # Create 1MB block-aligned raw file (256 blocks of 4096 bytes)
            BLOCK_SIZE = 4096
            content = bytearray(256 * BLOCK_SIZE)
            h1 = b"SPARSE_TEST_HEADER_BLOCK_0"
            content[0:len(h1)] = h1
            h2 = b"MIDDLE_BLOCK_DATA"
            content[4096 * 10:4096 * 10 + len(h2)] = h2
            h3 = b"TRAILING_BLOCK_DATA"
            content[4096 * 255:4096 * 255 + len(h3)] = h3
            raw_orig.write_bytes(content)

            self.assertFalse(is_sparse_image(raw_orig))

            # Convert to sparse
            raw_to_sparse(raw_orig, sparse_file)
            self.assertTrue(sparse_file.is_file())
            self.assertTrue(is_sparse_image(sparse_file))

            # Convert back to raw
            sparse_to_raw(sparse_file, raw_restored)
            self.assertTrue(raw_restored.is_file())
            self.assertEqual(raw_orig.read_bytes(), raw_restored.read_bytes())

    def test_split_and_merge_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            orig_img = td / "super.img"
            chunks_dir = td / "chunks"
            merged_img = td / "super_merged.img"

            # 2MB block-aligned image
            orig_img.write_bytes(b"A" * (4096 * 512))

            chunks = split_sparse_image(orig_img, out_dir=chunks_dir, parts=4, prefix="super.img")
            self.assertEqual(len(chunks), 4)

            merge_sparse_chunks(chunks, merged_img)
            self.assertTrue(merged_img.is_file())
            self.assertEqual(orig_img.read_bytes(), merged_img.read_bytes())


if __name__ == "__main__":
    unittest.main()
