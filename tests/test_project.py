"""Unit tests for project workspace lifecycle."""

import tempfile
import unittest
from pathlib import Path

from dna_core.config import GlobalConfig
from dna_core.project import (
    create_project,
    delete_project,
    list_projects,
    resolve_project,
    select_project,
)


class TestProject(unittest.TestCase):
    def test_create_and_resolve_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg_file = root / "config.toml"

            project = create_project(
                name="miui_test",
                root_dir=root,
                description="Test project",
                set_active=False,
            )

            self.assertEqual(project.name, "miui_test")
            self.assertTrue(project.directory.is_dir())
            self.assertTrue(project.paths.rom_dir.is_dir())
            self.assertTrue(project.paths.project_file.is_file())

            # Resolve project
            resolved = resolve_project("miui_test", root_dir=root)
            self.assertEqual(resolved.name, "miui_test")
            self.assertEqual(resolved.metadata.get("description"), "Test project")

    def test_conflict_and_auto_rename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project("rom", root_dir=root, set_active=False)

            with self.assertRaises(FileExistsError):
                create_project("rom", root_dir=root, set_active=False, auto_rename_on_conflict=False)

            renamed = create_project("rom", root_dir=root, set_active=False, auto_rename_on_conflict=True)
            self.assertTrue(renamed.name.startswith("rom_"))

    def test_list_and_delete_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_project("proj1", root_dir=root, set_active=False)
            create_project("proj2", root_dir=root, set_active=False)

            projects = list_projects(root_dir=root)
            self.assertEqual(len(projects), 2)
            names = [p.name for p, _ in projects]
            self.assertIn("proj1", names)
            self.assertIn("proj2", names)

            # Delete proj1
            del_dir = delete_project("proj1", root_dir=root)
            self.assertFalse(del_dir.exists())

            projects_after = list_projects(root_dir=root)
            self.assertEqual(len(projects_after), 1)
            self.assertEqual(projects_after[0][0].name, "proj2")

    def test_create_and_delete_split_project(self):
        with tempfile.TemporaryDirectory() as tmp_io, tempfile.TemporaryDirectory() as tmp_work:
            io_root = Path(tmp_io)
            work_root = Path(tmp_work)

            project = create_project(
                name="split_test",
                io_root=io_root,
                work_root=work_root,
                description="Split test",
                set_active=False,
            )

            self.assertEqual(project.name, "split_test")
            io_dir = io_root / "DNA_split_test"
            work_dir = work_root / "DNA_split_test"

            self.assertTrue(io_dir.is_dir())
            self.assertTrue((io_dir / "out").is_dir())
            self.assertTrue(work_dir.is_dir())
            self.assertTrue((work_dir / "config").is_dir())
            self.assertTrue((work_dir / "project.toml").is_file())
            self.assertTrue((io_dir / "project.toml").is_file())

            # Resolve project
            resolved = resolve_project("split_test", io_root=io_root, work_root=work_root)
            self.assertEqual(resolved.name, "split_test")
            self.assertEqual(resolved.paths.io_dir, io_dir)
            self.assertEqual(resolved.paths.work_dir, work_dir)

            # Delete project should remove both io_dir and work_dir
            del_dir = delete_project("split_test", io_root=io_root, work_root=work_root)
            self.assertFalse(io_dir.exists())
            self.assertFalse(work_dir.exists())


if __name__ == "__main__":
    unittest.main()
