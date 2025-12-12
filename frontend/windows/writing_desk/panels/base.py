"""
面板构建器基类 - 统一Builder模式接口

提供所有面板构建器的抽象基类，确保接口一致性。

设计原则：
- 统一接口：所有Builder实现相同的方法签名
- 依赖注入：通过构造函数注入样式器
- 单一职责：每个Builder只负责创建特定面板

主题刷新策略：
当前WDWorkspace使用重建策略（rebuild）处理主题切换，
即在_apply_theme中调用displayChapter重建整个面板。
这种方式简单可靠，避免了复杂的增量样式更新逻辑。

如果需要增量更新，子类可重写refresh_theme()方法，
并使用_register_panel()跟踪创建的面板引用。
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QTextEdit
from themes.book_theme_styler import BookThemeStyler
from utils.dpi_utils import dp, sp


class BasePanelBuilder(ABC):
    """面板构建器抽象基类

    所有面板构建器都应继承此类并实现其抽象方法。

    用法示例：
        class MyPanelBuilder(BasePanelBuilder):
            def create_panel(self, data: dict) -> QWidget:
                # 实现面板创建逻辑
                ...

            def refresh_theme(self):
                # 实现主题刷新逻辑（如果需要）
                ...
    """

    def __init__(self, styler: Optional[BookThemeStyler] = None):
        """初始化构建器

        Args:
            styler: 样式器实例（可选）。如果不提供，将创建新实例。
        """
        self._styler = styler or BookThemeStyler()
        # 存储已创建的面板引用（用于主题刷新）
        self._created_panels: list = []

    @property
    def styler(self) -> BookThemeStyler:
        """获取样式器"""
        return self._styler

    @abstractmethod
    def create_panel(self, data: dict) -> QWidget:
        """创建面板

        Args:
            data: 面板所需的数据字典

        Returns:
            创建的面板Widget
        """
        pass

    def refresh_theme(self):
        """刷新主题

        在主题切换时调用此方法。默认实现会刷新样式器。
        子类可以重写此方法以实现自定义的主题刷新逻辑。
        """
        self._styler.refresh()

    def _create_empty_state(self, title: str, description: str,
                            icon_char: str = '?') -> QWidget:
        """创建空状态Widget

        提供统一的空状态显示样式。

        Args:
            title: 标题
            description: 描述文本
            icon_char: 图标字符

        Returns:
            空状态Widget
        """
        from PyQt6.QtWidgets import QVBoxLayout
        from PyQt6.QtCore import Qt
        from components.empty_state import EmptyStateWithIllustration
        from utils.dpi_utils import dp

        empty_widget = QWidget()
        empty_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {self._styler.text_primary};
            }}
        """)
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(dp(32), dp(32), dp(32), dp(32))
        empty_layout.setSpacing(dp(24))

        empty_state = EmptyStateWithIllustration(
            illustration_char=icon_char,
            title=title,
            description=description,
            parent=empty_widget
        )
        empty_layout.addWidget(empty_state)

        return empty_widget

    def _register_panel(self, panel: QWidget):
        """注册创建的面板（用于后续主题刷新）

        Args:
            panel: 创建的面板Widget
        """
        self._created_panels.append(panel)

    def clear_panels(self):
        """清理已创建的面板引用"""
        self._created_panels.clear()

    # ==================== 样式辅助方法 ====================
    # 以下方法提供常用的样式字符串，使用BookThemeStyler确保一致性
    # 方法名与 BookThemeStyler 保持一致，提供便捷访问

    def _card_style(self, object_name: str, with_hover: bool = False) -> str:
        """获取卡片样式

        Args:
            object_name: QFrame的objectName，用于CSS选择器
            with_hover: 是否包含hover效果

        Returns:
            卡片的StyleSheet字符串
        """
        return self._styler.card_style(object_name, with_hover)

    def _info_card_style(self, object_name: str, card_type: str = "info") -> str:
        """获取信息卡片样式（带左边框高亮）

        Args:
            object_name: QFrame的objectName
            card_type: 卡片类型 (info/success/warning/error)

        Returns:
            信息卡片的StyleSheet字符串
        """
        return self._styler.info_card_style(object_name, card_type)

    def _text_edit_style(self, object_name: str) -> str:
        """获取多行文本编辑器样式

        Args:
            object_name: QTextEdit的objectName

        Returns:
            QTextEdit的StyleSheet字符串
        """
        return self._styler.text_edit_style(object_name)

    def _title_style(self, object_name: str, size: int = 16) -> str:
        """获取标题样式

        Args:
            object_name: QLabel的objectName
            size: 字体大小

        Returns:
            标题QLabel的StyleSheet字符串
        """
        return self._styler.title_style(object_name, size)

    def _subtitle_style(self, object_name: str, size: int = 14) -> str:
        """获取副标题样式

        Args:
            object_name: QLabel的objectName
            size: 字体大小

        Returns:
            副标题QLabel的StyleSheet字符串
        """
        return self._styler.subtitle_style(object_name, size)

    def _label_style(self, object_name: str, size: int = 12) -> str:
        """获取标签样式（小字体次要文本）

        Args:
            object_name: QLabel的objectName
            size: 字体大小

        Returns:
            标签QLabel的StyleSheet字符串
        """
        return self._styler.label_style(object_name, size)

    def _button_primary_style(self, object_name: str) -> str:
        """获取主要按钮样式

        Args:
            object_name: QPushButton的objectName

        Returns:
            主要按钮的StyleSheet字符串
        """
        return self._styler.button_primary_style(object_name)

    def _button_secondary_style(self, object_name: str) -> str:
        """获取次要按钮样式

        Args:
            object_name: QPushButton的objectName

        Returns:
            次要按钮的StyleSheet字符串
        """
        return self._styler.button_secondary_style(object_name)

    def _scrollbar_style(self) -> str:
        """获取滚动条样式

        Returns:
            滚动条的StyleSheet字符串
        """
        return self._styler.scrollbar_style()
