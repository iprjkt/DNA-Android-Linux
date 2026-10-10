"""Unit tests for native tools registry."""

import unittest
from dna_core.tools import (
    KNOWN_TOOLS,
    check_all_tools,
    detect_distribution,
    get_install_command,
)


class TestTools(unittest.TestCase):
    def test_known_tools_definitions(self):
        self.assertGreater(len(KNOWN_TOOLS), 10)
        tool_names = [t.name for t in KNOWN_TOOLS]
        self.assertIn("lpunpack", tool_names)
        self.assertIn("lpmake", tool_names)
        self.assertIn("mke2fs", tool_names)
        self.assertIn("fsck.erofs", tool_names)
        self.assertIn("brotli", tool_names)
        self.assertIn("zstd", tool_names)

    def test_detect_distribution(self):
        distro = detect_distribution()
        self.assertIn(distro, ("arch", "debian", "ubuntu", "fedora", "other"))

    def test_check_all_tools(self):
        statuses = check_all_tools()
        self.assertEqual(len(statuses), len(KNOWN_TOOLS))

        # Core required tools like zstd, brotli, mke2fs should be installed on this host
        installed_dict = {s.definition.name: s.installed for s in statuses}
        self.assertTrue(installed_dict.get("zstd", False))
        self.assertTrue(installed_dict.get("brotli", False))

    def test_get_install_command(self):
        missing = [t for t in KNOWN_TOOLS if t.name in ("lpunpack", "mke2fs")]
        arch_cmd = get_install_command(missing, distro="arch")
        self.assertIn("pacman -S", arch_cmd)

        deb_cmd = get_install_command(missing, distro="debian")
        self.assertIn("apt-get install", deb_cmd)


if __name__ == "__main__":
    unittest.main()
