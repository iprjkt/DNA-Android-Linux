"""Unit tests for Phase 7 Terminal User Interface (TUI)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dna_core.paths import ProjectPaths
from dna_core.project import Project
from dna_tui.app import (
    MenuItem,
    TUIState,
    get_menu_items,
    handle_menu_selection,
    start_tui,
)


class TestTUI(unittest.TestCase):
    def test_default_state_and_home_items(self):
        state = TUIState()
        self.assertEqual(state.menu_stack, ["home"])
        self.assertIsNone(state.active_project)

        items = get_menu_items(state)
        keys = [item.key for item in items]
        self.assertIn("select_proj", keys)
        self.assertIn("create_proj", keys)
        self.assertIn("list_proj", keys)
        self.assertIn("doctor", keys)
        self.assertIn("exit", keys)

    def test_home_items_with_active_project(self):
        with tempfile.TemporaryDirectory() as td:
            p_dir = Path(td) / "DNA_my_project"
            paths = ProjectPaths(project_dir=p_dir)
            paths.ensure_layout()
            proj = Project(paths=paths)

            state = TUIState(active_project=proj)
            items = get_menu_items(state)
            keys = [item.key for item in items]
            self.assertIn("goto_project", keys)
            self.assertIn("Open Project: my_project", items[0].label)

    def test_project_menu_structure(self):
        state = TUIState(menu_stack=["home", "project"])
        items = get_menu_items(state)
        keys = [item.key for item in items]

        self.assertIn("menu_unpack", keys)
        self.assertIn("menu_repack", keys)
        self.assertIn("menu_convert", keys)
        self.assertIn("menu_rom", keys)
        self.assertIn("menu_patch", keys)
        self.assertIn("menu_jar", keys)
        self.assertIn("menu_plugin", keys)
        self.assertIn("back", keys)

    def test_submenu_items(self):
        # ROM submenu
        rom_state = TUIState(menu_stack=["home", "project", "rom"])
        rom_items = get_menu_items(rom_state)
        rom_keys = [i.key for i in rom_items]
        self.assertIn("act_rom_debloat_gl", rom_keys)
        self.assertIn("act_rom_remove_oat", rom_keys)
        self.assertIn("act_rom_make_rw", rom_keys)
        self.assertIn("act_rom_decrypt", rom_keys)

        # Patch submenu
        patch_state = TUIState(menu_stack=["home", "project", "patch"])
        patch_items = get_menu_items(patch_state)
        patch_keys = [i.key for i in patch_items]
        self.assertIn("act_patch_vbmeta", patch_keys)
        self.assertIn("act_patch_integrity", patch_keys)
        self.assertIn("act_patch_safetycore", patch_keys)

        # Jar submenu
        jar_state = TUIState(menu_stack=["home", "project", "jar"])
        jar_items = get_menu_items(jar_state)
        jar_keys = [i.key for i in jar_items]
        self.assertIn("act_jar_dsv", jar_keys)
        self.assertIn("act_jar_dss", jar_keys)
        self.assertIn("act_jar_patch_all", jar_keys)

    def test_menu_navigation_handling(self):
        mock_scr = MagicMock()
        state = TUIState(menu_stack=["home", "project"])

        # Enter submenu
        sel_unpack = MenuItem("menu_unpack", "Unpack", "Desc")
        res = handle_menu_selection(mock_scr, state, sel_unpack)
        self.assertTrue(res)
        self.assertEqual(state.menu_stack, ["home", "project", "unpack"])

        # Back
        sel_back = MenuItem("back", "Back", "Desc")
        res = handle_menu_selection(mock_scr, state, sel_back)
        self.assertTrue(res)
        self.assertEqual(state.menu_stack, ["home", "project"])

        # Exit
        sel_exit = MenuItem("exit", "Exit", "Desc")
        res = handle_menu_selection(mock_scr, state, sel_exit)
        self.assertFalse(res)

    def test_start_tui_non_interactive_fallback(self):
        """Verify start_tui falls back cleanly when not in an interactive TTY."""
        with patch("sys.stdin.isatty", return_value=False):
            # Must not crash
            start_tui()


if __name__ == "__main__":
    unittest.main()
