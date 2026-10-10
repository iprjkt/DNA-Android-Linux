"""Custom styled modal dialogs for DNA-Linux GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dna_core.config import get_background_image, set_background_image
from dna_core.project import (
    ProjectPaths,
    create_project,
    delete_project,
    get_active_project,
    list_projects,
    select_project,
)
from dna_core.tools import run_doctor


class ToggleSwitch(QAbstractButton):
    """Sleek iOS/Android style toggle switch."""

    def __init__(self, parent: QWidget | None = None, checked: bool = False) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Track background
        track_color = QColor("#3b82f6") if self.isChecked() else QColor("#334155")
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 13, 13)

        # Thumb
        thumb_color = QColor("#ffffff")
        painter.setBrush(thumb_color)
        thumb_x = rect.width() - 23 if self.isChecked() else 3
        painter.drawEllipse(thumb_x, 3, 20, 20)


class AboutDialog(QDialog):
    """Project Information and About dialog with Custom Wallpaper selector."""

    background_changed = pyqtSignal(str)
    transparent_toggled = pyqtSignal(bool)  # compatibility signal

    def __init__(self, parent: QWidget | None = None, is_transparent: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("About DNA")
        self.setFixedSize(480, 370)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(
            "QDialog {"
            "   background-color: #16171b;"
            "   border: 1px solid #282a35;"
            "   border-radius: 20px;"
            "}"
            "QLabel { background: transparent; }"
            "QPushButton#btn_wallpaper {"
            "   background-color: #1e293b;"
            "   color: #38bdf8;"
            "   border: 1px solid #334155;"
            "   border-radius: 8px;"
            "   padding: 6px 14px;"
            "   font-size: 11px;"
            "   font-weight: 600;"
            "}"
            "QPushButton#btn_wallpaper:hover {"
            "   background-color: #0284c7;"
            "   color: #ffffff;"
            "}"
            "QPushButton#btn_clear {"
            "   background-color: #450a0a;"
            "   color: #f87171;"
            "   border: 1px solid #7f1d1d;"
            "   border-radius: 8px;"
            "   padding: 6px 12px;"
            "   font-size: 11px;"
            "   font-weight: 600;"
            "}"
            "QPushButton#btn_clear:hover {"
            "   background-color: #991b1b;"
            "   color: #ffffff;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Top section: "About · DNA" and "Version : 250511"
        top_layout = QVBoxLayout()
        top_layout.setSpacing(4)

        header_lbl = QLabel("About · DNA")
        header_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")
        top_layout.addWidget(header_lbl)

        ver_layout = QHBoxLayout()
        ver_layout.setSpacing(4)
        ver_title = QLabel("Version : ")
        ver_title.setStyleSheet("color: #60a5fa; font-size: 13px; font-weight: 600;")
        ver_val = QLabel("250511 (1.0.0-linux)")
        ver_val.setStyleSheet("color: #3b82f6; font-size: 13px; font-weight: 600;")
        ver_layout.addWidget(ver_title)
        ver_layout.addWidget(ver_val)
        ver_layout.addStretch(1)
        top_layout.addLayout(ver_layout)

        layout.addLayout(top_layout)
        layout.addStretch(1)

        # Center section: Stylized Title "D·N·A-Android" + Author
        center_layout = QVBoxLayout()
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel("D·N·A-Android")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("color: #b45309; letter-spacing: 1.5px; font-weight: 800;")
        center_layout.addWidget(title_lbl)

        author_lbl = QLabel("Author : tao1996, Meeting is fate")
        author_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_lbl.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 500;")
        center_layout.addWidget(author_lbl)

        port_lbl = QLabel("Linux Port : @iprjkt | Native x86_64 toolchain")
        port_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        port_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        center_layout.addWidget(port_lbl)

        layout.addLayout(center_layout)
        layout.addStretch(1)

        # Custom Background Card (replacing transparent UI)
        bg_card = QFrame()
        bg_card.setObjectName("bg_card")
        bg_card.setStyleSheet(
            "#bg_card { background-color: #121316; border: 1px solid #232530; border-radius: 12px; }"
            "QLabel { border: none; background: transparent; }"
        )
        bg_card_layout = QHBoxLayout(bg_card)
        bg_card_layout.setContentsMargins(12, 8, 12, 8)
        bg_card_layout.setSpacing(10)

        bg_text_layout = QVBoxLayout()
        bg_text_layout.setSpacing(2)
        bg_title = QLabel("Custom Background")
        bg_title.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: 600;")
        self.bg_subtitle = QLabel("Default solid theme")
        self.bg_subtitle.setStyleSheet("color: #64748b; font-size: 11px;")
        bg_text_layout.addWidget(bg_title)
        bg_text_layout.addWidget(self.bg_subtitle)
        bg_card_layout.addLayout(bg_text_layout)

        bg_card_layout.addStretch(1)

        self.btn_choose_bg = QPushButton("Set Wallpaper")
        self.btn_choose_bg.setObjectName("btn_wallpaper")
        self.btn_choose_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_choose_bg.clicked.connect(self._choose_wallpaper)
        bg_card_layout.addWidget(self.btn_choose_bg)

        self.btn_clear_bg = QPushButton("Clear")
        self.btn_clear_bg.setObjectName("btn_clear")
        self.btn_clear_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bg.clicked.connect(self._clear_wallpaper)
        bg_card_layout.addWidget(self.btn_clear_bg)

        # Keep a hidden toggle switch for backward compatibility
        self.toggle = ToggleSwitch(self)
        self.toggle.hide()
        self.toggle.toggled.connect(lambda val: self.transparent_toggled.emit(val))

        layout.addWidget(bg_card)

        # Bottom row: Kr-script reference
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addStretch(1)

        kr_lbl = QLabel("Based on [Kr-Script4.0.3] creation")
        kr_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        bottom_layout.addWidget(kr_lbl)

        layout.addLayout(bottom_layout)

        self._refresh_bg_state()

    def _refresh_bg_state(self) -> None:
        curr_bg = get_background_image()
        if curr_bg and Path(curr_bg).is_file():
            self.bg_subtitle.setText(f"Wallpaper: {Path(curr_bg).name}")
            self.bg_subtitle.setStyleSheet("color: #38bdf8; font-size: 11px;")
            self.btn_clear_bg.setEnabled(True)
            self.btn_clear_bg.show()
        else:
            self.bg_subtitle.setText("Default solid theme")
            self.bg_subtitle.setStyleSheet("color: #64748b; font-size: 11px;")
            self.btn_clear_bg.setEnabled(False)
            self.btn_clear_bg.hide()

    def _choose_wallpaper(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wallpaper Background Image",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if file_path:
            set_background_image(file_path)
            self.background_changed.emit(file_path)
            self.transparent_toggled.emit(True)
            self._refresh_bg_state()

    def _clear_wallpaper(self) -> None:
        set_background_image(None)
        self.background_changed.emit("")
        self.transparent_toggled.emit(False)
        self._refresh_bg_state()


class ConfirmDialog(QDialog):
    """Clean dark-themed confirmation modal."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        is_danger: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title_lbl = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #ffffff;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        layout.addWidget(msg_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        if is_danger:
            confirm_btn.setObjectName("btn_danger")
        else:
            confirm_btn.setObjectName("btn_primary")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)


