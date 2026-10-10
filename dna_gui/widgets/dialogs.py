"""Custom styled modal dialogs for DNA-Linux GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dna_core.project import (
    create_project,
    delete_project,
    get_active_project,
    list_projects,
    select_project,
)
from dna_core.tools import run_doctor


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

            # Col 0: Tool Name
            item_name = QTableWidgetItem(name)
            item_name.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, item_name)

            # Col 1: Status
            if found:
                item_status = QTableWidgetItem("✓ Found")
                item_status.setForeground(Qt.GlobalColor.green)
            else:
                missing_count += 1
                item_status = QTableWidgetItem("✗ Missing")
                item_status.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 1, item_status)

            # Col 2: Version
            item_ver = QTableWidgetItem(str(version))
            item_ver.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 2, item_ver)

            # Col 3: Required By
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
