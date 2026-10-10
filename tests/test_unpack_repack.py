"""Round-trip and integration tests for unpacking, repacking, resizing, and super."""

import tempfile
import unittest
from pathlib import Path

from dna_core.repack import repack_image, repack_super, repack_zstd
from dna_core.resize import resize_partition
from dna_core.unpack import unpack_image, unpack_super, unpack_zstd


class TestUnpackRepack(unittest.TestCase):
    def test_ext4_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            src_dir = td / "system_src"
            src_dir.mkdir()
            (src_dir / "bin").mkdir()
            (src_dir / "bin" / "sh").write_text("#!/bin/sh\necho test", encoding="utf-8")
            (src_dir / "build.prop").write_text("ro.build.id=TEST1234\n", encoding="utf-8")

            img_path = td / "system.img"
            unpack_dest = td / "system_extracted"

            # 1. Repack to ext4
            repack_image(src_dir=src_dir, out_img=img_path, fs_type="ext4", label="system")
            self.assertTrue(img_path.is_file())

            # 2. Unpack ext4
            unpack_image(img_path, out_dir=unpack_dest)
            self.assertTrue(unpack_dest.is_dir())
            self.assertTrue((unpack_dest / "bin" / "sh").is_file())
            self.assertTrue((unpack_dest / "build.prop").is_file())
            self.assertEqual(
                (src_dir / "build.prop").read_text(encoding="utf-8"),
                (unpack_dest / "build.prop").read_text(encoding="utf-8"),
            )

    def test_erofs_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            src_dir = td / "vendor_src"
            src_dir.mkdir()
            (src_dir / "etc").mkdir()
            (src_dir / "etc" / "fstab.qcom").write_text("/dev/block/boot /boot emmc defaults\n", encoding="utf-8")

            img_path = td / "vendor.erofs.img"
            unpack_dest = td / "vendor_extracted"

            # 1. Repack to erofs
            repack_image(src_dir=src_dir, out_img=img_path, fs_type="erofs", label="vendor")
            self.assertTrue(img_path.is_file())

            # 2. Unpack erofs
            unpack_image(img_path, out_dir=unpack_dest)
            self.assertTrue(unpack_dest.is_dir())
            self.assertTrue((unpack_dest / "etc" / "fstab.qcom").is_file())
            self.assertEqual(
                (src_dir / "etc" / "fstab.qcom").read_text(encoding="utf-8"),
                (unpack_dest / "etc" / "fstab.qcom").read_text(encoding="utf-8"),
            )

    def test_super_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            # Create small partition images (4MB each = 1024 blocks of 4096 bytes)
            sys_img = td / "system.img"
            sys_img.write_bytes(b"\x00" * (4 * 1024 * 1024))
            ven_img = td / "vendor.img"
            ven_img.write_bytes(b"\x00" * (4 * 1024 * 1024))

            super_img = td / "super.img"
            unpack_dir = td / "super_out"

            # 1. Repack super.img
            repack_super(
                partition_images=[sys_img, ven_img],
                out_super=super_img,
                device_size=32 * 1024 * 1024,  # 32MB super
                group_name="dyn_part",
                slot_type="a_only",
                sparse=False,
            )
            self.assertTrue(super_img.is_file())

            # 2. Unpack super.img
            extracted = unpack_super(super_img, out_dir=unpack_dir)
            extracted_names = [e.name for e in extracted]
            self.assertIn("system.img", extracted_names)
            self.assertIn("vendor.img", extracted_names)

    def test_zstd_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            orig = td / "test.txt"
            orig.write_text("Hello Zstandard Compression from DNA-Linux!" * 200, encoding="utf-8")
            compressed = td / "test.txt.zst"
            decompressed = td / "test_restored.txt"

            repack_zstd(orig, out_file=compressed, level=3)
            self.assertTrue(compressed.is_file())

            unpack_zstd(compressed, out_file=decompressed)
            self.assertTrue(decompressed.is_file())
            self.assertEqual(orig.read_text(encoding="utf-8"), decompressed.read_text(encoding="utf-8"))

    def test_resize_ext4(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            src_dir = td / "resize_src"
            src_dir.mkdir()
            (src_dir / "sample.txt").write_text("Test resize", encoding="utf-8")

            img_path = td / "resize.img"
            repack_image(src_dir=src_dir, out_img=img_path, fs_type="ext4", label="test")
            orig_size = img_path.stat().st_size

            # Append +4MB
            resize_partition(img_path, extra_mb=4)
            new_size = img_path.stat().st_size
            self.assertEqual(new_size, orig_size + (4 * 1024 * 1024))


if __name__ == "__main__":
    unittest.main()
