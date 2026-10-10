"""Home view mirroring the original DNA-Android home screen."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dna_core.project import get_active_project
from dna_gui.widgets.card_button import CardItemWidget


class HomeView(QWidget):
    """Home screen containing primary project controls and disclaimer card."""

    navigate_project_menu = pyqtSignal()
    request_select_project = pyqtSignal()
    request_create_project = pyqtSignal()
    request_delete_project = pyqtSignal()
    request_unzip_rom = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for smooth scrolling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 20)
        content_layout.setSpacing(20)

        # 1. Primary Action Card Container
        card_frame = QFrame()
        card_frame.setObjectName("card_container")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        # Item 1: Select Project
        self.item_select = CardItemWidget(
            title="Select Project",
            subtitle="Current project: None",
            icon_type="menu",
            subtitle_color="#38bdf8",
        )
        self.item_select.clicked.connect(self.request_select_project.emit)
        card_layout.addWidget(self.item_select)

        # Item 2: Delete Project
        self.item_delete = CardItemWidget(
            title="Delete Project",
            subtitle=None,
            icon_type="menu",
        )
        self.item_delete.clicked.connect(self.request_delete_project.emit)
        card_layout.addWidget(self.item_delete)

        # Item 3: Create New Project
        self.item_create = CardItemWidget(
            title="Create New Project",
            subtitle=None,
            icon_type="menu",
        )
        self.item_create.clicked.connect(self.request_create_project.emit)
        card_layout.addWidget(self.item_create)

        # Item 4: Unzip ROM
        self.item_unzip = CardItemWidget(
            title="Unzip ROM",
            subtitle=None,
            icon_type="menu",
        )
        self.item_unzip.clicked.connect(self.request_unzip_rom.emit)
        card_layout.addWidget(self.item_unzip)

        # Item 5: Project Menu (with '>' navigation arrow)
        self.item_project_menu = CardItemWidget(
            title="Project Menu",
            subtitle=None,
            icon_type="arrow",
        )
        self.item_project_menu.clicked.connect(self.navigate_project_menu.emit)
        card_layout.addWidget(self.item_project_menu)

        content_layout.addWidget(card_frame)

        # 2. Disclaimer Card Container
        disclaimer_frame = QFrame()
        disclaimer_frame.setObjectName("disclaimer_card")
        disclaimer_layout = QVBoxLayout(disclaimer_frame)
        disclaimer_layout.setContentsMargins(16, 16, 16, 16)
        disclaimer_layout.setSpacing(10)

        disc_title = QLabel("Disclaimer")
        disc_font = QFont()
        disc_font.setPointSize(12)
        disc_font.setBold(True)
        disc_title.setFont(disc_font)
        disc_title.setStyleSheet("color: #f3f4f6;")
        disclaimer_layout.addWidget(disc_title)

        disc_body = QLabel(
            "This tool will not actively damage the phone system, all consequences caused by "
            "improper use are borne by the user.\n\n"
            "In one sentence: Use it if you love it, uninstall if you don't.\n\n"
            "Moded By @SoutaEver | Ported to Linux by @iprjkt\n"
            "Pure native x86_64 toolchain for Arch Linux / Debian / Ubuntu."
        )
        disc_body.setWordWrap(True)
        disc_body.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.4;")
        disclaimer_layout.addWidget(disc_body)

        content_layout.addWidget(disclaimer_frame)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        self.update_active_project()

    def update_active_project(self) -> None:
        """Refresh active project label on Select Project card."""
        active = get_active_project()
        if active:
            self.item_select.set_subtitle(
                f"Current project: {active.directory}\n{active.name}",
                color="#38bdf8",
            )
        else:
            self.item_select.set_subtitle("Current project: None selected", color="#94a3b8")
