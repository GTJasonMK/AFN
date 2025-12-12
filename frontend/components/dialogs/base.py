"""
对话框基类 - 主题适配

提供所有自定义对话框的基础功能，包括无边框窗口、主题信号连接等。
"""

from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager


class BaseDialog(QDialog):
    """对话框基类 - 主题适配"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._theme_connected = False
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题信号"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except TypeError:
                pass
            self._theme_connected = False

    def _on_theme_changed(self):
        """主题变更回调"""
        self._apply_theme()

    def _apply_theme(self):
        """应用主题 - 子类实现"""
        pass

    def closeEvent(self, event):
        """关闭时断开信号"""
        self._disconnect_theme_signal()
        super().closeEvent(event)
