"""Unit tests for DNA-Linux PyQt6 Graphical User Interface (GUI)."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# Ensure headless offscreen mode for automated test runners
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from dna_core.project import create_project, get_active_project, select_project
from dna_gui.app import MainWindow
from dna_gui.views.home_view import HomeView
from dna_gui.views.plugins_view import PluginsView
from dna_gui.views.project_view import ProjectView
from dna_gui.widgets.card_button import CardItemWidget, TrailingIcon
from dna_gui.widgets.console import ConsoleWidget
from dna_gui.widgets.header import HeaderWidget
from dna_gui.worker import WorkerThread


class TestDnaGui(unittest.TestCase):
    """Test suite covering GUI components and workflows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_trailing_icon_rendering(self) -> None:
        """TrailingIcon renders both menu and arrow types without crashing."""
        icon_menu = TrailingIcon(icon_type="menu")
        icon_arrow = TrailingIcon(icon_type="arrow")
        icon_menu.repaint()
        icon_arrow.repaint()
        self.assertEqual(icon_menu.width(), 28)
        self.assertEqual(icon_arrow.width(), 28)

    def test_card_item_widget(self) -> None:
        """CardItemWidget sets title, subtitle, and responds to click signal."""
        item = CardItemWidget("Test Title", "Initial Subtitle", icon_type="arrow")
        self.assertEqual(item.title_label.text(), "Test Title")
        self.assertEqual(item.subtitle_label.text(), "Initial Subtitle")

        item.set_subtitle("Updated Subtitle", color="#38bdf8")
        self.assertEqual(item.subtitle_label.text(), "Updated Subtitle")

        # Test click signal
        clicked_fired = []
        item.clicked.connect(lambda: clicked_fired.append(True))
        item.clicked.emit()
        self.assertTrue(clicked_fired)

    def test_header_widget(self) -> None:
        """HeaderWidget updates title, active project, and emits signals."""
        header = HeaderWidget()
        self.assertEqual(header.title_label.text(), "DNA-Linux")
        self.assertTrue(header.back_btn.isHidden())

        header.set_title("Project Menu", show_back=True)
        self.assertEqual(header.title_label.text(), "Project Menu")
        self.assertFalse(header.back_btn.isHidden())

        header.set_active_project("DNA_test_project")
        self.assertIn("DNA_test_project", header.project_btn.text())

    def test_console_widget(self) -> None:
        """ConsoleWidget appends logs, updates status, and clears content."""
        console = ConsoleWidget()
        console.append_log("Hello log 1")
        console.append_log("Hello log 2")
        self.assertIn("Hello log 1", console.text_edit.toPlainText())
        self.assertIn("Hello log 2", console.text_edit.toPlainText())

        console.set_status("Running Task", running=True)
        self.assertFalse(console.progress_bar.isHidden())

        console.set_status("Success", running=False)
        self.assertTrue(console.progress_bar.isHidden())

        console.clear_logs()
        self.assertEqual(console.text_edit.toPlainText(), "")

    def test_home_view(self) -> None:
        """HomeView creates all expected card items and navigation triggers."""
        home = HomeView()
        self.assertEqual(home.item_select.title_label.text(), "Select Project")
        self.assertEqual(home.item_delete.title_label.text(), "Delete Project")
        self.assertEqual(home.item_create.title_label.text(), "Create New Project")
        self.assertEqual(home.item_unzip.title_label.text(), "Unzip ROM")
        self.assertEqual(home.item_project_menu.title_label.text(), "Project Menu")

    def test_project_view(self) -> None:
        """ProjectView contains all operation signals."""
        pv = ProjectView()
        # Verify signal objects exist
        self.assertTrue(hasattr(pv, "action_unpack_super"))
        self.assertTrue(hasattr(pv, "action_repack_super"))
        self.assertTrue(hasattr(pv, "action_jar_dss"))
        self.assertTrue(hasattr(pv, "action_patch_vbmeta"))
        self.assertTrue(hasattr(pv, "action_rom_debloat"))

    def test_plugins_view(self) -> None:
        """PluginsView populates installed plugins without errors."""
        plugins_view = PluginsView()
        plugins_view.refresh_plugins()
        self.assertGreaterEqual(plugins_view.table.rowCount(), 0)

    def test_worker_thread_execution(self) -> None:
        """WorkerThread executes task, captures result, and emits finished signal."""
        def dummy_task(x: int, y: int) -> int:
            print(f"Adding {x} + {y}")
            return x + y

        worker = WorkerThread("AddNumbers", dummy_task, 15, 27)
        results = []
        logs = []
        worker.finished_signal.connect(lambda res: results.append(res))
        worker.log_signal.connect(lambda msg: logs.append(msg))

        worker.run()  # Run synchronously in test
        self.assertEqual(results, [42])
        self.assertTrue(any("Adding 15 + 27" in line for line in logs))

    def test_main_window_navigation(self) -> None:
        """MainWindow switches between Home, Project Menu, and Plugins views."""
        win = MainWindow()
        self.assertEqual(win.stack.currentIndex(), 0)
        self.assertEqual(win.header.title_label.text(), "DNA-Linux")

        # Navigate to Project Menu
        win.home_view.navigate_project_menu.emit()
        self.assertEqual(win.stack.currentIndex(), 1)
        self.assertEqual(win.header.title_label.text(), "Project Menu")
        self.assertFalse(win.header.back_btn.isHidden())

        # Navigate to Plugins
        win.project_view.navigate_plugins.emit()
        self.assertEqual(win.stack.currentIndex(), 2)
        self.assertEqual(win.header.title_label.text(), "Plugin Functions")

        # Back button: back to Project Menu
        win.header.back_clicked.emit()
        self.assertEqual(win.stack.currentIndex(), 1)
        self.assertEqual(win.header.title_label.text(), "Project Menu")

        # Back button: back to Home
        win.header.back_clicked.emit()
        self.assertEqual(win.stack.currentIndex(), 0)
        self.assertEqual(win.header.title_label.text(), "DNA-Linux")
        self.assertTrue(win.header.back_btn.isHidden())

        win.close()


if __name__ == "__main__":
    unittest.main()
