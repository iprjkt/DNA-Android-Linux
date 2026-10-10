"""Plugin management view for DNA-Linux GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dna_core.plugin import delete_plugin, import_plugin, list_plugins
from dna_gui.widgets.dialogs import ConfirmDialog


class PluginsView(QWidget):
    """View displaying installed plugins with run, import, and delete controls."""

    request_run_plugin = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # Header controls
        top_layout = QHBoxLayout()
        title_lbl = QLabel("Installed Plugins")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #ffffff;")
        top_layout.addWidget(title_lbl)

        top_layout.addStretch(1)

        self.import_btn = QPushButton("+ Import Plugin (.zip)")
        self.import_btn.setObjectName("btn_primary")
        self.import_btn.clicked.connect(self._import_dialog)
        top_layout.addWidget(self.import_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        top_layout.addWidget(self.refresh_btn)

        layout.addLayout(top_layout)

        # Plugins Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID / Name", "Version", "Author", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

        # Bottom action row
        bottom_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run Selected Plugin")
        self.run_btn.setObjectName("btn_primary")
        self.run_btn.clicked.connect(self._run_selected)
        bottom_layout.addWidget(self.run_btn)

        self.delete_btn = QPushButton("Delete Plugin")
        self.delete_btn.setObjectName("btn_danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        bottom_layout.addWidget(self.delete_btn)

        bottom_layout.addStretch(1)
        layout.addLayout(bottom_layout)

        self.refresh_plugins()

    def refresh_plugins(self) -> None:
        """Reload installed plugins list from filesystem."""
        plugins = list_plugins()
        self.table.setRowCount(len(plugins))

        for row, p in enumerate(plugins):
            item_id = QTableWidgetItem(f"{p.id} ({p.name})")
            item_id.setData(Qt.ItemDataRole.UserRole, p.id)
            item_id.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, item_id)

            item_ver = QTableWidgetItem(p.version)
            item_ver.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(row, 1, item_ver)

            item_auth = QTableWidgetItem(p.author)
            item_auth.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 2, item_auth)

            item_desc = QTableWidgetItem(p.description)
            item_desc.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 3, item_desc)

    def _get_selected_plugin_id(self) -> str | None:
        curr = self.table.currentRow()
        if curr < 0:
            return None
        item = self.table.item(curr, 0)
        if not item:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def _run_selected(self) -> None:
        p_id = self._get_selected_plugin_id()
        if not p_id:
            QMessageBox.warning(self, "No Selection", "Please select a plugin from the table.")
            return
        self.request_run_plugin.emit(p_id)

    def _delete_selected(self) -> None:
        p_id = self._get_selected_plugin_id()
        if not p_id:
            return
        confirm = ConfirmDialog(
            "Delete Plugin",
            f"Are you sure you want to delete plugin '{p_id}'?",
            confirm_text="Delete",
            is_danger=True,
            parent=self,
        )
        if confirm.exec() == ConfirmDialog.DialogCode.Accepted:
            try:
                from dna_core.plugin import get_plugin
                p_meta = get_plugin(p_id)
                delete_plugin(p_meta)
                self.refresh_plugins()
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _import_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Plugin Archive",
            "",
            "ZIP Archives (*.zip *.zip2);;All Files (*)",
        )
        if file_path:
            try:
                from dna_core.plugin import get_global_plugins_dir
                dest = import_plugin(Path(file_path), get_global_plugins_dir(), scope="global", overwrite=True)
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Successfully imported plugin: {dest.name} ({dest.id})!",
                )
                self.refresh_plugins()
            except Exception as exc:
                QMessageBox.critical(self, "Import Error", str(exc))
