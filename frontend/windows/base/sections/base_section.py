"""
Section基类

提供Section组件的通用功能。
"""

import logging
from typing import Any, Dict, Optional

from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

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


__all__ = ["BaseSection"]
