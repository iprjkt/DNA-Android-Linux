"""Interactive real-time execution console and progress drawer widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ConsoleWidget(QWidget):
    """Bottom collapsible console drawer displaying live logs, task progress, and controls."""

    close_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(220)
        self.setStyleSheet(
            "background-color: #0b0c10;"
            "border-top: 2px solid #1e2230;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(6)

        # Header bar of console
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #10b981; font-size: 14px;")
        header_layout.addWidget(self.status_icon)

        self.status_label = QLabel("Console Output (Ready)")
        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #e2e8f0;")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch(1)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(self.clear_btn)

        # Copy button
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.copy_btn.clicked.connect(self.copy_logs)
        header_layout.addWidget(self.copy_btn)

        # Hide button
        self.hide_btn = QPushButton("✕")
        self.hide_btn.setFixedSize(24, 24)
        self.hide_btn.setToolTip("Hide Console Drawer")
        self.hide_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #94a3b8; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { color: #f87171; background: #261619; border-radius: 4px; }"
        )
        self.hide_btn.clicked.connect(self.close_clicked.emit)
        header_layout.addWidget(self.hide_btn)

        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log viewer
        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("console_output")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(3000)
        layout.addWidget(self.text_edit, stretch=1)

    def append_log(self, text: str) -> None:
        """Append log message and auto-scroll to the bottom."""
        self.text_edit.appendPlainText(text)
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def set_status(self, text: str, running: bool = False, error: bool = False) -> None:
        """Update console status title and status icon color."""
        self.status_label.setText(text)
        if error:
            self.status_icon.setStyleSheet("color: #ef4444; font-size: 14px;")
            self.progress_bar.setVisible(False)
        elif running:
            self.status_icon.setStyleSheet("color: #3b82f6; font-size: 14px;")
            self.progress_bar.setRange(0, 0)  # Indeterminate pulse
            self.progress_bar.setVisible(True)
        else:
            self.status_icon.setStyleSheet("color: #10b981; font-size: 14px;")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)

    def clear_logs(self) -> None:
        self.text_edit.clear()

    def copy_logs(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_edit.toPlainText())
            self.append_log("[System] Logs copied to clipboard.")
