"""Card item widget mirroring the DNA-Android tactile UI components."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class TrailingIcon(QWidget):
    """Draws a clean vector icon (hamburger bars, chevron arrow, or action badge)."""

    def __init__(self, icon_type: str = "menu", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(28, 28)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("#38bdf8")  # Vibrant sky blue accent
        pen = QPen(color)

        if self.icon_type == "arrow":
            pen.setWidth(2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            # Draw chevron right '>'
            painter.drawLine(10, 8, 18, 14)
            painter.drawLine(18, 14, 10, 20)
        else:
            # Draw 3 hamburger bars
            pen.setWidth(3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(6, 8, 22, 8)
            painter.drawLine(6, 14, 22, 14)
            painter.drawLine(6, 20, 22, 20)

        painter.end()


class CardItemWidget(QWidget):
    """Clickable list item widget inside rounded card containers."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        icon_type: str = "menu",
        subtitle_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("card_item")
        self.setProperty("hovered", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #f3f4f6; background: transparent;")

        text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)
        sub_font = QFont()
        sub_font.setPointSize(9)
        self.subtitle_label.setFont(sub_font)
        self.default_sub_color = subtitle_color or "#94a3b8"
        self.set_subtitle(subtitle, color=self.default_sub_color)

        text_layout.addWidget(self.subtitle_label)
        layout.addLayout(text_layout, stretch=1)

        # Trailing action icon
        self.trailing_icon = TrailingIcon(icon_type=icon_type)
        layout.addWidget(self.trailing_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._update_style(hovered=False)

    def set_subtitle(self, text: str | None, color: str | None = None) -> None:
        """Update subtitle text and color dynamically."""
        if not text:
            self.subtitle_label.setText("")
            self.subtitle_label.setVisible(False)
            return

        c = color or self.default_sub_color
        self.subtitle_label.setText(text)
        self.subtitle_label.setStyleSheet(f"color: {c}; background: transparent; line-height: 1.3;")
        self.subtitle_label.setVisible(True)

    def mousePressEvent(self, a0) -> None:
        if a0.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(a0)

    def enterEvent(self, a0) -> None:
        self._update_style(hovered=True)
        super().enterEvent(a0)

    def leaveEvent(self, a0) -> None:
        self._update_style(hovered=False)
        super().leaveEvent(a0)

    def _update_style(self, hovered: bool) -> None:
        if hovered:
            self.setStyleSheet(
                "QWidget#card_item {"
                "   background-color: #232634;"
                "   border: 1px solid #3b82f6;"
                "   border-radius: 10px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QWidget#card_item {"
                "   background-color: #191b24;"
                "   border: 1px solid #232635;"
                "   border-radius: 10px;"
                "}"
            )