class InputDialog(QDialog):
    """Text input modal with placeholder and validation."""

    def __init__(
        self,
        title: str,
        prompt: str,
        default_value: str = "",
        placeholder: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_lbl = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #ffffff;")
        layout.addWidget(title_lbl)

        prompt_lbl = QLabel(prompt)
        prompt_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        layout.addWidget(prompt_lbl)

        self.input_edit = QLineEdit(default_value)
        self.input_edit.setPlaceholderText(placeholder)
        layout.addWidget(self.input_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def get_value(self) -> str:
        return self.input_edit.text().strip()


class SelectProjectDialog(QDialog):
    """Modal for selecting, creating, or deleting project workspaces."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Project")
        self.setFixedSize(500, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.selected_project_name: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_lbl = QLabel("Projects in ~/DNA")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_lbl.setFont(header_font)
        header_lbl.setStyleSheet("color: #ffffff;")
        layout.addWidget(header_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #14161f; border: 1px solid #252837; border-radius: 8px; padding: 6px; }"
            "QListWidget::item { padding: 10px; border-radius: 6px; margin: 2px 0px; }"
            "QListWidget::item:selected { background-color: #1e3a8a; color: #ffffff; }"
        )
        layout.addWidget(self.list_widget, stretch=1)

        # Action buttons row
        actions_layout = QHBoxLayout()
        self.new_btn = QPushButton("+ Create New")
        self.new_btn.clicked.connect(self._create_new)
        actions_layout.addWidget(self.new_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("btn_danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        actions_layout.addWidget(self.delete_btn)

        actions_layout.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        actions_layout.addWidget(self.cancel_btn)

        self.select_btn = QPushButton("Select Project")
        self.select_btn.setObjectName("btn_primary")
        self.select_btn.clicked.connect(self._select_current)
        actions_layout.addWidget(self.select_btn)

        layout.addLayout(actions_layout)

        self.refresh_list()

    def refresh_list(self) -> None:
        self.list_widget.clear()
        projects = list_projects()
        active = get_active_project()
        active_name = active.name if active else None

        for p, is_act in projects:
            p_name = p.name
            display_text = f"📁 {p_name}"
            if active_name and p_name == active_name:
                display_text += " [Active]"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, p_name)
            self.list_widget.addItem(item)
            if active_name and p_name == active_name:
                self.list_widget.setCurrentItem(item)

    def _select_current(self) -> None:
        curr = self.list_widget.currentItem()
        if not curr:
            QMessageBox.warning(self, "No Selection", "Please select a project from the list.")
            return
        p_name = curr.data(Qt.ItemDataRole.UserRole)
        select_project(p_name)
        self.selected_project_name = p_name
        self.accept()

    def _create_new(self) -> None:
        dlg = InputDialog(
            "Create New Project",
            "Enter new project name (e.g. 'myrom' or 'hyperos'):",
            placeholder="my_project",
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            val = dlg.get_value()
            if val:
                try:
                    create_project(val)
                    self.refresh_list()
                except Exception as exc:
                    QMessageBox.critical(self, "Creation Error", str(exc))

    def _delete_selected(self) -> None:
        curr = self.list_widget.currentItem()
        if not curr:
            return
        p_name = curr.data(Qt.ItemDataRole.UserRole)
        confirm = ConfirmDialog(
            "Delete Project",
            f"Are you sure you want to permanently delete project '{p_name}' and all its files?",
            confirm_text="Delete Permanently",
            is_danger=True,
            parent=self,
        )
        if confirm.exec() == QDialog.DialogCode.Accepted:
            try:
                delete_project(p_name)
                self.refresh_list()
            except Exception as exc:
                QMessageBox.critical(self, "Delete Error", str(exc))


class DeleteProjectDialog(QDialog):
    """Dedicated modal for deleting project workspaces in ~/DNA."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Delete Project")
        self.setFixedSize(480, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_lbl = QLabel("Select project in ~/DNA to delete:")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header_lbl.setFont(header_font)
        header_lbl.setStyleSheet("color: #ffffff;")
        layout.addWidget(header_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #14161f; border: 1px solid #252837; border-radius: 8px; padding: 6px; }"
            "QListWidget::item { padding: 10px; border-radius: 6px; margin: 2px 0px; }"
            "QListWidget::item:selected { background-color: #7f1d1d; color: #ffffff; }"
        )
        layout.addWidget(self.list_widget, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.delete_btn = QPushButton("Delete Project")
        self.delete_btn.setObjectName("btn_danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)
        self.refresh_list()

    def refresh_list(self) -> None:
        self.list_widget.clear()
        projects = list_projects()
        active = get_active_project()
        active_name = active.name if active else None

        for p, is_act in projects:
            p_name = p.name
            display_text = f"📁 {p_name}"
            if active_name and p_name == active_name:
                display_text += " [Active]"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, p_name)
            self.list_widget.addItem(item)

    def _delete_selected(self) -> None:
        curr = self.list_widget.currentItem()
        if not curr:
            QMessageBox.warning(self, "No Selection", "Please select a project to delete.")
            return
        p_name = curr.data(Qt.ItemDataRole.UserRole)
        confirm = ConfirmDialog(
            "Delete Project",
            f"Are you sure you want to permanently delete project '{p_name}' and all its files from ~/DNA?",
            confirm_text="Delete Permanently",
            is_danger=True,
            parent=self,
        )
        if confirm.exec() == QDialog.DialogCode.Accepted:
            try:
                delete_project(p_name)
                self.refresh_list()
                self.accept()
            except Exception as exc:
                QMessageBox.critical(self, "Delete Error", str(exc))


class DoctorDialog(QDialog):
    """Modal displaying native Linux toolchain health and environment status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("DNA-Linux Tool Doctor")
        self.setFixedSize(700, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_lbl = QLabel("Toolchain & Environment Health")
        header_font = QFont()
        header_font.setPointSize(13)
        header_font.setBold(True)
        header_lbl.setFont(header_font)
        header_lbl.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch(1)

        self.summary_badge = QLabel("Checking...")
        self.summary_badge.setStyleSheet(
            "background: #172033; color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: bold;"
        )
        header_layout.addWidget(self.summary_badge)
        layout.addLayout(header_layout)

        # Tools Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tool", "Status", "Version / Details", "Required By"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, stretch=1)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.clicked.connect(self.run_checks)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("btn_primary")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.run_checks()

    def run_checks(self) -> None:
        report = run_doctor()
        tools = report.get("tools", [])

        self.table.setRowCount(len(tools))
        missing_count = 0

        for row, t in enumerate(tools):
            name = t.get("name", "")
            found = t.get("found", False)
            version = t.get("version") or t.get("path") or "Not installed"
            required_by = t.get("required_by", "")

            item_name = QTableWidgetItem(name)
            item_name.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, item_name)

            if found:
                item_status = QTableWidgetItem("✓ Found")
                item_status.setForeground(Qt.GlobalColor.green)
            else:
                missing_count += 1
                item_status = QTableWidgetItem("✗ Missing")
                item_status.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 1, item_status)

            item_ver = QTableWidgetItem(str(version))
            item_ver.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 2, item_ver)

            item_req = QTableWidgetItem(required_by)
            item_req.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 3, item_req)

        if missing_count == 0:
            self.summary_badge.setText(f"All {len(tools)} Tools Ready")
            self.summary_badge.setStyleSheet(
                "background: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 6px; font-weight: bold;"
            )
        else:
            self.summary_badge.setText(f"{missing_count} Missing")
            self.summary_badge.setStyleSheet(
                "background: #7f1d1d; color: #fca5a5; padding: 4px 10px; border-radius: 6px; font-weight: bold;"
            )


# =====================================================================
# Reusable Extended Operation Dialog Components (UI_example/1)
# =====================================================================

def get_repack_partition_candidates(proj: ProjectPaths | None, mode: str = "all") -> list[Path]:
    """Detect real partition targets from workspace: unpacked folders and partition .img files."""
    if not proj:
        return []
    candidates: list[Path] = []
    seen: set[Path] = set()

    # 1. Unpacked partition directories under ~/DNA/<project>/unpacked/
    if mode in ("all", "folder") and proj.unpacked.is_dir():
        for d in sorted(proj.unpacked.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                resolved = d.resolve()
                if resolved not in seen:
                    candidates.append(d)
                    seen.add(resolved)

    # 2. Partition image files under ~/DNA/<project>/images/ (excluding super.img)
    if mode in ("all", "img") and proj.images.is_dir():
        for f in sorted(proj.images.glob("*.img")):
            if f.name.lower() != "super.img" and not f.name.startswith("."):
                resolved = f.resolve()
                if resolved not in seen:
                    candidates.append(f)
                    seen.add(resolved)

    # 3. Partition image files directly under project root ~/DNA/<project>/ (excluding super.img)
    if mode in ("all", "img") and proj.project_dir.is_dir():
        for f in sorted(proj.project_dir.glob("*.img")):
            if f.name.lower() != "super.img" and not f.name.startswith("."):
                resolved = f.resolve()
                if resolved not in seen:
                    candidates.append(f)
                    seen.add(resolved)

    return candidates


class StyledComboBox(QComboBox):
    """QComboBox styled with a dark theme, custom chevron arrow, and translucent popup background to prevent white frames on Hyprland/Wayland."""

    def __init__(self, parent: QWidget | None = None, borderless: bool = False) -> None:
        super().__init__(parent)
        self.borderless = borderless
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if borderless:
            self.setStyleSheet(
                "QComboBox {"
                "   combobox-popup: 0;"
                "   background-color: transparent;"
                "   border: none;"
                "   color: #ffffff;"
                "   font-size: 13px;"
                "   padding: 4px 28px 4px 6px;"
                "}"
                "QComboBox:hover { color: #38bdf8; }"
                "QComboBox::drop-down { border: none; width: 0px; }"
            )
        else:
            self.setStyleSheet(
                "QComboBox {"
                "   combobox-popup: 0;"
                "   background-color: #1a1b20;"
                "   border: 1px solid #282a32;"
                "   border-radius: 10px;"
                "   color: #ffffff;"
                "   font-size: 13px;"
                "   padding: 8px 30px 8px 14px;"
                "}"
                "QComboBox:hover { border-color: #3b82f6; }"
                "QComboBox::drop-down { border: none; width: 0px; }"
            )

        v = self.view()
        v.setStyleSheet(
            "QAbstractItemView {"
            "   background-color: #2b2d32;"
            "   color: #ffffff;"
            "   border: none;"
            "   padding: 4px;"
            "   outline: none;"
            "}"
            "QAbstractItemView::item {"
            "   min-height: 32px;"
            "   padding: 6px 12px;"
            "   border-radius: 6px;"
            "   color: #e2e8f0;"
            "}"
            "QAbstractItemView::item:hover {"
            "   background-color: #383b42;"
            "   color: #ffffff;"
            "}"
            "QAbstractItemView::item:selected {"
            "   background-color: #383b42;"
            "   color: #ffffff;"
            "}"
        )
        container = v.parentWidget()
        if container:
            container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            container.setWindowFlags(
                Qt.WindowType.Popup
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.NoDropShadowWindowHint
            )
            container.setStyleSheet(
                "background-color: #2b2d32; border: 1px solid #3c3f46; border-radius: 10px; padding: 4px;"
            )

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(
            QPen(
                QColor("#94a3b8"),
                2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        r = self.rect()
        cx = r.right() - 14
        cy = r.center().y()
        p.drawLine(cx - 4, cy - 2, cx, cy + 2)
        p.drawLine(cx, cy + 2, cx + 4, cy - 2)

    def showPopup(self) -> None:
        container = self.view().parentWidget()
        if container:
            container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            container.setStyleSheet(
                "background-color: #2b2d32; border: 1px solid #3c3f46; border-radius: 10px; padding: 4px;"
            )
        super().showPopup()
        container = self.view().parentWidget()
        if container:
            container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            container.setStyleSheet(
                "background-color: #2b2d32; border: 1px solid #3c3f46; border-radius: 10px; padding: 4px;"
            )


class OptionRowCard(QWidget):
    """Horizontal card with label on left, control on right, and optional subtitle note below.
    Matches the card design in DNA-Android (Screenshot_2026-10-11-01-29-56-211).
    """

    def __init__(
        self,
        label_text: str,
        widget: QWidget,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.card_layout = main_layout

        self.pill = QFrame(self)
        self.pill.setObjectName("option_pill")
        self.pill.setStyleSheet(
            "#option_pill {"
            "   background-color: #1a1b20;"
            "   border: 1px solid #282a32;"
            "   border-radius: 12px;"
            "   min-height: 48px;"
            "}"
            "#option_pill:hover {"
            "   border-color: #3b82f6;"
            "}"
        )
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(14, 4, 14, 4)
        pill_layout.setSpacing(10)

        self.label = QLabel(label_text, self.pill)
        self.label.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-weight: 500; background: transparent; border: none;"
        )
        self.label.setWordWrap(True)
        self.label.setFixedWidth(105)
        pill_layout.addWidget(self.label)

        divider = QFrame(self.pill)
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet(
            "background-color: #2f323c; border: none; min-width: 1px; max-width: 1px; min-height: 22px; max-height: 22px;"
        )
        pill_layout.addWidget(divider)

        self.widget = widget
        pill_layout.addWidget(self.widget, 1)
        main_layout.addWidget(self.pill)

        self.sub_lbl: QLabel | None = None
        if subtitle:
            self.sub_lbl = QLabel(subtitle, self)
            self.sub_lbl.setWordWrap(True)
            self.sub_lbl.setStyleSheet(
                "color: #71767c; font-size: 11px; padding-left: 6px; background: transparent;"
            )
            main_layout.addWidget(self.sub_lbl)


class FileListSelectDialog(QDialog):
    """Modal allowing multi-selection of project workspace files with checkboxes and manual browsing."""

    def __init__(
        self,
        title: str,
        files: list[Path],
        selected_files: list[Path] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(480, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(
            "QDialog {"
            "   background-color: #16171b;"
            "   border: 1px solid #282a35;"
            "   border-radius: 16px;"
            "}"
            "QLabel { background: transparent; color: #ffffff; }"
            "QLineEdit {"
            "   background-color: #1c1d24;"
            "   border: 1px solid #282a35;"
            "   border-radius: 8px;"
            "   padding: 8px 12px;"
            "   color: #ffffff;"
            "   font-size: 12px;"
            "}"
            "QListWidget {"
            "   background-color: #121316;"
            "   border: 1px solid #282a35;"
            "   border-radius: 10px;"
            "   padding: 4px;"
            "   color: #ffffff;"
            "}"
            "QListWidget::item {"
            "   padding: 8px;"
            "   border-radius: 6px;"
            "}"
            "QListWidget::item:hover {"
            "   background-color: #1c1d24;"
            "}"
        )

        self.all_files = list(files)
        selected_set = {f.resolve() for f in (selected_files or [])}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        hdr = QLabel(title)
        hdr.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        layout.addWidget(hdr)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files...")
        self.search_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_input)

        self.empty_lbl = QLabel(
            "No partition files detected in project. Click '+ Browse File...' or '+ Browse Folder...' to add one."
        )
        self.empty_lbl.setWordWrap(True)
        self.empty_lbl.setStyleSheet("color: #64748b; font-size: 12px; padding: 10px;")
        layout.addWidget(self.empty_lbl)
        self.empty_lbl.setVisible(len(self.all_files) == 0)

        self.list_widget = QListWidget()
        for fp in self.all_files:
            self._add_item_widget(fp, checked=(fp.resolve() in selected_set))
        layout.addWidget(self.list_widget, stretch=1)

        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)

        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setStyleSheet(
            "background: #1e293b; color: #94a3b8; border-radius: 6px; padding: 5px 10px; font-size: 11px;"
        )
        sel_all_btn.clicked.connect(self._select_all)
        quick_layout.addWidget(sel_all_btn)

        desel_all_btn = QPushButton("Deselect All")
        desel_all_btn.setStyleSheet(
            "background: #1e293b; color: #94a3b8; border-radius: 6px; padding: 5px 10px; font-size: 11px;"
        )
        desel_all_btn.clicked.connect(self._deselect_all)
        quick_layout.addWidget(desel_all_btn)

        quick_layout.addStretch(1)

        browse_file_btn = QPushButton("+ Browse File...")
        browse_file_btn.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 6px; padding: 5px 10px; font-size: 11px; font-weight: 500;"
        )
        browse_file_btn.clicked.connect(self._browse_file)
        quick_layout.addWidget(browse_file_btn)

        browse_folder_btn = QPushButton("+ Browse Folder...")
        browse_folder_btn.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #334155; border-radius: 6px; padding: 5px 10px; font-size: 11px; font-weight: 500;"
        )
        browse_folder_btn.clicked.connect(self._browse_folder)
        quick_layout.addWidget(browse_folder_btn)

        layout.addLayout(quick_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setStyleSheet(
            "background-color: #262934; color: #cbd5e1; font-weight: 600; border-radius: 14px; height: 38px; border: none;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("CONFIRM")
        confirm_btn.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: 600; border-radius: 14px; height: 38px; border: none;"
        )
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _add_item_widget(self, fp: Path, checked: bool = False) -> None:
        display_name = f"📁  {fp.name} (Folder)" if fp.is_dir() else f"💿  {fp.name}"
        item = QListWidgetItem(display_name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, fp)
        self.list_widget.addItem(item)
        self.empty_lbl.setVisible(False)

    def _select_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _apply_filter(self, text: str) -> None:
        filter_text = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(filter_text not in item.text().lower())

    def _browse_file(self) -> None:
        start_dir = str(self.all_files[0].parent) if self.all_files else str(Path.home())
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Select Partition Image File",
            start_dir,
            "Partition Images (*.img *.bin *.raw);;All Files (*)",
        )
        if chosen:
            self._add_custom_path(Path(chosen))

    def _browse_folder(self) -> None:
        start_dir = str(self.all_files[0].parent) if self.all_files else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Select Unpacked Partition Folder",
            start_dir,
        )
        if chosen:
            self._add_custom_path(Path(chosen))

    def _add_custom_path(self, fp: Path) -> None:
        resolved = fp.resolve()
        for i in range(self.list_widget.count()):
            existing = self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            if isinstance(existing, Path) and existing.resolve() == resolved:
                self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)
                return
        self.all_files.append(fp)
        self._add_item_widget(fp, checked=True)

    def get_selected_files(self) -> list[Path]:
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                fp = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(fp, Path):
                    selected.append(fp)
        return selected


class FileSelectField(QWidget):
    """Card widget with 'Please select' text, blue count badge, and subtitle, opening FileListSelectDialog."""

    selection_changed = pyqtSignal()

    def __init__(
        self,
        candidate_files: list[Path] | None = None,
        subtitle: str = "",
        dialog_title: str = "Select Files",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.candidate_files = list(candidate_files or [])
        self.selected_files: list[Path] = []
        self.dialog_title = dialog_title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn = QPushButton()
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #1c1d24;"
            "   border: 1px solid #282a35;"
            "   border-radius: 12px;"
            "   padding: 12px 14px;"
            "   text-align: left;"
            "}"
            "QPushButton:hover {"
            "   border-color: #3b82f6;"
            "   background-color: #21232d;"
            "}"
        )
        self.btn.clicked.connect(self._open_selector)

        btn_layout = QHBoxLayout(self.btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.label_text = QLabel("Please select")
        self.label_text.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500;")
        btn_layout.addWidget(self.label_text)

        btn_layout.addStretch(1)

        self.badge = QLabel("0")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-size: 12px; font-weight: bold; border-radius: 10px; min-width: 20px; padding: 2px 6px;"
        )
        btn_layout.addWidget(self.badge)

        layout.addWidget(self.btn)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            layout.addWidget(sub_lbl)

    def set_candidate_files(self, files: list[Path]) -> None:
        self.candidate_files = list(files)
        cand_set = {f.resolve() for f in self.candidate_files}
        self.selected_files = [f for f in self.selected_files if f.resolve() in cand_set]
        self._update_display()

    def set_selected_files(self, files: list[Path]) -> None:
        self.selected_files = list(files)
        self._update_display()

    def get_selected_files(self) -> list[Path]:
        return list(self.selected_files)

    def _open_selector(self) -> None:
        dlg = FileListSelectDialog(
            self.dialog_title,
            self.candidate_files,
            selected_files=self.selected_files,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Sync candidate_files if custom files were browsed
            for f in dlg.all_files:
                if f not in self.candidate_files:
                    self.candidate_files.append(f)
            self.selected_files = dlg.get_selected_files()
            self._update_display()
            self.selection_changed.emit()

    def _update_display(self) -> None:
        count = len(self.selected_files)
        self.badge.setText(str(count))
        if count == 0:
            self.label_text.setText("Please select")
            self.label_text.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")
        elif count == 1:
            self.label_text.setText(self.selected_files[0].name)
            self.label_text.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
        else:
            self.label_text.setText(f"{count} files selected")
            self.label_text.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")


class NumberStepper(QWidget):
    """Minus/Slider/Plus stepper control matching Repack zstd / single partition dialogs."""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        min_val: int = 1,
        max_val: int = 22,
        default_val: int = 3,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        stepper_bar = QHBoxLayout()
        stepper_bar.setSpacing(10)

        # Minus button
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(36, 32)
        self.btn_minus.setStyleSheet(
            "QPushButton { background-color: #1e2029; color: #ffffff; border: 1px solid #282a35; border-radius: 8px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2b2e3b; border-color: #3b82f6; }"
        )
        self.btn_minus.clicked.connect(self._decrement)
        stepper_bar.addWidget(self.btn_minus)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #20222a; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #ffffff; width: 16px; margin: -5px 0; border-radius: 8px; }"
        )
        self.slider.valueChanged.connect(self._on_slider_changed)
        stepper_bar.addWidget(self.slider, stretch=1)

        # Value badge
        self.val_badge = QLabel(str(default_val))
        self.val_badge.setFixedSize(38, 30)
        self.val_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_badge.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; font-size: 13px; font-weight: bold; border-radius: 6px; border: 1px solid #334155;"
        )
        stepper_bar.addWidget(self.val_badge)

        # Plus button
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(36, 32)
        self.btn_plus.setStyleSheet(
            "QPushButton { background-color: #1e2029; color: #ffffff; border: 1px solid #282a35; border-radius: 8px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2b2e3b; border-color: #3b82f6; }"
        )
        self.btn_plus.clicked.connect(self._increment)
        stepper_bar.addWidget(self.btn_plus)

        layout.addLayout(stepper_bar)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            layout.addWidget(sub_lbl)

    def _decrement(self) -> None:
        self.slider.setValue(max(self.min_val, self.slider.value() - 1))

    def _increment(self) -> None:
        self.slider.setValue(min(self.max_val, self.slider.value() + 1))

    def _on_slider_changed(self, val: int) -> None:
        self.val_badge.setText(str(val))
        self.value_changed.emit(val)

    def get_value(self) -> int:
        return self.slider.value()

    def set_value(self, val: int) -> None:
        self.slider.setValue(val)


class CheckboxCard(QFrame):
    """Enclosed dark card containing a checkbox and explanation."""

    def __init__(
        self,
        label: str,
        subtitle: str = "",
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("checkbox_card")
        self.setStyleSheet(
            "#checkbox_card {"
            "   background-color: #1c1d24;"
            "   border: 1px solid #282a35;"
            "   border-radius: 12px;"
            "}"
            "QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.checkbox = QCheckBox(label)
        self.checkbox.setChecked(checked)
        self.checkbox.setStyleSheet(
            "QCheckBox { background: transparent; color: #ffffff; font-size: 13px; font-weight: 500; spacing: 10px; }"
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #3b82f6; background: #131418; }"
            "QCheckBox::indicator:checked { background: #2563eb; }"
        )
        layout.addWidget(self.checkbox)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 28px;")
            layout.addWidget(sub_lbl)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, val: bool) -> None:
        self.checkbox.setChecked(val)


class BaseOperationDialog(QDialog):
    """Base modal window providing styling, bullet section headers, and CANCEL/CONFIRM buttons."""

    def __init__(self, title: str, subtitle: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(
            "QDialog {"
            "   background-color: #16171b;"
            "   border: 1px solid #282a35;"
            "   border-radius: 20px;"
            "}"
            "QLabel { background: transparent; }"
            "QComboBox {"
            "   background-color: #1c1d24;"
            "   border: 1px solid #282a35;"
            "   border-radius: 10px;"
            "   padding: 8px 12px;"
            "   color: #ffffff;"
            "   font-size: 13px;"
            "}"
            "QComboBox:hover { border-color: #3b82f6; }"
            "QComboBox::drop-down { border: none; width: 22px; }"
            "QComboBox QAbstractItemView {"
            "   background-color: #181920;"
            "   color: #ffffff;"
            "   border: 1px solid #282a35;"
            "   border-radius: 8px;"
            "   padding: 4px;"
            "   outline: none;"
            "   selection-background-color: #2563eb;"
            "   selection-color: #ffffff;"
            "}"
            "QComboBox QAbstractItemView::item {"
            "   min-height: 28px;"
            "   padding: 4px 8px;"
            "   border-radius: 4px;"
            "   color: #cbd5e1;"
            "}"
            "QComboBox QAbstractItemView::item:hover {"
            "   background-color: #222533;"
            "   color: #ffffff;"
            "}"
            "QComboBox QAbstractItemView::item:selected {"
            "   background-color: #2563eb;"
            "   color: #ffffff;"
            "}"
            "QLineEdit {"
            "   background-color: #1c1d24;"
            "   border: 1px solid #282a35;"
            "   border-radius: 12px;"
            "   padding: 10px 14px;"
            "   color: #ffffff;"
            "   font-size: 13px;"
            "}"
            "QLineEdit:focus { border-color: #3b82f6; }"
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 22, 22, 20)
        self.main_layout.setSpacing(14)

        # Header Title
        title_lbl = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #ffffff;")
        self.main_layout.addWidget(title_lbl)

        # Optional Subtitle
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setWordWrap(True)
            sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
            self.main_layout.addWidget(sub_lbl)

        # Scroll Area for Form items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { border: none; background: transparent; width: 6px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #334155; min-height: 20px; border-radius: 3px; }"
            "QScrollBar::handle:vertical:hover { background: #475569; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.form_layout = QVBoxLayout(self.scroll_content)
        self.form_layout.setContentsMargins(0, 0, 4, 0)
        self.form_layout.setSpacing(12)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, stretch=1)

        # Action Buttons Footer
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(14)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #262934;"
            "   color: #cbd5e1;"
            "   font-size: 13px;"
            "   font-weight: 600;"
            "   border-radius: 18px;"
            "   height: 44px;"
            "   border: none;"
            "}"
            "QPushButton:hover { background-color: #2f3342; color: #ffffff; }"
        )
        self.cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("CONFIRM")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #2563eb;"
            "   color: #ffffff;"
            "   font-size: 13px;"
            "   font-weight: 600;"
            "   border-radius: 18px;"
            "   height: 44px;"
            "   border: none;"
            "}"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        self.confirm_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.confirm_btn)

        self.main_layout.addLayout(footer_layout)

    def add_section_header(self, text: str) -> QLabel:
        lbl = QLabel(f"<span style='color: #3b82f6;'>●</span> <span style='color: #e2e8f0; font-size: 13px; font-weight: 600;'>{text}</span>")
        self.form_layout.addWidget(lbl)
        return lbl

    def add_field_subtitle(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        self.form_layout.addWidget(lbl)
        return lbl


# =====================================================================
# Specific Extended Dialogs Matching Screenshots in UI_example/1
# =====================================================================

class UnpackImgDialog(BaseOperationDialog):
    """Unpack img modal matching Screenshot_2026-10-11-01-29-33-565_com.dna.tools.jpg."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Unpack img", parent=parent)

        # 1. Delete source file card
        self.chk_delete_source = CheckboxCard("Delete source file", "Delete source file after unpack", checked=False)
        self.form_layout.addWidget(self.chk_delete_source)

        # 2. Select IMG files to unpack
        self.add_section_header("Select IMG files to unpack")
        img_candidates = []
        if proj:
            img_candidates = [
                f for f in (list(proj.images.glob("*.img")) + list(proj.project_dir.glob("*.img")))
                if f.name != "super.img"
            ]
        self.file_picker = FileSelectField(
            candidate_files=img_candidates,
            subtitle="Select partition img files under ~/DNA project path",
            dialog_title="Select Partition Images to Unpack",
        )
        self.form_layout.addWidget(self.file_picker)

        # 3. Hint card
        hint_lbl = QLabel(
            "HINT: If you encounter an error unpack EROFS, please unpack with super.img "
            "or turn off \"Unpack erofs by chunk\" in general settings."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet(
            "background-color: #171b26; border: 1px solid #1e3a8a; border-radius: 10px; padding: 10px 12px; color: #93c5fd; font-size: 11px; line-height: 1.4;"
        )
        self.form_layout.addWidget(hint_lbl)

    def get_delete_source(self) -> bool:
        return self.chk_delete_source.is_checked()

    def get_selected_files(self) -> list[Path]:
        return self.file_picker.get_selected_files()


class UnpackZstdDialog(BaseOperationDialog):
    """Unpack zstd modal matching Screenshot_2026-10-11-01-29-36-702_com.dna.tools.jpg."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Unpack zstd", parent=parent)

        self.chk_delete_source = CheckboxCard("Delete source file", "Delete source file after unpack", checked=False)
        self.form_layout.addWidget(self.chk_delete_source)

        self.add_section_header("Select ZSTD files to unpack")
        zst_candidates = []
        if proj:
            zst_candidates = list(proj.images.glob("*.zst")) + list(proj.images.glob("*.zstd")) + list(proj.project_dir.glob("*.zst"))
        self.file_picker = FileSelectField(
            candidate_files=zst_candidates,
            subtitle="Select zstd files under project path",
            dialog_title="Select Zstandard Archives",
        )
        self.form_layout.addWidget(self.file_picker)

    def get_delete_source(self) -> bool:
        return self.chk_delete_source.is_checked()

    def get_selected_files(self) -> list[Path]:
        return self.file_picker.get_selected_files()


class RepackZstdDialog(BaseOperationDialog):
    """Repack zstd modal matching Screenshot_2026-10-11-01-29-42-145_com.dna.tools.jpg."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Repack zstd", parent=parent)

        self.chk_delete_source = CheckboxCard("Delete source file", "Delete source file after repack", checked=False)
        self.form_layout.addWidget(self.chk_delete_source)

        self.add_section_header("Select files to repack")
        candidates = []
        if proj:
            candidates = [f for f in proj.images.glob("*.img") if f.name != "super.img"]
        self.file_picker = FileSelectField(
            candidate_files=candidates,
            subtitle="Select files to repack with zstd under project path",
            dialog_title="Select Files to Compress with Zstd",
        )
        self.form_layout.addWidget(self.file_picker)

        self.add_section_header("Select zstd compression level")
        self.stepper = NumberStepper(min_val=1, max_val=22, default_val=3, subtitle="Default: 3 (1-22)")
        self.form_layout.addWidget(self.stepper)

    def get_delete_source(self) -> bool:
        return self.chk_delete_source.is_checked()

    def get_selected_files(self) -> list[Path]:
        return self.file_picker.get_selected_files()

    def get_compression_level(self) -> int:
        return self.stepper.get_value()


class RepackSingleImgDialog(BaseOperationDialog):
    """Repack single partition modal matching Screenshot_2026-10-11-01-29-46-660 & 48-377."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Repack single img partition", parent=parent)
        self.setFixedSize(480, 720)
        self.proj = proj

        # Detect candidate partition targets from workspace
        img_candidates = get_repack_partition_candidates(proj, mode="img")
        folder_candidates = get_repack_partition_candidates(proj, mode="folder")
        initial_mode = "Folder" if (not img_candidates and folder_candidates) else "IMG"
        initial_candidates = folder_candidates if initial_mode == "Folder" else (img_candidates or folder_candidates)

        # 1. Target selector (Card matching top item in Screenshot_2026-10-11-01-29-46-660)
        self.file_picker = FileSelectField(
            candidate_files=initial_candidates,
            subtitle="Supports multiple repacking; tool will automatically detect image format",
            dialog_title="Select Partition to Repack",
        )
        self.form_layout.addWidget(self.file_picker)

        # 2. Packing Method (ext4 / erofs / f2fs)
        self.combo_method = StyledComboBox(borderless=True)
        self.combo_method.addItems(["ext4", "erofs", "f2fs"])
        self.combo_method.setMinimumWidth(120)
        self.card_method = OptionRowCard("Packing Method", self.combo_method)
        self.form_layout.addWidget(self.card_method)

        # 3. Partition Access (rw / ro)
        self.combo_access = StyledComboBox(borderless=True)
        self.combo_access.addItems(["Read/Write ---rw", "Read-only ---ro"])
        self.combo_access.setMinimumWidth(160)
        self.card_access = OptionRowCard(
            "Partition Access",
            self.combo_access,
            subtitle="Note: Only applicable when packing ext4",
        )
        self.form_layout.addWidget(self.card_access)

        # 4. Packing Size (Auto Calculate Size / Custom size)
        self.combo_size_mode = StyledComboBox(borderless=True)
        self.combo_size_mode.addItems(["Auto Calculate Size", "Custom size"])
        self.combo_size_mode.setMinimumWidth(160)
        self.combo_size_mode.currentTextChanged.connect(self._on_size_mode_changed)
        self.card_size = OptionRowCard(
            "Packing Size",
            self.combo_size_mode,
            subtitle="Note: Only applicable when packing ext4",
        )
        self.custom_size_edit = QLineEdit("4096")
        self.custom_size_edit.setPlaceholderText("Enter size in MB (e.g. 4096)")
        self.custom_size_edit.hide()
        self.card_size.card_layout.addWidget(self.custom_size_edit)
        self.form_layout.addWidget(self.card_size)

        # 5. Packing Format (raw, sparse, dat, dat.br)
        self.combo_format = StyledComboBox(borderless=True)
        self.combo_format.addItems([
            "Recovery Flashable Format ---raw",
            "sparse",
            "dat",
            "dat.br",
        ])
        self.combo_format.setMinimumWidth(210)
        self.card_format = OptionRowCard(
            "Packing Format",
            self.combo_format,
            subtitle="Note: Only applicable when packing ext4/erofs",
        )
        self.form_layout.addWidget(self.card_format)

        # 6. Repack From (IMG / Folder)
        self.combo_from = StyledComboBox(borderless=True)
        self.combo_from.addItems(["IMG", "Folder"])
        self.combo_from.setMinimumWidth(100)
        if initial_mode == "Folder":
            self.combo_from.setCurrentText("Folder")
        self.combo_from.currentTextChanged.connect(self._on_repack_from_changed)
        self.card_from = OptionRowCard(
            "Repack From",
            self.combo_from,
            subtitle="Note: Only applicable when packing ext4/erofs",
        )
        self.form_layout.addWidget(self.card_from)

        # 7. BR Compression (stepper 1 to 11, default 3)
        self.stepper_brotli = NumberStepper(1, 11, 3)
        self.stepper_brotli.setFixedWidth(200)
        self.card_brotli = OptionRowCard(
            "BR Compression",
            self.stepper_brotli,
            subtitle="Note: Only applies when repacking to BR; higher = slower",
        )
        self.form_layout.addWidget(self.card_brotli)

        # 8. EROFS Level (stepper 1 to 9, default 8)
        self.stepper_erofs = NumberStepper(1, 9, 8)
        self.stepper_erofs.setFixedWidth(200)
        self.card_erofs_level = OptionRowCard(
            "EROFS Level",
            self.stepper_erofs,
            subtitle="Only applies when repacking to EROFS or F2FS",
        )
        self.form_layout.addWidget(self.card_erofs_level)

        # 9. EROFS Compression (lz4hc / lz4 / lzma / none)
        self.combo_erofs_algo = StyledComboBox(borderless=True)
        self.combo_erofs_algo.addItems(["lz4hc", "lz4", "lzma", "none"])
        self.combo_erofs_algo.setMinimumWidth(110)
        self.card_erofs_algo = OptionRowCard(
            "EROFS Compression",
            self.combo_erofs_algo,
            subtitle="Note: Only applies when packing EROFS",
        )
        self.form_layout.addWidget(self.card_erofs_algo)

        # 10. Compress ext4 Image Size (toggle switch)
        self.switch_compress_ext4 = ToggleSwitch(checked=False)
        self.card_compress_ext4 = OptionRowCard(
            "Compress ext4 Image Size",
            self.switch_compress_ext4,
            subtitle="Note: This switch only affects ext4 image repacking",
        )
        self.form_layout.addWidget(self.card_compress_ext4)

        # 11. Remove AVB, Data Encryption (toggle switch)
        self.switch_remove_avb = ToggleSwitch(checked=False)
        self.card_remove_avb = OptionRowCard(
            "Remove AVB, Data Encryption",
            self.switch_remove_avb,
            subtitle="Note: This will modify fstab. May cause boot failure on some devices",
        )
        self.form_layout.addWidget(self.card_remove_avb)

    def _on_repack_from_changed(self, text: str) -> None:
        mode = "folder" if text == "Folder" else "img"
        new_cands = get_repack_partition_candidates(self.proj, mode=mode)
        for f in self.file_picker.candidate_files:
            if (mode == "folder" and f.is_dir()) or (mode == "img" and not f.is_dir()):
                if f not in new_cands:
                    new_cands.append(f)
        self.file_picker.set_candidate_files(new_cands)

    def _on_size_mode_changed(self, mode: str) -> None:
        self.custom_size_edit.setVisible("Custom" in mode)

    def get_selected_files(self) -> list[Path]:
        return self.file_picker.get_selected_files()

    def get_parameters(self) -> dict[str, Any]:
        selected = self.file_picker.get_selected_files()
        cands = self.file_picker.candidate_files
        partition_name = selected[0].stem if selected else (cands[0].stem if cands else "")
        return {
            "selected_files": selected,
            "partition": partition_name,
            "repack_from": self.combo_from.currentText(),
            "fs_type": self.combo_method.currentText(),
            "access_rights": "ro" if "ro" in self.combo_access.currentText().lower() else "rw",
            "size_mode": self.combo_size_mode.currentText(),
            "custom_size_mb": int(self.custom_size_edit.text() or "4096") if "custom" in self.combo_size_mode.currentText().lower() else None,
            "format": self.combo_format.currentText(),
            "brotli_level": self.stepper_brotli.get_value(),
            "erofs_algo": self.combo_erofs_algo.currentText(),
            "erofs_level": self.stepper_erofs.get_value(),
            "compress_ext4": self.switch_compress_ext4.isChecked(),
            "remove_avb": self.switch_remove_avb.isChecked(),
        }


class RepackSuperDialog(BaseOperationDialog):
    """Repack super.img modal matching Screenshot_2026-10-11-01-29-56-211 & 58-226."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Repack super.img", parent=parent)
        self.setFixedSize(480, 560)

        # 1. Packing Type
        self.combo_type = StyledComboBox(borderless=True)
        self.combo_type.addItems(["virtual_ab", "ab", "a_only"])
        self.card_type = OptionRowCard("Packing\nType", self.combo_type)
        self.form_layout.addWidget(self.card_type)

        # 2. Packing Format
        self.combo_format = StyledComboBox(borderless=True)
        self.combo_format.addItems(["sparse", "raw"])
        self.card_format = OptionRowCard("Packing\nFormat", self.combo_format)
        self.form_layout.addWidget(self.card_format)

        # 3. super.img Total Size
        self.edit_size = QLineEdit("8.5")
        self.edit_size.setStyleSheet(
            "background: transparent; border: none; color: #ffffff; font-size: 13px; padding: 4px 6px;"
        )
        self.card_size = OptionRowCard(
            "super.img\nTotal Size",
            self.edit_size,
            subtitle="Enter in GB. Default: 8.5GB",
        )
        self.form_layout.addWidget(self.card_size)

        # 4. Dynamic Partition
        self.edit_group = QLineEdit("qti_dynamic_partitions")
        self.edit_group.setStyleSheet(
            "background: transparent; border: none; color: #ffffff; font-size: 13px; padding: 4px 6px;"
        )
        self.card_group = OptionRowCard(
            "Dynamic\nPartition",
            self.edit_group,
            subtitle="Use default if unsure",
        )
        self.form_layout.addWidget(self.card_group)

        # 5. Partition image files selector
        self.add_section_header("Select IMG files to pack:")
        candidates = []
        if proj:
            raw_cands = (
                list(proj.images.glob("*.img")) + list(proj.project_dir.glob("*.img"))
            )
            seen = set()
            for f in raw_cands:
                if f.name.lower() != "super.img" and not f.name.startswith("."):
                    res = f.resolve()
                    if res not in seen:
                        seen.add(res)
                        candidates.append(f)

        self.file_picker = FileSelectField(
            candidate_files=candidates,
            subtitle="Detects files from ~/DNA project path",
            dialog_title="Select Partition Images for Super Image",
        )
        self.form_layout.addWidget(self.file_picker)

    def get_selected_files(self) -> list[Path]:
        return self.file_picker.get_selected_files()

    def get_parameters(self) -> dict[str, Any]:
        try:
            size_gb = float(self.edit_size.text().strip())
        except ValueError:
            size_gb = 8.5
        device_size_bytes = int(size_gb * 1024 * 1024 * 1024)

        return {
            "slot_type": self.combo_type.currentText(),
            "format": self.combo_format.currentText(),
            "sparse": self.combo_format.currentText() == "sparse",
            "device_size": device_size_bytes,
            "group_name": self.edit_group.text().strip() or "qti_dynamic_partitions",
            "selected_files": self.file_picker.get_selected_files(),
        }


class ImgSimgDialog(BaseOperationDialog):
    """img-simg Conversion modal matching Screenshot_2026-10-11-01-30-05-249_com.dna.tools.jpg."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("img-simg Conversion", parent=parent)

        self.add_section_header("Select IMG files to convert:")
        candidates = []
        if proj:
            candidates = list(proj.images.glob("*.img"))
        self.file_picker = FileSelectField(
            candidate_files=candidates,
            subtitle="Convert between raw img and sparse simg automatically",
            dialog_title="Select Images for Simg/Raw Conversion",
        )
        self.form_layout.addWidget(self.file_picker)

        self.add_section_header("Select conversion mode:")
        self.combo_mode = StyledComboBox()
        self.combo_mode.addItems(["Auto detect (Raw <-> Simg)", "Raw to Sparse (img2simg)", "Sparse to Raw (simg2img)"])
        self.form_layout.addWidget(self.combo_mode)

    def get_parameters(self) -> dict[str, Any]:
        return {
            "selected_files": self.file_picker.get_selected_files(),
            "mode": self.combo_mode.currentText(),
        }


class CorePatchDsvDialog(BaseOperationDialog):
    """Core patch - DSV modal matching Screenshot_2026-10-11-01-30-11-568 & 13-040."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Core patch - DSV",
            subtitle="Allows downgrading apps, disable signature verification and comparison on package installation.",
            parent=parent,
        )

        self.add_section_header("Select Android Version:")
        self.combo_version = StyledComboBox()
        self.combo_version.addItems(["Android 13+", "Android 15+"])
        self.form_layout.addWidget(self.combo_version)
        self.add_field_subtitle("Choose Android version")

        self.chk_invoke_custom = CheckboxCard(
            "Remove invoke-custom",
            "Disable invoke-custom usage in smali (only for Android 15+)",
            checked=False,
        )
        self.form_layout.addWidget(self.chk_invoke_custom)

    def get_parameters(self) -> dict[str, Any]:
        return {
            "android_version": self.combo_version.currentText(),
            "remove_invoke_custom": self.chk_invoke_custom.is_checked(),
        }


