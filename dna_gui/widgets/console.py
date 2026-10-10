"""Interactive real-time execution log and terminal widget matching original DNA-Android UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ConsoleWidget(QWidget):
    """Right-side log view precisely mirroring Screenshot_2026-10-10-19-24-56-881_com.dna.tools.jpg

    and Screenshot_2026-10-10-19-25-26-527_com.dna.tools.jpg.
    """

    close_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        # 1. Action Title Header
        self.task_title = QLabel("DNA-Android Terminal")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        self.task_title.setFont(title_font)
        self.task_title.setStyleSheet("color: #ffffff; background: transparent; padding-left: 2px;")
        layout.addWidget(self.task_title)

        # 2. Sleek Horizontal Progress Accent Line
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("log_progress")
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 3. Main Dark Terminal Card
        self.log_card = QFrame()
        self.log_card.setObjectName("log_card")
        card_layout = QVBoxLayout(self.log_card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(0)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("console_output")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(5000)
        card_layout.addWidget(self.text_edit)

        layout.addWidget(self.log_card, stretch=1)

        # 4. Bottom Action Buttons: [ COPY THE OUTPUT ]  [ EXIT ]
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setContentsMargins(0, 4, 0, 0)
        self.btn_layout.setSpacing(12)

        self.copy_btn = QPushButton("COPY THE OUTPUT")
        self.copy_btn.setObjectName("btn_copy_output")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #1a1e28;"
            "   color: #3b82f6;"
            "   border: 1px solid #283042;"
            "   border-radius: 22px;"
            "   font-size: 12px;"
            "   font-weight: 700;"
            "   letter-spacing: 0.5px;"
            "   padding: 10px 18px;"
            "   min-height: 42px;"
            "}"
            "QPushButton:hover { background-color: #242938; color: #60a5fa; border-color: #3b82f6; }"
            "QPushButton:pressed { background-color: #151821; }"
        )
        self.copy_btn.clicked.connect(self.copy_logs)
        self.btn_layout.addWidget(self.copy_btn, stretch=1)

        self.exit_btn = QPushButton("EXIT")
        self.exit_btn.setObjectName("btn_exit_log")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #2563eb;"
            "   color: #ffffff;"
            "   border: none;"
            "   border-radius: 22px;"
            "   font-size: 12px;"
            "   font-weight: 700;"
            "   letter-spacing: 0.5px;"
            "   padding: 10px 18px;"
            "   min-height: 42px;"
            "}"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:pressed { background-color: #1e40af; }"
        )
        self.exit_btn.clicked.connect(self._on_exit_clicked)
        self.exit_btn.setVisible(False)
        self.btn_layout.addWidget(self.exit_btn, stretch=1)


        layout.addLayout(self.btn_layout)

    def append_log(self, text: str) -> None:
        """Append log line with '> ' prefix formatting and auto-scroll to the end."""
        if not text:
            return

        lines = text.splitlines()
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                self.text_edit.appendPlainText("")
                continue

            # Format like the original DNA-Android output
            if (
                line_stripped.startswith(">")
                or line_stripped.startswith("[")
                or "Script execution" in line_stripped
            ):
                formatted = line_stripped
            else:
                formatted = f"> {line_stripped}"

            self.text_edit.appendPlainText(formatted)

        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def set_status(self, text: str, running: bool = False, error: bool = False) -> None:
        """Update action title and progress bar state matching the original Android behavior."""
        self.task_title.setText(text)
        if running:
            self.progress_bar.setRange(0, 0)  # Smooth indeterminate pulse
            self.progress_bar.setVisible(True)
            self.exit_btn.setVisible(False)
            self.copy_btn.setText("COPY THE OUTPUT")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            self.exit_btn.setVisible(True)
            if not error and self.text_edit.toPlainText():
                # Append standard completion note if not already present
                plain = self.text_edit.toPlainText().strip()
                if not plain.endswith("Script execution completed"):
                    self.text_edit.appendPlainText("Script execution completed")
                    self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self) -> None:
        """Clear all terminal text and reset view to initial state."""
        self.text_edit.clear()
        self.task_title.setText("DNA-Android Terminal")
        self.progress_bar.setVisible(False)
        self.exit_btn.setVisible(False)
        self.copy_btn.setText("COPY THE OUTPUT")

    def copy_logs(self) -> None:
        """Copy full log content to system clipboard with visual button confirmation."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_edit.toPlainText())
            self.copy_btn.setText("COPIED TO CLIPBOARD")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("COPY THE OUTPUT"))

    def _on_exit_clicked(self) -> None:
        """Handle EXIT button click: reset console output and emit exit signal."""
        self.clear_logs()
        self.exit_clicked.emit()
        self.close_clicked.emit()


# Alias for backwards compatibility
LogWidget = ConsoleWidget
