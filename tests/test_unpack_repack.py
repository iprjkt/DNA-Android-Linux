"""Round-trip and integration tests for unpacking, repacking, resizing, and super."""

import tempfile
import unittest
from pathlib import Path

from dna_core.project import create_project
from dna_core.repack import repack_image, repack_super, repack_zstd
from dna_core.resize import resize_partition
from dna_core.unpack import (
    _create_temp_raw_file,
    format_partition_size,
    get_super_partitions_info,
    unpack_image,
    unpack_super,
    unpack_zstd,
)


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

    def test_super_vab_slot_normalization(self):
        """Verify that Virtual A/B super.img unpacking normalizes partition names (vendor_a.img -> vendor.img)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            sys_img = td / "system.img"
            sys_img.write_bytes(b"\x00" * (4 * 1024 * 1024))
            ven_img = td / "vendor.img"
            ven_img.write_bytes(b"\x00" * (4 * 1024 * 1024))

            super_img = td / "super.img"
            unpack_dir = td / "super_out"

            # 1. Repack super with Virtual A/B (partitions are named system_a, vendor_a in super)
            repack_super(
                partition_images=[sys_img, ven_img],
                out_super=super_img,
                device_size=32 * 1024 * 1024,
                group_name="qti_dynamic_partitions",
                slot_type="vab",
                sparse=False,
            )
            self.assertTrue(super_img.is_file())

            # 2. Unpack all: partition files should be normalized to system.img and vendor.img (no _a)
            extracted = unpack_super(super_img, out_dir=unpack_dir)
            extracted_names = [e.name for e in extracted]
            self.assertIn("system.img", extracted_names)
            self.assertIn("vendor.img", extracted_names)
            self.assertNotIn("system_a.img", extracted_names)
            self.assertNotIn("vendor_a.img", extracted_names)

            self.assertTrue((unpack_dir / "system.img").is_file())
            self.assertTrue((unpack_dir / "vendor.img").is_file())
            self.assertFalse((unpack_dir / "system_a.img").exists())
            self.assertFalse((unpack_dir / "vendor_a.img").exists())

            # 3. Selective unpack using clean name 'vendor'
            unpack_sel_dir = td / "super_sel_out"
            extracted_sel = unpack_super(super_img, out_dir=unpack_sel_dir, partitions=["vendor"])
            extracted_sel_names = [e.name for e in extracted_sel]
            self.assertEqual(extracted_sel_names, ["vendor.img"])
            self.assertTrue((unpack_sel_dir / "vendor.img").is_file())
            self.assertFalse((unpack_sel_dir / "system.img").exists())
            self.assertFalse((unpack_sel_dir / "vendor_a.img").exists())

    def test_create_temp_raw_file_prefers_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            custom_dir = td / "custom_work"
            custom_dir.mkdir()
            dummy_src = td / "dummy.img"
            dummy_src.touch()

            tmp_raw = _create_temp_raw_file(dummy_src, preferred_dir=custom_dir)
            try:
                self.assertTrue(tmp_raw.is_file())
                self.assertEqual(tmp_raw.parent.resolve(), custom_dir.resolve())
            finally:
                if tmp_raw.exists():
                    tmp_raw.unlink()

    def test_super_sparse_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            sys_img = td / "system.img"
            sys_img.write_bytes(b"\x00" * (4 * 1024 * 1024))
            ven_img = td / "vendor.img"
            ven_img.write_bytes(b"\x00" * (4 * 1024 * 1024))

            super_img = td / "super.img"
            unpack_dir = td / "super_out"

            # 1. Repack sparse super.img
            repack_super(
                partition_images=[sys_img, ven_img],
                out_super=super_img,
                device_size=32 * 1024 * 1024,
                group_name="dyn_part",
                slot_type="a_only",
                sparse=True,
            )
            self.assertTrue(super_img.is_file())

            # 2. Unpack sparse super.img into unpack_dir
            extracted = unpack_super(super_img, out_dir=unpack_dir)
            extracted_names = [e.name for e in extracted]
            self.assertIn("system.img", extracted_names)
            self.assertIn("vendor.img", extracted_names)
            self.assertNotIn("super.img", extracted_names)
            # Ensure no lingering temp raw files left behind
            lingering = list(unpack_dir.glob(".tmp_raw_*")) + list(td.glob(".tmp_raw_*"))
            self.assertEqual(lingering, [])

    def test_format_partition_size(self):
        self.assertEqual(format_partition_size(512), "512B")
        self.assertEqual(format_partition_size(348160), "340.0K")
        self.assertEqual(format_partition_size(964034560), "919.4M")
        self.assertEqual(format_partition_size(3389730816), "3.2G")

    def test_get_super_partitions_info_and_selective_unpack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            sys_img = td / "system.img"
            sys_img.write_bytes(b"\x00" * (4 * 1024 * 1024))
            ven_img = td / "vendor.img"
            ven_img.write_bytes(b"\x00" * (4 * 1024 * 1024))

            super_img = td / "super.img"
            repack_super(
                partition_images=[sys_img, ven_img],
                out_super=super_img,
                device_size=32 * 1024 * 1024,
                group_name="dyn_part",
                slot_type="a_only",
                sparse=True,
            )

            # Test get_super_partitions_info
            infos = get_super_partitions_info(super_img)
            self.assertEqual(len(infos), 2)
            names = [info.name for info in infos]
            self.assertIn("system", names)
            self.assertIn("vendor", names)
            labels = [info.label for info in infos]
            self.assertIn("system(4.0M)", labels)
            self.assertIn("vendor(4.0M)", labels)

            # Test selective unpack of only 'system'
            unpack_dir = td / "super_sel_out"
            extracted = unpack_super(super_img, out_dir=unpack_dir, partitions=["system"])
            extracted_names = [e.name for e in extracted]
            self.assertIn("system.img", extracted_names)
            self.assertNotIn("vendor.img", extracted_names)

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

    def test_split_project_unpack_repack_flow(self):
        with tempfile.TemporaryDirectory() as tmp_io, tempfile.TemporaryDirectory() as tmp_work:
            io_root = Path(tmp_io)
            work_root = Path(tmp_work)

            proj = create_project(
                name="jacobi_flow",
                io_root=io_root,
                work_root=work_root,
                set_active=False,
            )

            # Create an ext4 product.img in io_dir
            src_dir = work_root / "temp_product_src"
            src_dir.mkdir()
            (src_dir / "app").mkdir()
            (src_dir / "app" / "MiuiHome.apk").write_bytes(b"APK_DATA")
            (src_dir / "build.prop").write_text("ro.product.name=jacobi\n", encoding="utf-8")

            input_img = proj.paths.io_dir / "product.img"
            repack_image(src_dir=src_dir, out_img=input_img, fs_type="ext4", label="product")
            self.assertTrue(input_img.is_file())

            # Unpack into project: should go directly into proj.paths.work_dir / "product"
            # and metadata in proj.paths.work_dir / "config"
            unpack_dest = unpack_image(input_img, project=proj)
            self.assertEqual(unpack_dest, proj.paths.work_dir / "product")
            self.assertTrue(unpack_dest.is_dir())
            self.assertTrue((unpack_dest / "build.prop").is_file())
            self.assertTrue((proj.paths.config_dir / "product_fs_config").is_file())
            self.assertTrue((proj.paths.config_dir / "product_file_contexts").is_file())

            # Repack from project: should output to proj.paths.out_dir / "product.img"
            out_img = repack_image(src_dir=unpack_dest, project=proj)
            self.assertEqual(out_img, proj.paths.out_dir / "product.img")
            self.assertTrue(out_img.is_file())


if __name__ == "__main__":
    unittest.main()
