"""Main application window and coordinator for DNA-Linux GUI."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from dna_core.config import (
    GlobalConfig,
    get_background_image,
    set_background_image,
    set_workspace_roots,
)
from dna_core.debloat import debloat_rom
from dna_core.jar import (
    patch_core_patch_dsv,
    patch_disable_secure_screenshot,
    patch_remove_apk_protection,
)
from dna_core.patch import (
    patch_disable_ota,
    patch_disable_xiaomi_services,
    patch_integrity_fix,
    patch_privapp_permissions,
    patch_safetycore,
    patch_vbmeta,
)
from dna_core.plugin import run_plugin
from dna_core.project import (
    ProjectPaths,
    create_project,
    get_active_project,
    select_project,
)
from dna_core.repack import repack_image, repack_super, repack_zstd
from dna_core.resize import resize_ext4
from dna_core.rom import unzip_rom
from dna_core.rom_tweaks import decrypt_rom, make_rom_rw, remove_oat_directories
from dna_core.sdat import img2sdat, sdat2img
from dna_core.sparse import merge_sparse_chunks, raw_to_sparse, sparse_to_raw, split_sparse_image
from dna_core.tools import run_tool
from dna_core.unpack import (
    unpack_bin,
    unpack_brotli,
    unpack_dat,
    unpack_image,
    unpack_super,
    unpack_zstd,
)
from dna_gui.theme import DARK_THEME_QSS
from dna_gui.views.home_view import HomeView
from dna_gui.views.plugins_view import PluginsView
from dna_gui.views.project_view import ProjectView
from dna_gui.widgets.console import ConsoleWidget
from dna_gui.widgets.dialogs import (
    AboutDialog,
    ConfirmDialog,
    CorePatchDsvDialog,
    CreateProjectDialog,
    DebloatRomDialog,
    DeleteProjectDialog,
    DisableSecureScreenshotDialog,
    DoctorDialog,
    ImgSimgDialog,
    InputDialog,
    PatchVbmetaDialog,
    RemoveApkProtectionDialog,
    RepackSingleImgDialog,
    RepackSuperDialog,
    RepackZstdDialog,
    SelectProjectDialog,
    UnpackImgDialog,
    UnpackSuperDialog,
    UnpackZstdDialog,
)
from dna_gui.widgets.header import HeaderWidget
from dna_gui.worker import WorkerThread


class MainWindow(QMainWindow):
    """Primary desktop window hosting navigation screens, worker thread, and right-side log terminal."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DNA-Android — Android ROM Toolkit")
        self.resize(1120, 780)
        self.setMinimumSize(880, 600)

        self.worker: WorkerThread | None = None
        self.is_transparent_ui: bool = False
        self.background_pixmap: QPixmap | None = None
        self.setStyleSheet(DARK_THEME_QSS)

        # Set original DNA-Android logo
        icon_png = Path(__file__).resolve().parent.parent / "data" / "icons" / "dna.png"
        icon_svg = Path(__file__).resolve().parent.parent / "data" / "icons" / "dna.svg"
        if icon_png.exists():
            self.setWindowIcon(QIcon(str(icon_png)))
        elif icon_svg.exists():
            self.setWindowIcon(QIcon(str(icon_svg)))

        # Central layout
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Navigation Header
        self.header = HeaderWidget(self)
        self.header.back_clicked.connect(self._on_back_clicked)
        self.header.project_badge_clicked.connect(self._open_project_selector)
        self.header.doctor_clicked.connect(self._open_doctor)
        self.header.info_clicked.connect(self._open_about)
        self.header.quit_clicked.connect(self.close)
        main_layout.addWidget(self.header)

        # Horizontal Splitter: Left Navigation Stack | Right Log Terminal UI
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setContentsMargins(12, 10, 12, 12)
        self.splitter.setHandleWidth(6)

        # Left Container for Stacked Screens
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        left_layout.addWidget(self.stack)
        self.splitter.addWidget(left_container)

        # View 0: HomeView
        self.home_view = HomeView()
        self.home_view.navigate_project_menu.connect(lambda: self._switch_view(1, "Project Menu"))
        self.home_view.request_select_project.connect(self._open_project_selector)
        self.home_view.request_create_project.connect(self._open_project_creator)
        self.home_view.request_delete_project.connect(self._open_project_deleter)
        self.home_view.request_unzip_rom.connect(self._action_unzip_rom)
        self.stack.addWidget(self.home_view)

        # View 1: ProjectView
        self.project_view = ProjectView()
        self.project_view.navigate_plugins.connect(lambda: self._switch_view(2, "Plugin Functions"))
        self._wire_project_view_actions()
        self.stack.addWidget(self.project_view)

        # View 2: PluginsView
        self.plugins_view = PluginsView()
        self.plugins_view.request_run_plugin.connect(self._action_run_plugin)
        self.stack.addWidget(self.plugins_view)

        # Right Side Log Terminal (mirroring Screenshot_2026-10-10-19-24-56-881_com.dna.tools.jpg)
        self.console = ConsoleWidget(self)
        self.splitter.addWidget(self.console)

        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 6)
        self.splitter.setSizes([480, 580])
        self.splitter.setChildrenCollapsible(False)

        main_layout.addWidget(self.splitter, stretch=1)

        # Load persisted background wallpaper if configured
        bg_init = get_background_image()
        if bg_init:
            self._load_background_image(bg_init)

        # Sync active project on launch
        self._refresh_active_project_state()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        if self.background_pixmap and not self.background_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            scaled = self.background_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

            # Translucent dark scrim layer so cards, text, and terminal pop cleanly
            painter.fillRect(self.rect(), QColor(14, 15, 18, 205))

    def _switch_view(self, index: int, title: str) -> None:
        self.stack.setCurrentIndex(index)
        show_back = index > 0
        self.header.set_title(title, show_back=show_back)

    def _on_back_clicked(self) -> None:
        curr = self.stack.currentIndex()
        if curr == 2:
            self._switch_view(1, "Project Menu")
        elif curr == 1:
            self._switch_view(0, "DNA-Android")

    def _open_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.background_changed.connect(self._on_background_changed)
        dlg.transparent_toggled.connect(self._on_transparent_toggled)
        dlg.exec()

    def _on_background_changed(self, path: str) -> None:
        self._load_background_image(path)

    def _load_background_image(self, path: str | None) -> None:
        if path and Path(path).is_file():
            pix = QPixmap(path)
            if not pix.isNull():
                self.background_pixmap = pix
                self.centralWidget().setStyleSheet("background-color: transparent;")
            else:
                self.background_pixmap = None
                self.centralWidget().setStyleSheet("")
        else:
            self.background_pixmap = None
            self.centralWidget().setStyleSheet("")
        self.update()

    def _on_transparent_toggled(self, enabled: bool) -> None:
        self.is_transparent_ui = enabled

    def _refresh_active_project_state(self) -> None:
        active = get_active_project()
        p_name = active.name if active else None
        self.header.set_active_project(p_name)
        self.home_view.update_active_project()

    def _open_project_selector(self) -> None:
        dlg = SelectProjectDialog(self)
        if dlg.exec() == SelectProjectDialog.DialogCode.Accepted:
            self._refresh_active_project_state()

    def _open_project_creator(self) -> None:
        dlg = CreateProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, io_root, work_root, desc, save_default = dlg.get_values()
            if save_default:
                set_workspace_roots(io_root=io_root, work_root=work_root)
            try:
                proj = create_project(name, io_root=io_root, work_root=work_root, description=desc)
                self._refresh_active_project_state()
                QMessageBox.information(
                    self,
                    "Project Created",
                    f"Created and activated project '{proj.name}'!\nIO: {proj.paths.io_dir}\nWork: {proj.paths.work_dir}",
                )
            except Exception as exc:
                QMessageBox.critical(self, "Creation Error", str(exc))

    def _open_project_deleter(self) -> None:
        dlg = DeleteProjectDialog(self)
        if dlg.exec() == DeleteProjectDialog.DialogCode.Accepted:
            self._refresh_active_project_state()

    def _open_doctor(self) -> None:
        dlg = DoctorDialog(self)
        dlg.exec()

    def _require_project(self) -> ProjectPaths | None:
        active = get_active_project()
        if not active:
            QMessageBox.warning(
                self,
                "No Active Project",
                "Please select or create an active project workspace first.",
            )
            self._open_project_selector()
            active = get_active_project()
            if not active:
                return None
        return active.paths

    def run_async_task(self, task_name: str, target: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Run an operation asynchronously in the WorkerThread with live logging."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Task In Progress",
                "Another task is currently running. Please wait for it to finish.",
            )
            return

        self.console.clear_logs()
        self.console.set_status(task_name, running=True)

        self.worker = WorkerThread(task_name, target, *args, **kwargs)
        self.worker.log_signal.connect(self.console.append_log)
        self.worker.finished_signal.connect(lambda res: self._on_task_finished(task_name, res))
        self.worker.failed_signal.connect(lambda err: self._on_task_failed(task_name, err))
        self.worker.start()

    def _on_task_finished(self, task_name: str, result: Any) -> None:
        self.console.set_status(task_name, running=False, error=False)
        self._refresh_active_project_state()

    def _on_task_failed(self, task_name: str, error_msg: str) -> None:
        self.console.set_status(task_name, running=False, error=True)
        self.console.append_log(f"[Error] {task_name} failed: {error_msg}")
        QMessageBox.critical(self, "Task Failed", f"{task_name} encountered an error:\n\n{error_msg}")


    # -----------------------------------------------------------------
    # Home View Actions
    # -----------------------------------------------------------------
    def _action_unzip_rom(self) -> None:
        proj = self._require_project()
        if not proj:
            return

        testbed_dir = "/run/media/fxxyz73/sigeonpex/ROM_Fastboot_Recovery_ISO"
        start_dir = testbed_dir if Path(testbed_dir).is_dir() else str(proj.project_dir)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ROM ZIP Archive",
            start_dir,
            "ZIP Archives (*.zip);;All Files (*)",
        )
        if not file_path:
            return

        confirm = ConfirmDialog(
            "Unzip ROM",
            f"Extract ROM ZIP:\n{file_path}\ninto project workspace:\n{proj.project_dir}?",
            confirm_text="Extract",
            parent=self,
        )
        if confirm.exec() == ConfirmDialog.DialogCode.Accepted:
            active = get_active_project()
            if active:
                self.run_async_task("Unzip ROM", unzip_rom, Path(file_path), active, delete_source=False)

    # -----------------------------------------------------------------
    # Project View Actions Wire-up
    # -----------------------------------------------------------------
    def _wire_project_view_actions(self) -> None:
        pv = self.project_view
        # Unpack
        pv.action_unpack_bin.connect(self._action_unpack_bin)
        pv.action_unpack_br.connect(self._action_unpack_br)
        pv.action_unpack_dat.connect(self._action_unpack_dat)
        pv.action_unpack_img.connect(self._action_unpack_img)
        pv.action_unpack_zstd.connect(self._action_unpack_zstd)
        pv.action_unpack_super.connect(self._action_unpack_super)

        # Repack
        pv.action_resize_img.connect(self._action_resize_img)
        pv.action_repack_img.connect(self._action_repack_img)
        pv.action_repack_zstd.connect(self._action_repack_zstd)
        pv.action_repack_super.connect(self._action_repack_super)

        # Convert
        pv.action_convert_simg.connect(self._action_convert_simg)
        pv.action_convert_dat_br.connect(self._action_convert_dat_br)
        pv.action_convert_merge_super.connect(self._action_convert_merge_super)
        pv.action_convert_split_super.connect(self._action_convert_split_super)

        # Jar
        pv.action_jar_dsv.connect(self._action_jar_dsv)
        pv.action_jar_apk_protection.connect(self._action_jar_apk_protection)
        pv.action_jar_dss.connect(self._action_jar_dss)

        # Patch
        pv.action_patch_vbmeta.connect(self._action_patch_vbmeta)
        pv.action_patch_integrity.connect(self._action_patch_integrity)
        pv.action_patch_safetycore.connect(self._action_patch_safetycore)
        pv.action_patch_privapp.connect(self._action_patch_privapp)
        pv.action_patch_ota.connect(self._action_patch_ota)
        pv.action_patch_xiaomi.connect(self._action_patch_xiaomi)

        # Rom
        pv.action_rom_debloat.connect(self._action_rom_debloat)
        pv.action_rom_remove_oat.connect(self._action_rom_remove_oat)
        pv.action_rom_make_rw.connect(self._action_rom_make_rw)
        pv.action_rom_decrypt.connect(self._action_rom_decrypt)

    # -----------------------------------------------------------------
    # Implementation of Specific Project Operations
    # -----------------------------------------------------------------
    def _action_unpack_bin(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        # Look for payload.bin in images/
        payload = proj.images / "payload.bin"
        if not payload.exists():
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Select payload.bin", str(proj.project_dir), "Payload (*.bin);;All Files (*)"
            )
            if not chosen:
                return
            payload = Path(chosen)

        self.run_async_task("Unpack payload.bin", unpack_bin, payload, proj.images)

    def _action_unpack_br(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        br_files = list(proj.images.glob("*.new.dat.br"))
        if br_files:
            target = br_files[0]
        else:
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Select Brotli Archive", str(proj.images), "Brotli (*.br);;All Files (*)"
            )
            if not chosen:
                return
            target = Path(chosen)

        out_dat = target.with_suffix("")
        self.run_async_task("Decompress Brotli", unpack_brotli, target, out_file=out_dat)

    def _action_unpack_dat(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dat_files = list(proj.images.glob("*.new.dat"))
        if dat_files:
            dat_file = dat_files[0]
            prefix = dat_file.name.replace(".new.dat", "")
            transfer_file = proj.images / f"{prefix}.transfer.list"
        else:
            chosen_dat, _ = QFileDialog.getOpenFileName(
                self, "Select system.new.dat", str(proj.images), "DAT (*.dat);;All Files (*)"
            )
            if not chosen_dat:
                return
            dat_file = Path(chosen_dat)
            chosen_tr, _ = QFileDialog.getOpenFileName(
                self, "Select .transfer.list", str(dat_file.parent), "Transfer List (*.transfer.list);;All Files (*)"
            )
            if not chosen_tr:
                return
            transfer_file = Path(chosen_tr)

        out_img = proj.images / f"{dat_file.stem.replace('.new', '')}.img"
        self.run_async_task("Convert DAT to Raw IMG", unpack_dat, transfer_file, dat_file, out_img=out_img)

    def _action_unpack_img(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = UnpackImgDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_files()
            del_src = dlg.get_delete_source()
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one partition image to unpack.")
                return

            def _do_unpack_all() -> None:
                for target in selected:
                    part_name = target.stem
                    out_dir = proj.unpacked / part_name
                    unpack_image(target, out_dir, delete_source=del_src)

            first_name = selected[0].name
            title_text = f"Unpack {first_name}" if len(selected) == 1 else f"Unpack {len(selected)} Images"
            self.run_async_task(title_text, _do_unpack_all)

    def _action_unpack_zstd(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = UnpackZstdDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_files()
            del_src = dlg.get_delete_source()
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one ZSTD file to unpack.")
                return

            def _do_unpack_zst() -> None:
                for target in selected:
                    out_img = target.with_suffix("")
                    unpack_zstd(target, out_file=out_img, delete_source=del_src)

            first_name = selected[0].name
            title_text = f"Decompress {first_name}" if len(selected) == 1 else f"Decompress {len(selected)} Archives"
            self.run_async_task(title_text, _do_unpack_zst)

    def _action_unpack_super(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        super_img = proj.images / "super.img"
        if not super_img.exists() and (proj.io_dir / "super.img").exists():
            super_img = proj.io_dir / "super.img"
        elif not super_img.exists():
            start_dir = str(proj.io_dir if proj.io_dir.is_dir() else proj.images)
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Select super.img", start_dir, "Super Image (super.img *.img);;All Files (*)"
            )
            if not chosen:
                return
            super_img = Path(chosen)

        dlg = UnpackSuperDialog(super_img=super_img, proj=proj, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            del_src = dlg.get_delete_source()
            auto_unpack = dlg.get_auto_unpack()
            partitions = dlg.get_selected_partitions()

            self.run_async_task(
                "Unpack super.img",
                unpack_super,
                super_img,
                proj.images,
                partitions=partitions,
                auto_unpack_imgs=auto_unpack,
                delete_source=del_src,
            )

    def _action_resize_img(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Select ext4 image to resize", str(proj.images), "Image (*.img);;All Files (*)"
        )
        if not chosen:
            return
        target = Path(chosen)

        size_mb, ok = QInputDialog.getInt(
            self, "Target Size", "Enter target size in MB (e.g. 4096):", 4096, 64, 65536
        )
        if not ok:
            return
        target_bytes = size_mb * 1024 * 1024
        self.run_async_task(f"Resize Image ({target.name})", resize_ext4, target, target_bytes)

    def _action_repack_img(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = RepackSingleImgDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            selected = dlg.get_selected_files()
            if not selected:
                first_name = params.get("partition")
                if first_name:
                    cand_path = proj.work_dir / first_name
                    if not cand_path.is_dir():
                        cand_path = proj.unpacked / first_name
                    if not cand_path.is_dir():
                        cand_path = proj.images / f"{first_name}.img"
                    if not cand_path.exists():
                        cand_path = proj.io_dir / f"{first_name}.img"
                    if cand_path.exists():
                        selected = [cand_path]
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one partition or image to repack.")
                return

            fs_type = params["fs_type"]
            fmt_raw = params["format"]
            if "dat.br" in fmt_raw or "br" in fmt_raw:
                fmt = "br"
            elif "dat" in fmt_raw:
                fmt = "dat"
            elif "sparse" in fmt_raw or "simg" in fmt_raw:
                fmt = "sparse"
            else:
                fmt = "raw"

            size_mb = params.get("custom_size_mb")
            size_bytes = (size_mb * 1024 * 1024) if size_mb else None
            brotli_level = params["brotli_level"]
            erofs_algo = params["erofs_algo"]
            erofs_level = params["erofs_level"]
            remove_avb = params.get("remove_avb", False)

            def _do_repack_all() -> None:
                for target in selected:
                    if target.is_dir():
                        part_name = target.name
                        in_dir = target
                    else:
                        part_name = target.stem
                        in_dir = proj.unpacked / part_name
                        if not in_dir.is_dir():
                            unpack_image(target, in_dir)

                    if remove_avb:
                        try:
                            decrypt_rom(in_dir)
                        except Exception:
                            pass

                    out_img = proj.out / f"{part_name}.img"
                    repack_image(
                        in_dir,
                        out_img=out_img,
                        fs_type=fs_type,
                        output_format=fmt,
                        size_bytes=size_bytes,
                        compress_erofs=erofs_algo,
                        erofs_level=erofs_level,
                        brotli_level=brotli_level,
                        project=proj,
                    )

            first_name = selected[0].name
            title_text = f"Repack {first_name} ({fs_type})" if len(selected) == 1 else f"Repack {len(selected)} Partitions ({fs_type})"
            self.run_async_task(title_text, _do_repack_all)

    def _action_repack_zstd(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = RepackZstdDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_files()
            del_src = dlg.get_delete_source()
            level = dlg.get_compression_level()
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one file to compress.")
                return

            def _do_repack_zst() -> None:
                for target in selected:
                    out_zst = target.with_suffix(target.suffix + ".zst")
                    repack_zstd(target, out_file=out_zst, level=level, delete_source=del_src)

            first_name = selected[0].name
            title_text = f"Compress {first_name} (zstd -{level})" if len(selected) == 1 else f"Compress {len(selected)} Files (zstd -{level})"
            self.run_async_task(title_text, _do_repack_zst)

    def _action_repack_super(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = RepackSuperDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            selected = params["selected_files"]
            if not selected:
                selected = [f for f in proj.images.glob("*.img") if f.name != "super.img"]
            if not selected:
                QMessageBox.warning(self, "No Images", "No partition images found to assemble super.img.")
                return

            out_super = proj.out / "super.img"
            self.run_async_task(
                "Repack super.img",
                repack_super,
                selected,
                out_super=out_super,
                device_size=params["device_size"],
                group_name=params["group_name"],
                slot_type=params["slot_type"],
                sparse=params["sparse"],
            )

    def _action_convert_simg(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = ImgSimgDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            selected = params["selected_files"]
            mode = params["mode"]
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one image to convert.")
                return

            def _do_convert() -> None:
                for target in selected:
                    if "Sparse to Raw" in mode:
                        out_img = target.with_name(f"{target.stem}_raw.img")
                        sparse_to_raw(target, out_img)
                    elif "Raw to Sparse" in mode:
                        out_img = target.with_name(f"{target.stem}_sparse.img")
                        raw_to_sparse(target, out_img)
                    else:
                        from dna_core.detection import detect_image_type, ImageType
                        img_t = detect_image_type(target)
                        if img_t == ImageType.SPARSE:
                            out_img = target.with_name(f"{target.stem}_raw.img")
                            sparse_to_raw(target, out_img)
                        else:
                            out_img = target.with_name(f"{target.stem}_sparse.img")
                            raw_to_sparse(target, out_img)

            first_name = selected[0].name
            title_text = f"Convert {first_name}" if len(selected) == 1 else f"Convert {len(selected)} Images"
            self.run_async_task(title_text, _do_convert)

    def _action_convert_dat_br(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Select Raw Image to convert to DAT/BR", str(proj.images), "Image (*.img);;All Files (*)"
        )
        if not chosen:
            return
        target = Path(chosen)

        def _do_dat_br() -> None:
            img2sdat(target, out_dir=proj.images, prefix=target.stem)
            dat_file = proj.images / f"{target.stem}.new.dat"
            br_file = proj.images / f"{target.stem}.new.dat.br"
            if dat_file.exists():
                run_tool("brotli", ["-q", "3", "-f", str(dat_file), "-o", str(br_file)], check=True)

        self.run_async_task("Convert IMG to DAT + BR", _do_dat_br)

    def _action_convert_merge_super(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        chunks = sorted(list(proj.images.glob("super.img.*")))
        if not chunks and proj.io_dir != proj.images:
            chunks = sorted(list(proj.io_dir.glob("super.img.*")))
        if not chunks:
            QMessageBox.warning(
                self,
                "No Super Chunks Found",
                f"No 'super.img.*' chunks found in {proj.images}.",
            )
            return

        out_img = proj.images / "super.img"
        self.run_async_task("Merge super.img chunks", merge_sparse_chunks, chunks, out_img)

    def _action_convert_split_super(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        super_img = proj.images / "super.img"
        if not super_img.exists() and (proj.io_dir / "super.img").exists():
            super_img = proj.io_dir / "super.img"
        elif not super_img.exists():
            start_dir = str(proj.io_dir if proj.io_dir.is_dir() else proj.images)
            chosen, _ = QFileDialog.getOpenFileName(
                self, "Select super.img to split", start_dir, "Image (*.img);;All Files (*)"
            )
            if not chosen:
                return
            super_img = Path(chosen)

        chunk_mb, ok = QInputDialog.getInt(
            self, "Chunk Size", "Enter chunk size in MB (e.g. 1024 or 1500):", 1024, 100, 10000
        )
        if not ok:
            return

        self.run_async_task("Split super.img", split_sparse_image, super_img, chunk_mb, out_dir=proj.images)

    def _action_jar_dsv(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        jar_path = self._find_or_pick_services_jar(proj)
        if not jar_path:
            return
        dlg = CorePatchDsvDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            self.run_async_task(
                "Core Patch DSV",
                patch_core_patch_dsv,
                jar_path,
                disable_invoke_custom=params.get("remove_invoke_custom", False),
            )

    def _action_jar_apk_protection(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        jar_path = self._find_or_pick_services_jar(proj)
        if not jar_path:
            return
        dlg = RemoveApkProtectionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            self.run_async_task(
                "Remove APK Protection",
                patch_remove_apk_protection,
                jar_path,
                disable_invoke_custom=params.get("remove_invoke_custom", False),
            )

    def _action_jar_dss(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        jar_path = self._find_or_pick_services_jar(proj)
        if not jar_path:
            return
        dlg = DisableSecureScreenshotDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            self.run_async_task(
                "Disable Secure Screenshot",
                patch_disable_secure_screenshot,
                jar_path,
                disable_invoke_custom=params.get("remove_invoke_custom", False),
            )

    def _find_or_pick_services_jar(self, proj: ProjectPaths) -> Path | None:
        candidates = [
            proj.unpacked / "system" / "system" / "framework" / "services.jar",
            proj.unpacked / "system" / "framework" / "services.jar",
        ]
        for c in candidates:
            if c.exists():
                return c
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Select services.jar", str(proj.unpacked), "JAR (*.jar);;All Files (*)"
        )
        if chosen:
            return Path(chosen)
        return None

    def _action_patch_vbmeta(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = PatchVbmetaDialog(proj, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_parameters()
            selected = params["selected_files"]
            if not selected:
                vbmeta_path = proj.images / "vbmeta.img"
                if vbmeta_path.exists():
                    selected = [vbmeta_path]
            if not selected:
                QMessageBox.warning(self, "No Selection", "Please select at least one vbmeta image to patch.")
                return

            mode = params["mode"]

            def _do_patch() -> None:
                for f in selected:
                    patch_vbmeta(f, mode=mode)

            self.run_async_task(f"Patch VBMeta ({params['patch_type']})", _do_patch)

    def _action_patch_integrity(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Patch Integrity Fix (Pixel 7 Pro)", patch_integrity_fix, proj.unpacked)

    def _action_patch_safetycore(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Patch SafetyCore Placeholder", patch_safetycore, proj.unpacked)

    def _action_patch_privapp(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Patch Priv-App Permissions", patch_privapp_permissions, proj.unpacked)

    def _action_patch_ota(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Disable OTA Updates", patch_disable_ota, proj.unpacked)

    def _action_patch_xiaomi(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Disable Xiaomi Services & Telemetry", patch_disable_xiaomi_services, proj.unpacked)

    def _action_rom_debloat(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        dlg = DebloatRomDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            profile = dlg.get_rom_type()
            self.run_async_task(f"Debloat ROM ({profile})", debloat_rom, proj.unpacked, profile=profile)

    def _action_rom_remove_oat(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Remove OAT Directories", remove_oat_directories, proj.unpacked)

    def _action_rom_make_rw(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Make ROM Read-Write", make_rom_rw, proj.unpacked)

    def _action_rom_decrypt(self) -> None:
        proj = self._require_project()
        if not proj:
            return
        self.run_async_task("Decrypt ROM (Disable Encryption in Fstab)", decrypt_rom, proj.unpacked)

    def _action_run_plugin(self, plugin_id: str) -> None:
        proj = self._require_project()
        if not proj:
            return
        from dna_core.plugin import get_plugin
        plugin = get_plugin(plugin_id, project_plugins_dir=proj.plugins_dir)
        self.run_async_task(f"Run Plugin: {plugin_id}", run_plugin, plugin, proj)


def start_gui() -> int:
    """Entrypoint for starting the DNA-Linux desktop GUI."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setStyleSheet(DARK_THEME_QSS)
    window = MainWindow()
    window.show()
    return app.exec()
