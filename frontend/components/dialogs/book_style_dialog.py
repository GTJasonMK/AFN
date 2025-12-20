"""
书籍风格对话框基类

为设置页面等需要书籍风格的标准 Qt 对话框提供统一的主题管理。
与 BaseDialog（无边框自定义对话框）不同，此基类保留标准窗口框架。

用法：
    from components.dialogs.book_style_dialog import BookStyleDialog
    from components.dialogs.styles import DialogStyles

    class MyConfigDialog(BookStyleDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("配置")
            self._create_ui_structure()
            self._apply_theme()

        def _create_ui_structure(self):
            # 创建UI组件
            pass

        def _apply_theme(self):
            # 应用主题，使用 DialogStyles 的 book_* 方法
            self.setStyleSheet(DialogStyles.book_dialog_background())
"""

from PyQt6.QtWidgets import QDialog
from themes.theme_manager import theme_manager


class BookStyleDialog(QDialog):
    """书籍风格对话框基类

    特性：
    - 保留标准 Qt 窗口框架
    - 自动管理主题切换信号连接
    - 自动在对话框关闭时断开信号（防止内存泄漏）
    - 提供 _apply_theme() 钩子方法供子类实现
    """

    def __init__(self, parent=None):
        super().__init__(parent)
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

    def _on_theme_changed(self, mode: str):
        """主题改变回调"""
        self._apply_theme()

    def _apply_theme(self):
        """应用主题 - 子类实现

        子类应重写此方法来设置组件样式。
        推荐使用 DialogStyles 的 book_* 系列方法。
        """
        pass

    def closeEvent(self, event):
        """关闭时断开信号"""
        self._disconnect_theme_signal()
        super().closeEvent(event)
