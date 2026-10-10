"""Modern Dark Theme stylesheet and color palette for DNA-Linux GUI."""

DARK_THEME_QSS = """
/* Global Application Style */
QWidget {
    background-color: #0f1015;
    color: #e5e7eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f1015;
}

QDialog {
    background-color: #12131a;
    border: 1px solid #252837;
    border-radius: 12px;
}

/* Scroll Area & Viewport */
QScrollArea {
    background-color: #0f1015;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #0f1015;
}

QScrollBar:vertical {
    border: none;
    background: #111218;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #2a2c3a;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #38bdf8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

/* Card Containers */
QFrame#card_container {
    background-color: #171821;
    border: 1px solid #232532;
    border-radius: 16px;
    padding: 8px;
}

QFrame#disclaimer_card {
    background-color: #171821;
    border: 1px solid #232532;
    border-radius: 16px;
    padding: 16px;
}

QLabel#section_header {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-left: 6px;
    margin-bottom: 4px;
    margin-top: 14px;
    background: transparent;
}

/* PushButtons */
QPushButton {
    background-color: #1b1d27;
    color: #f3f4f6;
    border: 1px solid #282a39;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #242735;
    border-color: #38bdf8;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #181922;
    border-color: #0284c7;
}

QPushButton:disabled {
    background-color: #13141a;
    color: #4b5563;
    border-color: #1e2029;
}

QPushButton#btn_primary {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: #0369a1;
    border-color: #7dd3fc;
}

QPushButton#btn_danger {
    background-color: #7f1d1d;
    color: #fecaca;
    border: 1px solid #991b1b;
    font-weight: 600;
}

QPushButton#btn_danger:hover {
    background-color: #991b1b;
    color: #ffffff;
}

/* Inputs and LineEdits */
QLineEdit, QComboBox {
    background-color: #13141c;
    color: #f3f4f6;
    border: 1px solid #272a39;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #0284c7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #161822;
}

QComboBox::drop-down {
    border: none;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161822;
    color: #f3f4f6;
    selection-background-color: #0284c7;
    border: 1px solid #272a39;
    border-radius: 6px;
    padding: 4px;
}

/* Progress Bar */
QProgressBar {
    background-color: #13141c;
    border: 1px solid #252837;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: #e5e7eb;
}

QProgressBar::chunk {
    background-color: #38bdf8;
    border-radius: 4px;
}

/* Tables and Lists */
QTableWidget, QListWidget {
    background-color: #13141c;
    color: #e5e7eb;
    border: 1px solid #232532;
    border-radius: 8px;
    gridline-color: #1d1f2b;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #172554;
    color: #38bdf8;
}

QHeaderView::section {
    background-color: #171822;
    color: #94a3b8;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #232532;
    font-weight: 600;
}

/* Console Output */
QPlainTextEdit#console_output {
    background-color: #0a0b0e;
    color: #4ade80;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 11px;
    border: 1px solid #1f212d;
    border-radius: 8px;
    padding: 8px;
}
"""
