"""
工作台页面基类

提供工作台的通用结构：Header + Sidebar + Workspace
可被 WritingDesk 等继承使用。
"""

import logging
from typing import Dict, List, Optional, Any

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt

from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.worker_manager import WorkerManager

logger = logging.getLogger(__name__)


class BaseWorkspacePage(BasePage):
    """工作台页面基类

    提供通用的页面结构：
    +------------------------------------------------------------------+
    | Header: 项目信息 | 导航按钮 | 操作按钮                             |
    +------------------------------------------------------------------+
    | Sidebar        |                  Workspace                      |
    | (章节/模块列表)  |                  (内容编辑区域)                  |
    |                |                                                  |
    +------------------------------------------------------------------+

    子类需要实现：
    - create_header() -> 创建Header组件
    - create_sidebar() -> 创建Sidebar组件
    - create_workspace() -> 创建Workspace组件
    - get_blueprint() -> 获取蓝图数据
    - load_project_data() -> 加载项目数据
    """

    def __init__(self, project_id: str, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        # 项目数据
        self.project: Optional[Dict[str, Any]] = None

        # 当前选中的章节/模块编号
        self.selected_item_number: Optional[int] = None

        # 异步任务管理
        self.worker_manager = WorkerManager(self)

        # UI组件引用（子类在create_*方法中设置）
        self.header: Optional[QWidget] = None
        self.sidebar: Optional[QWidget] = None
        self.workspace: Optional[QWidget] = None
        self.content_widget: Optional[QWidget] = None

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_base_ui_structure()
        self._apply_theme()

    def _create_base_ui_structure(self):
        """创建基础UI结构"""
        from PyQt6.QtWidgets import QApplication

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = self.create_header()
        if self.header:
            main_layout.addWidget(self.header)

        # 主内容区
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        content_layout.setSpacing(dp(12))

        # Sidebar
        self.sidebar = self.create_sidebar()
        if self.sidebar:
            content_layout.addWidget(self.sidebar)

        # Workspace
        self.workspace = self.create_workspace()
        if self.workspace:
            self.workspace.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            content_layout.addWidget(self.workspace, stretch=1)

        main_layout.addWidget(self.content_widget, stretch=1)

        # 处理事件循环
        QApplication.processEvents()

        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """连接信号

        子类应重写此方法连接自己的信号
        """
        pass

    def _apply_theme(self):
        """应用主题样式"""
        from themes.modern_effects import ModernEffects

        bg_color = theme_manager.book_bg_primary()
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = theme_manager.get_component_opacity("content")

        if transparency_enabled:
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            # 透明容器
            for container in [self.header, self.content_widget, self.sidebar, self.workspace]:
                if container:
                    container.setAutoFillBackground(False)

            if self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            for container in [self.header, self.content_widget, self.sidebar, self.workspace]:
                if container:
                    container.setAutoFillBackground(True)

            if self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")

    # ==================== 生命周期 ====================

    def onHide(self):
        """页面隐藏时停止运行中的任务"""
        self._cleanup_workers(full_cleanup=False)

    def _cleanup_workers(self, full_cleanup: bool = True):
        """清理所有异步任务

        Args:
            full_cleanup: True表示完全清理，False表示只停止当前任务
        """
        if hasattr(self, 'worker_manager') and self.worker_manager:
            if full_cleanup:
                self.worker_manager.cleanup_all()
            else:
                self.worker_manager.stop_all()

    def closeEvent(self, event):
        """窗口关闭时清理"""
        self._cleanup_workers(full_cleanup=True)
        super().closeEvent(event)

    # ==================== 子类需要实现的方法 ====================

    def create_header(self) -> Optional[QWidget]:
        """创建Header组件

        Returns:
            Header组件
        """
        raise NotImplementedError("子类必须实现 create_header()")

    def create_sidebar(self) -> Optional[QWidget]:
        """创建Sidebar组件

        Returns:
            Sidebar组件
        """
        raise NotImplementedError("子类必须实现 create_sidebar()")

    def create_workspace(self) -> Optional[QWidget]:
        """创建Workspace组件

        Returns:
            Workspace组件
        """
        raise NotImplementedError("子类必须实现 create_workspace()")

    def get_blueprint(self) -> Dict[str, Any]:
        """获取蓝图数据

        Returns:
            蓝图字典
        """
        raise NotImplementedError("子类必须实现 get_blueprint()")

    def load_project_data(self):
        """加载项目数据

        子类应实现异步加载逻辑
        """
        raise NotImplementedError("子类必须实现 load_project_data()")


__all__ = ["BaseWorkspacePage"]
