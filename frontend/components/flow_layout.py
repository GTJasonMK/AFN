"""
流式布局组件

实现自动换行的标签/按钮布局，当一行放不下时自动换到下一行。
"""

from PyQt6.QtWidgets import QLayout, QWidgetItem, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QSize, QPoint


class FlowLayout(QLayout):
    """流式布局 - 自动换行的布局管理器

    类似于 CSS 的 flex-wrap: wrap，当一行放不下时自动换到下一行。

    用法：
        layout = FlowLayout(spacing=8)
        layout.addWidget(tag1)
        layout.addWidget(tag2)
        ...
    """

    def __init__(self, parent=None, spacing: int = 6):
        """初始化流式布局

        Args:
            parent: 父组件
            spacing: 组件间距（水平和垂直）
        """
        super().__init__(parent)
        self._items = []
        self._h_spacing = spacing
        self._v_spacing = spacing

    def addItem(self, item):
        """添加布局项"""
        self._items.append(item)

    def count(self):
        """返回项目数量"""
        return len(self._items)

    def itemAt(self, index):
        """获取指定索引的项目"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        """移除并返回指定索引的项目"""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        """返回扩展方向"""
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        """是否支持高度随宽度变化"""
        return True

    def heightForWidth(self, width):
        """根据宽度计算高度"""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        """设置布局几何区域"""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        """返回推荐尺寸"""
        return self.minimumSize()

    def minimumSize(self):
        """返回最小尺寸"""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                      margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only=False):
        """执行布局计算

        Args:
            rect: 布局区域
            test_only: 是否仅测试（不实际移动组件）

        Returns:
            计算出的总高度
        """
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(), margins.top(),
            -margins.right(), -margins.bottom()
        )

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        space_x = self._h_spacing
        space_y = self._v_spacing

        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue

            # 获取组件尺寸
            size_hint = item.sizeHint()
            item_width = size_hint.width()
            item_height = size_hint.height()

            # 检查是否需要换行
            next_x = x + item_width
            if next_x > effective_rect.right() and line_height > 0:
                # 换行
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item_width
                line_height = 0

            # 设置组件位置
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), size_hint))

            # 更新位置
            x = next_x + space_x
            line_height = max(line_height, item_height)

        # 返回总高度
        return y + line_height - rect.y() + margins.bottom()

    def clear(self):
        """清空所有项目"""
        while self._items:
            item = self._items.pop()
            if item.widget():
                item.widget().deleteLater()
