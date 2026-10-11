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
        self.assertEqual(header.title_label.text(), "DNA-Android")
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
        self.assertTrue(console.exit_btn.isHidden())

        console.set_status("Success", running=False)
        self.assertTrue(console.progress_bar.isHidden())
        self.assertFalse(console.exit_btn.isHidden())

        console.copy_logs()
        self.assertEqual(console.copy_btn.text(), "COPIED TO CLIPBOARD")

        console.clear_logs()
        self.assertEqual(console.text_edit.toPlainText(), "")
        self.assertTrue(console.exit_btn.isHidden())

    def test_about_dialog(self) -> None:
        """AboutDialog initializes with version, title, and toggle switch."""
        from dna_gui.widgets.dialogs import AboutDialog
        about = AboutDialog()
        self.assertIn("About DNA", about.windowTitle())
        self.assertIsNotNone(about.toggle)
        # Test toggle interaction
        toggled_vals = []
        about.transparent_toggled.connect(lambda val: toggled_vals.append(val))
        about.toggle.click()
        self.assertEqual(toggled_vals, [True])

    def test_delete_project_dialog(self) -> None:
        """DeleteProjectDialog lists projects in ~/DNA."""
        from dna_gui.widgets.dialogs import DeleteProjectDialog
        dlg = DeleteProjectDialog()
        self.assertEqual(dlg.windowTitle(), "Delete Project")
        self.assertIsNotNone(dlg.list_widget)

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
        """MainWindow switches between Home, Project Menu, and Plugins views with right-side log terminal."""
        win = MainWindow()
        self.assertEqual(win.stack.currentIndex(), 0)
        self.assertEqual(win.header.title_label.text(), "DNA-Android")

        # Verify splitter and side-by-side terminal
        self.assertIsNotNone(win.splitter)
        self.assertEqual(win.splitter.count(), 2)
        self.assertEqual(win.splitter.widget(1), win.console)

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
        self.assertEqual(win.header.title_label.text(), "DNA-Android")
        self.assertTrue(win.header.back_btn.isHidden())

        win.close()

    def test_custom_background_workflow(self) -> None:
        """AboutDialog manages custom background and MainWindow renders pixmap."""
        from dna_gui.widgets.dialogs import AboutDialog
        about = AboutDialog()
        self.assertIsNotNone(about.btn_choose_bg)
        self.assertIsNotNone(about.btn_clear_bg)

        signals_received = []
        about.background_changed.connect(lambda p: signals_received.append(p))
        about._clear_wallpaper()
        self.assertIn("", signals_received)

        # MainWindow background pixmap test
        win = MainWindow()
        with TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "test_bg.png"
            from PyQt6.QtGui import QImage
            img = QImage(100, 100, QImage.Format.Format_RGB32)
            img.fill(Qt.GlobalColor.blue)
            img.save(str(img_path))

            win._load_background_image(str(img_path))
            self.assertIsNotNone(win.background_pixmap)
            self.assertFalse(win.background_pixmap.isNull())
            win.repaint()

            win._load_background_image(None)
            self.assertIsNone(win.background_pixmap)

        win.close()

    def test_main_window_action_repack_img_dialog(self) -> None:
        """Verify _action_repack_img executes without NameError on QDialog."""
        from unittest.mock import patch
        from dna_core.paths import ProjectPaths
        from dna_gui.widgets.dialogs import RepackSingleImgDialog
        from PyQt6.QtWidgets import QDialog

        win = MainWindow()
        with TemporaryDirectory() as tmpdir:
            proj_dir = Path(tmpdir)
            p = ProjectPaths(project_dir=proj_dir)
            p.images.mkdir(parents=True, exist_ok=True)
            p.unpacked.mkdir(parents=True, exist_ok=True)
            (p.unpacked / "system").mkdir()

            with patch.object(win, "_require_project", return_value=p):
                with patch.object(RepackSingleImgDialog, "exec", return_value=QDialog.DialogCode.Rejected):
                    win._action_repack_img()

                with patch.object(RepackSingleImgDialog, "exec", return_value=QDialog.DialogCode.Accepted):
                    with patch.object(win, "run_async_task") as mock_task:
                        win._action_repack_img()
                        mock_task.assert_called_once()
        win.close()

    def test_file_select_and_stepper_widgets(self) -> None:
        """FileSelectField, NumberStepper, and CheckboxCard function correctly."""
        from dna_gui.widgets.dialogs import CheckboxCard, FileSelectField, NumberStepper

        # CheckboxCard
        chk = CheckboxCard("Test Check", "Subtitle here", checked=True)
        self.assertTrue(chk.is_checked())
        chk.set_checked(False)
        self.assertFalse(chk.is_checked())

        # NumberStepper
        stepper = NumberStepper(min_val=1, max_val=22, default_val=3)
        self.assertEqual(stepper.get_value(), 3)
        stepper._increment()
        self.assertEqual(stepper.get_value(), 4)
        stepper._decrement()
        self.assertEqual(stepper.get_value(), 3)

        # FileSelectField
        f1 = Path("/tmp/a.img")
        f2 = Path("/tmp/b.img")
        field = FileSelectField(candidate_files=[f1, f2], subtitle="Hint text")
        self.assertEqual(len(field.get_selected_files()), 0)
        field.set_selected_files([f1])
        self.assertEqual(field.get_selected_files(), [f1])
        self.assertEqual(field.badge.text(), "1")

    def test_extended_operation_dialogs(self) -> None:
        """Instantiate and verify default parameters for all extended operation dialogs."""
        from dna_gui.widgets.dialogs import (
            CorePatchDsvDialog,
            DebloatRomDialog,
            DisableSecureScreenshotDialog,
            ImgSimgDialog,
            PatchVbmetaDialog,
            RemoveApkProtectionDialog,
            RepackSingleImgDialog,
            RepackSuperDialog,
            RepackZstdDialog,
            UnpackImgDialog,
            UnpackZstdDialog,
        )

        with TemporaryDirectory() as tmpdir:
            from dna_core.paths import ProjectPaths
            proj_dir = Path(tmpdir)
            p = ProjectPaths(project_dir=proj_dir)
            p.images.mkdir(parents=True, exist_ok=True)
            p.unpacked.mkdir(parents=True, exist_ok=True)
            (p.images / "system.img").touch()
            (p.images / "vendor.img").touch()
            (p.images / "test.zst").touch()
            (p.images / "vbmeta.img").touch()
            (p.unpacked / "system").mkdir(parents=True, exist_ok=True)

            # 1. UnpackImgDialog
            d_unpack_img = UnpackImgDialog(proj=p)
            self.assertFalse(d_unpack_img.get_delete_source())
            self.assertGreaterEqual(len(d_unpack_img.file_picker.candidate_files), 1)

            # 2. UnpackZstdDialog
            d_unpack_zstd = UnpackZstdDialog(proj=p)
            self.assertFalse(d_unpack_zstd.get_delete_source())
            self.assertGreaterEqual(len(d_unpack_zstd.file_picker.candidate_files), 1)

            # 3. RepackZstdDialog
            d_repack_zstd = RepackZstdDialog(proj=p)
            self.assertEqual(d_repack_zstd.get_compression_level(), 3)
            self.assertFalse(d_repack_zstd.get_delete_source())

            # 4. RepackSingleImgDialog
            d_repack_single = RepackSingleImgDialog(proj=p)
            params_single = d_repack_single.get_parameters()
            self.assertEqual(params_single["partition"], "system")
            self.assertEqual(params_single["fs_type"], "ext4")

            # 5. RepackSuperDialog
            d_repack_super = RepackSuperDialog(proj=p)
            params_super = d_repack_super.get_parameters()
            self.assertEqual(params_super["slot_type"], "virtual_ab")
            self.assertTrue(params_super["sparse"])
            self.assertGreater(params_super["device_size"], 0)

            # 6. ImgSimgDialog
            d_simg = ImgSimgDialog(proj=p)
            params_simg = d_simg.get_parameters()
            self.assertIn("Auto detect", params_simg["mode"])

            # 7. CorePatchDsvDialog
            d_dsv = CorePatchDsvDialog()
            params_dsv = d_dsv.get_parameters()
            self.assertEqual(params_dsv["android_version"], "Android 13+")
            self.assertFalse(params_dsv["remove_invoke_custom"])

            # 8. DisableSecureScreenshotDialog
            d_dss = DisableSecureScreenshotDialog()
            params_dss = d_dss.get_parameters()
            self.assertEqual(params_dss["android_version"], "Android 13+")
            self.assertFalse(params_dss["remove_invoke_custom"])

            # 9. RemoveApkProtectionDialog
            d_apk_prot = RemoveApkProtectionDialog()
            params_apk = d_apk_prot.get_parameters()
            self.assertEqual(params_apk["android_version"], "Android 13+")
            self.assertFalse(params_apk["remove_invoke_custom"])

            # 10. PatchVbmetaDialog
            d_vbmeta = PatchVbmetaDialog(proj=p)
            params_vbmeta = d_vbmeta.get_parameters()
            self.assertEqual(params_vbmeta["mode"], "verity")
            self.assertFalse(params_vbmeta["delete_source"])

            # 11. DebloatRomDialog
            d_debloat = DebloatRomDialog()
            self.assertEqual(d_debloat.get_rom_type(), "global")

    def test_repack_single_img_dynamic_detection(self) -> None:
        """Verify dynamic partition detection without hardcoding and mode switching."""
        from dna_core.paths import ProjectPaths
        from dna_gui.widgets.dialogs import RepackSingleImgDialog, get_repack_partition_candidates

        with TemporaryDirectory() as tmpdir:
            proj_dir = Path(tmpdir)
            p = ProjectPaths(project_dir=proj_dir)

            # 1. Empty project: must return empty list (no fake hardcoded fallbacks!)
            self.assertEqual(get_repack_partition_candidates(p), [])
            d_empty = RepackSingleImgDialog(proj=p)
            self.assertEqual(len(d_empty.file_picker.candidate_files), 0)

            # 2. Project with real partitions
            p.images.mkdir(parents=True, exist_ok=True)
            p.unpacked.mkdir(parents=True, exist_ok=True)
            (p.unpacked / "custom_sys").mkdir()
            (p.unpacked / "custom_vendor").mkdir()
            (p.images / "boot.img").touch()
            (p.images / "super.img").touch()  # Should be excluded!

            all_cands = get_repack_partition_candidates(p, mode="all")
            cand_names = [c.name for c in all_cands]
            self.assertIn("custom_sys", cand_names)
            self.assertIn("custom_vendor", cand_names)
            self.assertIn("boot.img", cand_names)
            self.assertNotIn("super.img", cand_names)

            # Test mode filtering
            folder_cands = get_repack_partition_candidates(p, mode="folder")
            self.assertEqual({c.name for c in folder_cands}, {"custom_sys", "custom_vendor"})

            img_cands = get_repack_partition_candidates(p, mode="img")
            self.assertEqual({c.name for c in img_cands}, {"boot.img"})

            # RepackSingleImgDialog switching between IMG and Folder
            dlg = RepackSingleImgDialog(proj=p)
            self.assertGreaterEqual(len(dlg.file_picker.candidate_files), 1)

            dlg.combo_from.setCurrentText("Folder")
            folder_files = [f.name for f in dlg.file_picker.candidate_files]
            self.assertIn("custom_sys", folder_files)
            self.assertNotIn("boot.img", folder_files)

            dlg.combo_from.setCurrentText("IMG")
            img_files = [f.name for f in dlg.file_picker.candidate_files]
            self.assertIn("boot.img", img_files)
            self.assertNotIn("custom_sys", img_files)

            # Test parameters
            dlg.file_picker.set_selected_files([p.images / "boot.img"])
            params = dlg.get_parameters()
            self.assertEqual(params["partition"], "boot")
            self.assertEqual(params["selected_files"], [p.images / "boot.img"])
            self.assertIn(params["fs_type"], ["ext4", "erofs", "f2fs"])
            self.assertFalse(params["compress_ext4"])
            self.assertFalse(params["remove_avb"])

            dlg.switch_compress_ext4.setChecked(True)
            dlg.switch_remove_avb.setChecked(True)
            params = dlg.get_parameters()
            self.assertTrue(params["compress_ext4"])
            self.assertTrue(params["remove_avb"])

    def test_file_list_select_browsing(self) -> None:
        """Verify FileListSelectDialog allows manual browsing and adding files/folders."""
        from dna_gui.widgets.dialogs import FileListSelectDialog

        with TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "part1.img"
            f1.touch()
            f2 = Path(tmpdir) / "my_custom_folder"
            f2.mkdir()

            dlg = FileListSelectDialog("Test Selector", files=[])
            self.assertEqual(len(dlg.all_files), 0)
            self.assertEqual(len(dlg.get_selected_files()), 0)

            # Add file manually
            dlg._add_custom_path(f1)
            self.assertEqual(len(dlg.all_files), 1)
            self.assertEqual(dlg.get_selected_files(), [f1])

            # Add folder manually
            dlg._add_custom_path(f2)
            self.assertEqual(len(dlg.all_files), 2)
            self.assertEqual(dlg.get_selected_files(), [f1, f2])

            dlg._add_custom_path(f1)
            self.assertEqual(len(dlg.all_files), 2)

    def test_open_project_creator(self) -> None:
        """Verify _open_project_creator executes with CreateProjectDialog."""
        from unittest.mock import patch
        from dna_gui.widgets.dialogs import CreateProjectDialog
        from PyQt6.QtWidgets import QDialog

        win = MainWindow()
        with patch.object(CreateProjectDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            win._open_project_creator()
        win.close()

    def test_create_project_dialog_custom_directories(self) -> None:
        """Verify CreateProjectDialog accepts custom IO and Work directories."""
        from dna_gui.widgets.dialogs import CreateProjectDialog

        dlg = CreateProjectDialog()
        dlg.edit_name.setText("custom_test")
        dlg.edit_io.setText("/tmp/custom_io")
        dlg.edit_work.setText("/tmp/custom_work")
        dlg.edit_desc.setText("Custom note")
        dlg.chk_save_defaults.setChecked(True)

        name, io_p, work_p, desc, save_def = dlg.get_values()
        self.assertEqual(name, "custom_test")
        self.assertEqual(io_p, Path("/tmp/custom_io").resolve())
        self.assertEqual(work_p, Path("/tmp/custom_work").resolve())
        self.assertEqual(desc, "Custom note")
        self.assertTrue(save_def)
        dlg.close()

    def test_select_project_dialog_roots_management(self) -> None:
        """Verify SelectProjectDialog displays and updates custom workspace roots."""
        from dna_gui.widgets.dialogs import SelectProjectDialog
        from dna_core.config import set_workspace_roots, reset_workspace_roots
        from dna_core.paths import get_default_io_root, get_default_work_root

        with TemporaryDirectory() as tmpdir:
            custom_io = Path(tmpdir) / "custom_io"
            custom_work = Path(tmpdir) / "custom_work"
            set_workspace_roots(io_root=custom_io, work_root=custom_work)

            dlg = SelectProjectDialog()
            self.assertEqual(dlg.lbl_io_path.text(), str(custom_io.resolve()))
            self.assertEqual(dlg.lbl_work_path.text(), str(custom_work.resolve()))

            # Reset roots
            dlg._reset_roots()
            self.assertEqual(dlg.lbl_io_path.text(), str(get_default_io_root()))
            self.assertEqual(dlg.lbl_work_path.text(), str(get_default_work_root()))
            dlg.close()


if __name__ == "__main__":
    unittest.main()

