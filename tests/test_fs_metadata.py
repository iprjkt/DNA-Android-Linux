"""Unit tests for fs_metadata, SELinux file_contexts preservation, and SAR repacking."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from dna_core.fs_metadata import (
    FsConfigEntry,
    get_effective_mount_point,
    harvest_partition_file_contexts,
    is_system_as_root,
    sanitize_fs_config_entry,
    scan_directory_fs_metadata,
    sync_file_contexts_file,
    sync_fs_config_file,
    write_file_contexts_file,
    write_fs_config_file,
)
from dna_core.repack import repack_image


class TestFsMetadata(unittest.TestCase):
    def test_sar_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Not SAR (no system folder)
            self.assertFalse(is_system_as_root(root, "system"))
            self.assertEqual(get_effective_mount_point(root, "system"), "/system")
            self.assertEqual(get_effective_mount_point(root, "vendor"), "/vendor")

            # SAR layout
            (root / "system").mkdir()
            (root / "init").symlink_to("/system/bin/init")
            (root / "system" / "bin").mkdir(parents=True)
            (root / "system" / "bin" / "init").write_text("binary")

            self.assertTrue(is_system_as_root(root, "system"))
            self.assertEqual(get_effective_mount_point(root, "system"), "/")

    def test_uid_gid_sanitization(self):
        # Host user 1000:1000 on standard file
        entry = FsConfigEntry(path="system/etc/build.prop", uid=1000, gid=1000, mode="644")
        san = sanitize_fs_config_entry(entry, is_sar=False)
        self.assertEqual(san.uid, 0)
        self.assertEqual(san.gid, 0)
        self.assertEqual(san.mode, "644")

        # Executable in bin/
        bin_entry = FsConfigEntry(path="system/bin/sh", uid=1000, gid=1000, mode="755")
        san_bin = sanitize_fs_config_entry(bin_entry, is_sar=False)
        self.assertEqual(san_bin.uid, 0)
        self.assertEqual(san_bin.gid, 2000)

        # Init must be 0:0 and 755
        init_entry = FsConfigEntry(path="system/bin/init", uid=1000, gid=1000, mode="777")
        san_init = sanitize_fs_config_entry(init_entry, is_sar=False)
        self.assertEqual(san_init.uid, 0)
        self.assertEqual(san_init.gid, 0)
        self.assertEqual(san_init.mode, "755")

        # SAR double-prefix fix
        sar_double = FsConfigEntry(path="system/system/bin/init", uid=1000, gid=1000, mode="755")
        san_sar = sanitize_fs_config_entry(sar_double, is_sar=True)
        self.assertEqual(san_sar.path, "system/bin/init")
        self.assertEqual(san_sar.uid, 0)

    def test_harvest_and_sync_canonical_file_contexts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            selinux_dir = root / "system" / "etc" / "selinux"
            selinux_dir.mkdir(parents=True)
            plat_fc = selinux_dir / "plat_file_contexts"
            plat_fc.write_text(
                "/init u:object_r:init_exec:s0\n"
                "/system/bin/init u:object_r:init_exec:s0\n"
                "/system/bin/sh u:object_r:shell_exec:s0\n"
                "/system(/.*)? u:object_r:system_file:s0\n"
            )

            # Harvest canonical contexts
            fc_list = harvest_partition_file_contexts(root, part_name="system", is_sar=True)
            fc_dict = dict(fc_list)
            self.assertEqual(fc_dict.get("/system/bin/init"), "u:object_r:init_exec:s0")
            self.assertEqual(fc_dict.get("/init"), "u:object_r:init_exec:s0")

            # Test sync_file_contexts_file enriching an existing stub
            cfg_fc = root / "system_file_contexts"
            cfg_fc.write_text("/system(/.*)? u:object_r:system_file:s0\n")

            sync_file_contexts_file(mount_point="system", fc_file=cfg_fc, root_dir=root)
            enriched_text = cfg_fc.read_text()
            self.assertIn("/system/bin/init u:object_r:init_exec:s0", enriched_text)
            self.assertIn("/lost\\+found u:object_r:rootfs:s0", enriched_text)

    def test_repack_sar_ext4_preserves_selinux_xattrs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "system_tree"
            src.mkdir()
            (src / "init").symlink_to("/system/bin/init")
            (src / "system" / "bin").mkdir(parents=True)
            (src / "system" / "bin" / "init").write_text("#!/bin/sh\nexit 0")
            (src / "system" / "etc" / "selinux").mkdir(parents=True)
            (src / "system" / "etc" / "selinux" / "plat_file_contexts").write_text(
                "/init u:object_r:init_exec:s0\n"
                "/system/bin/init u:object_r:init_exec:s0\n"
                "/system(/.*)? u:object_r:system_file:s0\n"
            )

            out_img = root / "system.img"
            repack_image(src, out_img=out_img, fs_type="ext4", label="system")

            self.assertTrue(out_img.is_file())

            # Verify xattrs using debugfs
            res = subprocess.run(
                ["debugfs", "-R", "ea_list /system/bin/init", str(out_img)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("u:object_r:init_exec:s0", res.stdout)
            self.assertNotIn("u:object_r:system_file:s0", res.stdout)

            # Verify rootfs /init symlink xattr
            res_init = subprocess.run(
                ["debugfs", "-R", "ea_list /init", str(out_img)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("u:object_r:init_exec:s0", res_init.stdout)


if __name__ == "__main__":
    unittest.main()
