"""
Section基类

提供Section组件的通用功能。
"""

import logging
from typing import Any, Dict, Optional, Callable, List, Tuple

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QScrollArea, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class BaseSection(ThemeAwareFrame):
    """Section基类

    提供Section组件的通用功能：
    - 主题感知
    - 编辑信号
    - 数据更新

    子类需要实现：
    - _create_ui_structure(): 创建UI结构
    - _apply_theme(): 应用主题样式
    - updateData(data): 更新数据
    """

    # 编辑请求信号: (field_name, label, current_value)
    editRequested = pyqtSignal(str, str, object)

    # 刷新请求信号
    refreshRequested = pyqtSignal()

    def __init__(self, data: Any = None, editable: bool = True, parent=None):
        """初始化Section

        Args:
            data: 初始数据
            editable: 是否可编辑
            parent: 父组件
        """
        self._data = data
        self._editable = editable
        super().__init__(parent)

    @property
    def data(self) -> Any:
        """获取当前数据"""
        return self._data

    @property
    def editable(self) -> bool:
        """是否可编辑"""
        return self._editable

    def updateData(self, data: Any):
        """更新数据

        子类应重写此方法实现数据更新逻辑
        """
        self._data = data

    def requestEdit(self, field: str, label: str, value: Any):
        """请求编辑字段

        Args:
            field: 字段名
            label: 显示标签
            value: 当前值
        """
        if self._editable:
            self.editRequested.emit(field, label, value)

    def requestRefresh(self):
        """请求刷新"""
        self.refreshRequested.emit()

    def _apply_scroll_style(self, scroll: QScrollArea):
        """应用滚动区域样式"""
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

    def _create_scroll_container_layout(
        self,
        *,
        spacing: Optional[int] = None,
        right_margin: Optional[int] = None,
    ) -> QVBoxLayout:
        """创建标准滚动容器骨架，并返回内容区布局

        目的：避免各 Section 重复手写 QScrollArea + 内容容器 + 主布局的样板代码。

        Args:
            spacing: 内容区布局 spacing，默认 dp(16)
            right_margin: 内容区布局右侧 margin，默认 dp(8)
        """
        spacing_value = spacing if spacing is not None else dp(16)
        right_margin_value = right_margin if right_margin is not None else dp(8)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, right_margin_value, 0)
        layout.setSpacing(spacing_value)

        scroll.setWidget(content)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self._apply_scroll_style(scroll)
        return layout

    def _create_empty_label(
        self,
        text: str,
        padding: Optional[int] = None,
        font_size: Optional[int] = None,
    ) -> QLabel:
        """创建空状态标签"""
        label = QLabel(text)
        label.setObjectName("empty_label")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        padding_value = padding if padding is not None else dp(40)
        font_size_value = font_size if font_size is not None else dp(14)
        label.setStyleSheet(f"""
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {font_size_value}px;
                padding: {padding_value}px;
            }}
        """)
        return label

    def _create_empty_hint_widget(
        self,
        text: str,
        padding_h: Optional[int] = None,
        padding_v: Optional[int] = None,
        word_wrap: bool = True,
    ) -> QWidget:
        """创建提示型空状态组件"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        padding_h_value = padding_h if padding_h is not None else dp(20)
        padding_v_value = padding_v if padding_v is not None else dp(40)
        empty_layout.setContentsMargins(
            padding_h_value,
            padding_v_value,
            padding_h_value,
            padding_v_value,
        )
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_label = QLabel(text)
        empty_label.setObjectName("empty_label")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setWordWrap(word_wrap)
        empty_layout.addWidget(empty_label)

        return empty_widget

    def _build_basic_header_style(
        self,
        count_label_name: str,
        title_size: Optional[int] = None,
        count_size: Optional[int] = None,
        count_margin_left: Optional[int] = None,
    ) -> str:
        """构建基础标题样式"""
        title_size_value = title_size if title_size is not None else dp(16)
        count_size_value = count_size if count_size is not None else dp(13)
        margin_left_value = count_margin_left if count_margin_left is not None else dp(8)
        return f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {title_size_value}px;
                font-weight: 600;
            }}
            QLabel#{count_label_name} {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {count_size_value}px;
                margin-left: {margin_left_value}px;
            }}
        """

    def _build_section_header(
        self,
        title: str,
        *,
        title_object_name: str = "section_title",
        stat_items: Optional[List[Tuple[str, str]]] = None,
        left_widgets: Optional[List[QWidget]] = None,
        right_widgets: Optional[List[QWidget]] = None,
        spacing: Optional[int] = None,
    ) -> Tuple[QWidget, Dict[str, QLabel]]:
        """构建标题栏布局"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        if spacing is not None:
            header_layout.setSpacing(spacing)

        if left_widgets:
            for widget in left_widgets:
                header_layout.addWidget(widget)

        title_label = QLabel(title)
        title_label.setObjectName(title_object_name)
        header_layout.addWidget(title_label)

        label_map: Dict[str, QLabel] = {}
        if stat_items:
            for text, object_name in stat_items:
                label = QLabel(text)
                label.setObjectName(object_name)
                header_layout.addWidget(label)
                label_map[object_name] = label

        header_layout.addStretch()

        if right_widgets:
            for widget in right_widgets:
                header_layout.addWidget(widget)

        return header, label_map

    def _register_worker(self, worker):
        """注册异步 worker"""
        if not hasattr(self, "_workers"):
            self._workers = []
        self._workers.append(worker)
        return worker

    def _cleanup_workers(self):
        """清理已注册的异步 worker"""
        if not hasattr(self, "_workers"):
            return
        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()

    def _clear_cards(self, cards: list):
        """清理卡片列表"""
        for card in cards:
            try:
                card.deleteLater()
            except RuntimeError:
                pass
        cards.clear()

    def _render_card_list(
        self,
        items: Any,
        layout: Any,
        cards: list,
        card_factory: Callable[[Any], Any],
        empty_factory: Optional[Callable[[], Any]] = None,
    ):
        """渲染卡片列表（清理 -> 空态 -> 构建）"""
        self._clear_cards(cards)

        if not items:
            empty_widget = empty_factory() if empty_factory else self._create_empty_label("暂无数据")
            layout.addWidget(empty_widget)
            cards.append(empty_widget)
            return

        for item in items:
            card = card_factory(item)
            layout.addWidget(card)
            cards.append(card)

    def cleanup(self):
        """清理资源

        子类可重写此方法释放资源
        """
        pass

    def stopAllTasks(self):
        """停止所有异步任务

        子类可重写此方法停止异步任务
        """
        pass


def toggle_expand_state(expanded: bool, content: QWidget, icon: QLabel) -> bool:
    """切换展开状态"""
    next_state = not expanded
    content.setVisible(next_state)
    icon.setText("-" if next_state else "+")
    return next_state


__all__ = ["BaseSection", "toggle_expand_state"]
