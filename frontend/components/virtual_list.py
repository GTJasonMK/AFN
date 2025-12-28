"""
虚拟滚动列表组件

性能优化：只渲染可视区域内的列表项，支持大量数据的流畅滚动。

原理：
- 维护一个固定高度的滚动区域
- 只创建可见区域内的组件（+上下缓冲区）
- 滚动时复用组件，更新其数据

适用场景：
- 章节列表（>50章）
- 角色列表（>20个）
- 版本历史（>10个版本）

用法示例：
    from components.virtual_list import VirtualListWidget

    # 创建虚拟列表
    virtual_list = VirtualListWidget(
        item_height=48,
        buffer_size=5,  # 上下各缓冲5个item
        create_item_callback=lambda: ChapterCard({}, False),
        update_item_callback=lambda item, data, index: item.update_data(data)
    )

    # 设置数据
    virtual_list.set_data(chapter_list)

    # 监听选择事件
    virtual_list.item_clicked.connect(on_item_clicked)
"""

import logging
from typing import TypeVar, Generic, List, Callable, Optional, Any

from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QFrame, QVBoxLayout, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=QWidget)


class VirtualListWidget(QWidget):
    """虚拟滚动列表组件

    只渲染可视区域内的列表项，大幅提升大列表的渲染性能。

    特性：
    - 固定高度item：假设所有item高度相同（简化计算）
    - 组件复用：使用对象池模式复用item组件
    - 缓冲区：在可视区域上下各保留buffer_size个item
    - 延迟更新：滚动时使用节流避免过于频繁的更新
    """

    # 信号
    item_clicked = pyqtSignal(int, object)  # (index, data)
    scroll_to_end = pyqtSignal()  # 滚动到底部

    def __init__(
        self,
        item_height: int = 48,
        buffer_size: int = 5,
        create_item_callback: Callable[[], QWidget] = None,
        update_item_callback: Callable[[QWidget, Any, int], None] = None,
        parent=None
    ):
        """初始化虚拟列表

        Args:
            item_height: 每个item的固定高度（像素）
            buffer_size: 可视区域上下的缓冲item数量
            create_item_callback: 创建新item的回调函数
            update_item_callback: 更新item数据的回调函数 (item, data, index) -> None
        """
        super().__init__(parent)

        self._item_height = item_height
        self._buffer_size = buffer_size
        self._create_item = create_item_callback
        self._update_item = update_item_callback

        # 数据
        self._data: List[Any] = []

        # 组件池
        self._visible_items: List[QWidget] = []  # 当前可见的item
        self._item_pool: List[QWidget] = []  # 可复用的item池

        # 状态
        self._first_visible_index = 0
        self._last_visible_index = 0
        self._scroll_update_pending = False

        # UI组件
        self._scroll_area: QScrollArea = None
        self._content_widget: QWidget = None
        self._spacer_top: QWidget = None
        self._spacer_bottom: QWidget = None
        self._items_container: QWidget = None
        self._items_layout: QVBoxLayout = None

        self._setup_ui()

    def _setup_ui(self):
        """设置UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 内容容器
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 顶部占位符（用于模拟滚动高度）
        self._spacer_top = QWidget()
        self._spacer_top.setFixedHeight(0)
        content_layout.addWidget(self._spacer_top)

        # 实际item容器
        self._items_container = QWidget()
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(0)
        content_layout.addWidget(self._items_container)

        # 底部占位符
        self._spacer_bottom = QWidget()
        self._spacer_bottom.setFixedHeight(0)
        content_layout.addWidget(self._spacer_bottom)

        self._scroll_area.setWidget(self._content_widget)

        # 监听滚动事件
        self._scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        layout.addWidget(self._scroll_area)

    def set_data(self, data: List[Any]):
        """设置列表数据

        Args:
            data: 数据列表
        """
        self._data = data

        # 更新总高度
        total_height = len(data) * self._item_height

        # 重置滚动位置
        self._scroll_area.verticalScrollBar().setValue(0)

        # 更新可见区域
        self._update_visible_items()

    def get_data(self) -> List[Any]:
        """获取当前数据"""
        return self._data

    def scroll_to_index(self, index: int):
        """滚动到指定索引

        Args:
            index: 目标索引
        """
        if 0 <= index < len(self._data):
            scroll_pos = index * self._item_height
            self._scroll_area.verticalScrollBar().setValue(scroll_pos)

    def refresh(self):
        """刷新显示"""
        self._update_visible_items()

    def _on_scroll(self, value: int):
        """滚动事件处理（带节流）"""
        if self._scroll_update_pending:
            return

        self._scroll_update_pending = True
        # 使用短延迟节流，避免滚动时过于频繁更新
        QTimer.singleShot(16, self._do_scroll_update)  # ~60fps

    def _do_scroll_update(self):
        """执行滚动更新"""
        self._scroll_update_pending = False
        self._update_visible_items()

        # 检查是否滚动到底部
        scrollbar = self._scroll_area.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - self._item_height:
            self.scroll_to_end.emit()

    def _update_visible_items(self):
        """更新可见区域的item"""
        if not self._data:
            self._clear_visible_items()
            self._spacer_top.setFixedHeight(0)
            self._spacer_bottom.setFixedHeight(0)
            return

        # 计算可视区域
        viewport_height = self._scroll_area.viewport().height()
        scroll_top = self._scroll_area.verticalScrollBar().value()

        # 计算可见的item范围
        first_visible = max(0, scroll_top // self._item_height - self._buffer_size)
        items_in_viewport = (viewport_height // self._item_height) + 2 * self._buffer_size + 2
        last_visible = min(len(self._data) - 1, first_visible + items_in_viewport)

        # 如果范围没有变化，不需要更新
        if first_visible == self._first_visible_index and last_visible == self._last_visible_index:
            return

        self._first_visible_index = first_visible
        self._last_visible_index = last_visible

        # 回收不再可见的item
        items_to_recycle = []
        for item in self._visible_items:
            item_index = getattr(item, '_virtual_list_index', -1)
            if item_index < first_visible or item_index > last_visible:
                items_to_recycle.append(item)

        for item in items_to_recycle:
            self._visible_items.remove(item)
            self._recycle_item(item)

        # 创建新可见的item
        visible_indices = set(getattr(item, '_virtual_list_index', -1) for item in self._visible_items)

        for idx in range(first_visible, last_visible + 1):
            if idx not in visible_indices:
                item = self._acquire_item()
                item._virtual_list_index = idx

                # 更新item数据
                if self._update_item and idx < len(self._data):
                    self._update_item(item, self._data[idx], idx)

                self._visible_items.append(item)

        # 按索引排序
        self._visible_items.sort(key=lambda x: getattr(x, '_virtual_list_index', 0))

        # 重新添加到布局
        for i in reversed(range(self._items_layout.count())):
            self._items_layout.itemAt(i).widget().setParent(None)

        for item in self._visible_items:
            self._items_layout.addWidget(item)
            item.show()

        # 更新占位符高度
        top_height = first_visible * self._item_height
        bottom_height = (len(self._data) - last_visible - 1) * self._item_height

        self._spacer_top.setFixedHeight(max(0, top_height))
        self._spacer_bottom.setFixedHeight(max(0, bottom_height))

    def _acquire_item(self) -> QWidget:
        """从池中获取或创建item"""
        if self._item_pool:
            item = self._item_pool.pop()
            return item

        if self._create_item:
            item = self._create_item()
            # 连接点击事件
            if hasattr(item, 'clicked'):
                item.clicked.connect(lambda idx=None: self._on_item_clicked(item))
            elif hasattr(item, 'mousePressEvent'):
                # 包装点击事件
                original_press = item.mousePressEvent

                def wrapped_press(event, orig=original_press, it=item):
                    orig(event)
                    self._on_item_clicked(it)

                item.mousePressEvent = wrapped_press
            return item

        # 默认创建空widget
        return QWidget()

    def _recycle_item(self, item: QWidget):
        """回收item到池中"""
        item.hide()
        item.setParent(None)
        self._item_pool.append(item)

    def _clear_visible_items(self):
        """清空所有可见item"""
        for item in self._visible_items:
            self._recycle_item(item)
        self._visible_items.clear()

    def _on_item_clicked(self, item: QWidget):
        """item被点击"""
        index = getattr(item, '_virtual_list_index', -1)
        if 0 <= index < len(self._data):
            self.item_clicked.emit(index, self._data[index])

    def clear(self):
        """清空列表"""
        self._clear_visible_items()
        for item in self._item_pool:
            try:
                item.deleteLater()
            except RuntimeError:
                pass
        self._item_pool.clear()
        self._data.clear()

    @property
    def item_count(self) -> int:
        """获取数据项数量"""
        return len(self._data)

    @property
    def visible_count(self) -> int:
        """获取当前可见item数量"""
        return len(self._visible_items)


__all__ = ['VirtualListWidget']
