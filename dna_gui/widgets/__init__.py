"""Custom widgets for DNA-Linux GUI."""

from dna_gui.widgets.card_button import CardItemWidget
from dna_gui.widgets.console import ConsoleWidget
from dna_gui.widgets.dialogs import (
    AboutDialog,
    ConfirmDialog,
    DeleteProjectDialog,
    DoctorDialog,
    InputDialog,
    SelectProjectDialog,
)
from dna_gui.widgets.header import HeaderWidget

__all__ = [
    "CardItemWidget",
    "ConsoleWidget",
    "HeaderWidget",
    "SelectProjectDialog",
    "DeleteProjectDialog",
    "DoctorDialog",
    "ConfirmDialog",
    "InputDialog",
    "AboutDialog",
]

