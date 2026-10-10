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
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #1e2230;
    min-height: 24px;
    border-radius: 3px;
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

/* Console Output & Log UI */
QFrame#log_card {
    background-color: #080a0f;
    border: 1px solid #1a2234;
    border-radius: 16px;
}

QPlainTextEdit#console_output {
    background-color: transparent;
    color: #cbd5e1;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 11px;
    border: none;
    padding: 6px;
}

QPushButton#btn_copy_output {
    background-color: #1a1e28;
    color: #3b82f6;
    border: 1px solid #283042;
    border-radius: 22px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 10px 18px;
    min-height: 42px;
}

QPushButton#btn_copy_output:hover {
    background-color: #242938;
    color: #60a5fa;
    border-color: #3b82f6;
}

QPushButton#btn_copy_output:pressed {
    background-color: #151821;
}

QPushButton#btn_exit_log {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 22px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 10px 18px;
    min-height: 42px;
}

QPushButton#btn_exit_log:hover {
    background-color: #1d4ed8;
}

QPushButton#btn_exit_log:pressed {
    background-color: #1e40af;
}

QProgressBar#log_progress {
    background-color: #11141d;
    border: none;
    border-radius: 1px;
    height: 3px;
    max-height: 3px;
}

QProgressBar#log_progress::chunk {
    background-color: #38bdf8;
    border-radius: 1px;
}

QSplitter {
    background-color: transparent;
}

QSplitter::handle:horizontal {
    background-color: #171822;
    width: 4px;
    margin: 8px 1px;
    border-radius: 2px;
}

QSplitter::handle:horizontal:hover {
    background-color: #38bdf8;
}
"""