class DisableSecureScreenshotDialog(BaseOperationDialog):
    """Disable secure screenshot modal matching Screenshot_2026-10-11-01-30-17-319 & 18-999."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Disable secure screenshot",
            subtitle="This removes the screenshots and screenrecords limits for all applications. Normally, special applications are replaced with black areas in records. This can be convenient in some cases but may lead to privacy leaks.",
            parent=parent,
        )

        self.add_section_header("Select Android Version:")
        self.combo_version = StyledComboBox()
        self.combo_version.addItems(["Android 13+", "Android 15+"])
        self.form_layout.addWidget(self.combo_version)
        self.add_field_subtitle("Choose Android version")

        self.chk_invoke_custom = CheckboxCard(
            "Remove invoke-custom",
            "Disable invoke-custom usage in smali (only for Android 15+)",
            checked=False,
        )
        self.form_layout.addWidget(self.chk_invoke_custom)

    def get_parameters(self) -> dict[str, Any]:
        return {
            "android_version": self.combo_version.currentText(),
            "remove_invoke_custom": self.chk_invoke_custom.is_checked(),
        }


class RemoveApkProtectionDialog(BaseOperationDialog):
    """Remove Apk Protection modal matching Screenshot_2026-10-11-01-30-23-435."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Remove Apk Protection",
            subtitle="Disables built-in APK protection in stock ROMs, allowing seamless replacement of modified system applications",
            parent=parent,
        )

        self.add_section_header("Select Android Version:")
        self.combo_version = StyledComboBox()
        self.combo_version.addItems(["Android 13+", "Android 15+"])
        self.form_layout.addWidget(self.combo_version)
        self.add_field_subtitle("Choose Android version")

        self.chk_invoke_custom = CheckboxCard(
            "Remove invoke-custom",
            "Disable invoke-custom usage in equals/hashCode/toString smali methods. Only applies to Android 15+.",
            checked=False,
        )
        self.form_layout.addWidget(self.chk_invoke_custom)

    def get_parameters(self) -> dict[str, Any]:
        return {
            "android_version": self.combo_version.currentText(),
            "remove_invoke_custom": self.chk_invoke_custom.is_checked(),
        }


