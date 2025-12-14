# -*- coding: utf-8 -*-
"""
应用程序主题样式
"""

CLAUDE_THEME = """
/* ==================== Claude 暖色主题 ==================== */
/* 基于 morningtheme.css 的 Claude 官方配色 */

/* 主窗口 */
QMainWindow {
    background-color: #f1ede6;
}

/* 通用控件 */
QWidget {
    background-color: #f7f3ee;
    color: #2c2621;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
}

/* ==================== 标签页 ==================== */
QTabWidget::pane {
    border: 1px solid #ddd9d3;
    background-color: #f7f3ee;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #ebe8e3;
    color: #615e5a;
    padding: 10px 24px;
    border: 1px solid #ddd9d3;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #f7f3ee;
    color: #2c2621;
    border-bottom: 2px solid #c6613f;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #e8e4df;
    color: #c6613f;
}

/* ==================== 输入控件 ==================== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 6px;
    padding: 8px 12px;
    color: #2c2621;
    selection-background-color: rgba(198, 97, 63, 0.25);
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #c6613f;
    background-color: #ffffff;
}

QLineEdit:hover, QTextEdit:hover {
    border-color: #c6613f;
}

/* ==================== 下拉框 ==================== */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 6px;
    padding: 6px 12px;
    color: #2c2621;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #c6613f;
}

QComboBox:focus {
    border: 2px solid #c6613f;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #615e5a;
}

QComboBox::down-arrow:hover {
    border-top-color: #c6613f;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 6px;
    selection-background-color: rgba(198, 97, 63, 0.15);
    selection-color: #2c2621;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    min-height: 24px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #e8e4df;
}

QComboBox QAbstractItemView::item:selected {
    background-color: rgba(198, 97, 63, 0.15);
    color: #c6613f;
}

/* ==================== 数值输入框 ==================== */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 6px;
    padding: 6px 8px;
    color: #2c2621;
}

QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #c6613f;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #c6613f;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #ebe8e3;
    border: none;
    width: 20px;
    border-radius: 3px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #c6613f;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #615e5a;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #615e5a;
    width: 0;
    height: 0;
}

QSpinBox::up-button:hover QSpinBox::up-arrow,
QDoubleSpinBox::up-button:hover QDoubleSpinBox::up-arrow,
QSpinBox::down-button:hover QSpinBox::down-arrow,
QDoubleSpinBox::down-button:hover QDoubleSpinBox::down-arrow {
    border-top-color: #ffffff;
    border-bottom-color: #ffffff;
}

/* ==================== 按钮 ==================== */
QPushButton {
    background-color: #c6613f;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    min-width: 70px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #b2512b;
}

QPushButton:pressed {
    background-color: #9a4425;
}

QPushButton:disabled {
    background-color: #ddd9d3;
    color: #9a9590;
}

/* 次要按钮样式 */
QPushButton[secondary="true"] {
    background-color: transparent;
    color: #2c2621;
    border: 1px solid #ddd9d3;
}

QPushButton[secondary="true"]:hover {
    background-color: #e8e4df;
    border-color: #c6613f;
    color: #c6613f;
}

/* ==================== 分组框 ==================== */
QGroupBox {
    background-color: #f7f3ee;
    border: 1px solid #ddd9d3;
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 2px;
    padding: 0 8px;
    background-color: #f7f3ee;
    color: #1a1714;
}

/* ==================== 进度条 ==================== */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #ebe4db;
    text-align: center;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #c6613f;
    border-radius: 6px;
}

/* ==================== 滚动条 ==================== */
QScrollBar:vertical {
    background-color: #f1ede6;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #ddd9d3;
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #c6613f;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: #f1ede6;
    height: 12px;
    margin: 0;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #ddd9d3;
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #c6613f;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ==================== 滚动区域 ==================== */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ==================== 复选框 ==================== */
QCheckBox {
    spacing: 8px;
    color: #2c2621;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ddd9d3;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #c6613f;
}

QCheckBox::indicator:checked {
    background-color: #c6613f;
    border-color: #c6613f;
}

QCheckBox::indicator:checked:hover {
    background-color: #b2512b;
    border-color: #b2512b;
}

/* ==================== 标签 ==================== */
QLabel {
    background-color: transparent;
    color: #2c2621;
}

/* ==================== 分割器 ==================== */
QSplitter::handle {
    background-color: #ddd9d3;
}

QSplitter::handle:hover {
    background-color: #c6613f;
}

QSplitter::handle:horizontal {
    width: 3px;
}

QSplitter::handle:vertical {
    height: 3px;
}

/* ==================== 工具提示 ==================== */
QToolTip {
    background-color: #2c2621;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ==================== 消息框 ==================== */
QMessageBox {
    background-color: #f7f3ee;
}

QMessageBox QLabel {
    color: #2c2621;
}

QMessageBox QPushButton {
    min-width: 80px;
    min-height: 28px;
}

/* ==================== 文件对话框 ==================== */
QFileDialog {
    background-color: #f7f3ee;
}

QFileDialog QListView, QFileDialog QTreeView {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 6px;
    selection-background-color: rgba(198, 97, 63, 0.15);
}

/* ==================== 菜单 ==================== */
QMenu {
    background-color: #ffffff;
    border: 1px solid #ddd9d3;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: rgba(198, 97, 63, 0.12);
    color: #c6613f;
}

QMenu::separator {
    height: 1px;
    background-color: #ddd9d3;
    margin: 6px 12px;
}

/* ==================== 框架 ==================== */
QFrame {
    background-color: transparent;
}

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    background-color: #ddd9d3;
}
"""
