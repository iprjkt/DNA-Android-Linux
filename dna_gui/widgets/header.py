"""Header navigation and status widget for DNA-Linux GUI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class HeaderWidget(QWidget):
    """Top bar containing navigation back button, title, project badge, and global actions."""

    back_clicked = pyqtSignal()
    project_badge_clicked = pyqtSignal()
    doctor_clicked = pyqtSignal()
    console_toggle_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet("background-color: #121318; border-bottom: 1px solid #1f222e;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Back button
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(36, 36)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet(
            "QPushButton {"
            "   background: #1a1c24;"
            "   border: 1px solid #272a38;"
            "   border-radius: 18px;"
            "   color: #f3f4f6;"
            "   font-size: 18px;"
            "   font-weight: bold;"
            "   padding-bottom: 2px;"
            "}"
            "QPushButton:hover { background: #262938; border-color: #38bdf8; color: #38bdf8; }"
        )
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setVisible(False)
        layout.addWidget(self.back_btn)

        # Title
        self.title_label = QLabel("DNA-Linux")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(self.title_label)

        layout.addStretch(1)

        # Active Project Pill
        self.project_btn = QPushButton("Project: None")
        self.project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #172033;"
            "   color: #38bdf8;"
            "   border: 1px solid #1e3a8a;"
            "   border-radius: 14px;"
            "   padding: 5px 12px;"
            "   font-size: 11px;"
            "   font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "   background-color: #1e3a8a;"
            "   color: #ffffff;"
            "}"
        )
        self.project_btn.clicked.connect(self.project_badge_clicked.emit)
        layout.addWidget(self.project_btn)

        # Tool Doctor Button
        self.doctor_btn = QPushButton("🩺 Doctor")
        self.doctor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.doctor_btn.setStyleSheet(
            "QPushButton { background: #1a1c24; border: 1px solid #272a38; border-radius: 8px; color: #cbd5e1; font-size: 11px; padding: 5px 10px; }"
            "QPushButton:hover { background: #262938; border-color: #10b981; color: #10b981; }"
        )
        self.doctor_btn.clicked.connect(self.doctor_clicked.emit)
        layout.addWidget(self.doctor_btn)

        # Logs / Console Toggle
        self.console_btn = QPushButton("⌨ Logs")
        self.console_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.console_btn.setStyleSheet(
            "QPushButton { background: #1a1c24; border: 1px solid #272a38; border-radius: 8px; color: #cbd5e1; font-size: 11px; padding: 5px 10px; }"
            "QPushButton:hover { background: #262938; border-color: #3b82f6; color: #60a5fa; }"
        )
        self.console_btn.clicked.connect(self.console_toggle_clicked.emit)
        layout.addWidget(self.console_btn)

        # Quit / Power button
        self.quit_btn = QPushButton("⏻")
        self.quit_btn.setFixedSize(36, 36)
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.setToolTip("Exit Application")
        self.quit_btn.setStyleSheet(
            "QPushButton { background: #27171a; border: 1px solid #4a1d24; border-radius: 18px; color: #f87171; font-size: 15px; font-weight: bold; }"
            "QPushButton:hover { background: #7f1d1d; color: #ffffff; border-color: #ef4444; }"
        )
        self.quit_btn.clicked.connect(self.quit_clicked.emit)
        layout.addWidget(self.quit_btn)

    def set_title(self, title: str, show_back: bool = False) -> None:
        """Update header title and back button visibility."""
        self.title_label.setText(title)
        self.back_btn.setVisible(show_back)

    def set_active_project(self, project_name: str | None) -> None:
        """Update active project text in header badge."""
        if project_name:
            self.project_btn.setText(f"📁 {project_name}")
            self.project_btn.setToolTip(f"Active Project: {project_name} (Click to switch)")
        else:
            self.project_btn.setText("📁 No Active Project")
            self.project_btn.setToolTip("Click to select or create a project")