class PatchVbmetaDialog(BaseOperationDialog):
    """Patch vbmeta modal matching Screenshot_2026-10-11-01-30-30-543 & 31-886."""

    def __init__(self, proj: ProjectPaths | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Patch vbmeta", parent=parent)

        self.chk_delete_source = CheckboxCard("Delete source file", checked=False)
        self.form_layout.addWidget(self.chk_delete_source)

        self.add_section_header("Select vbmeta Patch Type")
        self.combo_patch_type = StyledComboBox()
        self.combo_patch_type.addItems(["Disable dm-verity", "Disable dm-verification", "Disable both"])
        self.form_layout.addWidget(self.combo_patch_type)
        self.add_field_subtitle("Choose the type of patch to apply to vbmeta.img")

        self.add_section_header("Select vbmeta IMG files to patch")
        candidates = []
        if proj:
            candidates = list(proj.images.glob("*vbmeta*.img")) + list(proj.project_dir.glob("*vbmeta*.img"))
            if not candidates:
                candidates = list(proj.images.glob("*.img"))
        self.file_picker = FileSelectField(
            candidate_files=candidates,
            subtitle="Select vbmeta image files under project path",
            dialog_title="Select vbmeta Image Files",
        )
        self.form_layout.addWidget(self.file_picker)

    def get_parameters(self) -> dict[str, Any]:
        text = self.combo_patch_type.currentText()
        if "verity" in text and "both" not in text:
            mode = "verity"
        elif "verification" in text and "both" not in text:
            mode = "verification"
        else:
            mode = "both"

        return {
            "patch_type": text,
            "mode": mode,
            "delete_source": self.chk_delete_source.is_checked(),
            "selected_files": self.file_picker.get_selected_files(),
        }


class DebloatRomDialog(BaseOperationDialog):
    """Debloat Miui/HyperOs modal matching Screenshot_2026-10-11-01-30-39-202."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Debloat Miui/HyperOs",
            subtitle="Debloat Works on all MIUI versions 13/14 and HyperOS releases 1.0/2.0/2.0.2 safely removing bloatware to boost performance and free resources",
            parent=parent,
        )

        self.add_section_header("Select ROM Type:")
        self.combo_rom_type = StyledComboBox()
        self.combo_rom_type.addItems(["Miui/HyperOs Global", "Miui/HyperOs China"])
        self.form_layout.addWidget(self.combo_rom_type)

    def get_rom_type(self) -> str:
        return "global" if "Global" in self.combo_rom_type.currentText() else "china"
