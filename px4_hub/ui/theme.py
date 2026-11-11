"""
Modern Dark Engineering Theme and QSS Stylesheet for PX4 Setup Hub.
"""

DARK_THEME_QSS = """
/* PX4 Setup Hub Dark Engineering Palette */
QMainWindow, QDialog, QWidget {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar navigation */
QFrame#Sidebar {
    background-color: #080c14;
    border-right: 1px solid #1e293b;
    min-width: 220px;
    max-width: 220px;
}

QToolButton#NavButton {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}

QToolButton#NavButton:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

QToolButton#NavButton:checked {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 600;
}

/* Header & Top Bar */
QFrame#TopHeader {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
    padding: 8px 16px;
}

/* Cards & Containers */
QFrame.Card {
    background-color: #131b2e;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 16px;
}

QFrame.Card:hover {
    border: 1px solid #334155;
}

/* Labels */
QLabel#Title {
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
}

QLabel#Subtitle {
    font-size: 12px;
    color: #94a3b8;
}

QLabel#SectionHeading {
    font-size: 14px;
    font-weight: 600;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}

QLabel#MetricValue {
    font-size: 26px;
    font-weight: 700;
    color: #f1f5f9;
}

QLabel#MetricLabel {
    font-size: 11px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton#PrimaryButton {
    background-color: #0284c7;
    border-color: #0369a1;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #0369a1;
}

QPushButton#SuccessButton {
    background-color: #16a34a;
    border-color: #15803d;
    color: #ffffff;
}

QPushButton#DangerButton {
    background-color: #dc2626;
    border-color: #b91c1c;
    color: #ffffff;
}

/* Text Inputs and ComboBox */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0a0f1d;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #0284c7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #131b2e;
    color: #f8fafc;
    border: 1px solid #334155;
    selection-background-color: #0284c7;
}

/* Tables */
QTableWidget {
    background-color: #0e1526;
    alternate-background-color: #131b2e;
    color: #f1f5f9;
    gridline-color: #1e293b;
    border: 1px solid #1e293b;
    border-radius: 6px;
}

QHeaderView::section {
    background-color: #080c16;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: 600;
}

QTableWidget::item:selected {
    background-color: #0369a1;
}

/* Progress Bar */
QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #080c14;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
