"""Header navigation and status widget for DNA-Linux GUI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class CircleIconButton(QPushButton):
    """Circular outlined vector icon button matching original DNA-Android UI."""

    def __init__(self, icon_type: str, tooltip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_type = icon_type  # "power" or "info"
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self._hovered = False

    def enterEvent(self, event: Any) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Border and background colors
        if self._hovered:
            if self.icon_type == "power":
                bg_color = QColor("#3b151a")
                border_color = QColor("#ef4444")
                icon_color = QColor("#ef4444")
            else:
                bg_color = QColor("#1e293b")
                border_color = QColor("#38bdf8")
                icon_color = QColor("#38bdf8")
        else:
            bg_color = QColor("#181920")
            border_color = QColor("#334155")
            icon_color = QColor("#e2e8f0")

        # Draw circle container
        painter.setBrush(bg_color)
        pen = QPen(border_color, 1.2)
        painter.setPen(pen)
        painter.drawEllipse(2, 2, 32, 32)

        # Draw vector icon
        if self.icon_type == "power":
            icon_pen = QPen(icon_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(icon_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Power arc: 260 degree arc with top gap
            painter.drawArc(10, 10, 16, 16, 50 * 16, 260 * 16)
            # Top vertical line
            painter.drawLine(18, 9, 18, 17)
        elif self.icon_type == "info":
            painter.setPen(icon_color)
            font = painter.font()
            font.setFamily("-apple-system, Segoe UI, Roboto, sans-serif")
            font.setPointSize(13)
            font.setBold(True)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "i")


class BackButton(QPushButton):
    """Circular back navigation button with crisp vector arrow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Back")
        self._hovered = False

    def enterEvent(self, event: Any) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor("#262938") if self._hovered else QColor("#1a1c24")
        border = QColor("#38bdf8") if self._hovered else QColor("#272a38")
        fg = QColor("#38bdf8") if self._hovered else QColor("#f3f4f6")

        painter.setBrush(bg)
        painter.setPen(QPen(border, 1.2))
        painter.drawEllipse(2, 2, 32, 32)

        pen = QPen(fg, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        # Arrow shaft: from x=23 to x=13 at y=18
        painter.drawLine(23, 18, 13, 18)
        # Top barb: from (17, 13) to (13, 18)
        painter.drawLine(17, 13, 13, 18)
        # Bottom barb: from (17, 23) to (13, 18)
        painter.drawLine(17, 23, 13, 18)


class HeaderWidget(QWidget):
    """Top bar containing navigation back button, title, project badge, and global actions."""

    back_clicked = pyqtSignal()
    project_badge_clicked = pyqtSignal()
    doctor_clicked = pyqtSignal()
    info_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet("background-color: #121318; border-bottom: 1px solid #1f222e;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        # Back button
        self.back_btn = BackButton(self)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setVisible(False)
        layout.addWidget(self.back_btn)


        # Title
        self.title_label = QLabel("DNA-Android")
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

        # Power / Exit button (IEC Standby icon)
        self.quit_btn = CircleIconButton(icon_type="power", tooltip="Exit Application")
        self.quit_btn.clicked.connect(self.quit_clicked.emit)
        layout.addWidget(self.quit_btn)

        # Info button (ⓘ icon)
        self.info_btn = CircleIconButton(icon_type="info", tooltip="About · DNA")
        self.info_btn.clicked.connect(self.info_clicked.emit)
        layout.addWidget(self.info_btn)


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
