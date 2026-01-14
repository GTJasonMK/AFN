"""
编程项目工作台侧边栏

包含项目信息卡片和目录树。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from api.manager import APIClientManager

from .components import DirectoryTree, ProjectInfoCard

logger = logging.getLogger(__name__)


class CodingSidebar(ThemeAwareFrame):
    """编程项目工作台侧边栏

    布局：
    - 项目信息卡片（顶部）
    - 目录树标题栏（刷新按钮）
    - 目录树（主体，可滚动）
    """

    fileSelected = pyqtSignal(dict)  # 文件选中信号
    refreshRequested = pyqtSignal()  # 刷新请求信号

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = APIClientManager.get_client()

        # 数据
        self._project_data: Dict[str, Any] = {}
        self._modules: List[Dict] = []
        self._tree_data: Dict[str, Any] = {}

        # Worker
        self._worker: Optional[AsyncAPIWorker] = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 项目信息卡片
        self.project_card = ProjectInfoCard(self)
        layout.addWidget(self.project_card)

        # 目录树标题栏
        tree_header = QWidget()
        tree_header_layout = QHBoxLayout(tree_header)
        tree_header_layout.setContentsMargins(0, 0, 0, 0)
        tree_header_layout.setSpacing(dp(8))

        tree_title = QLabel("目录结构")
        tree_title.setObjectName("tree_title")
        tree_header_layout.addWidget(tree_title)

        tree_header_layout.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._on_refresh)
        tree_header_layout.addWidget(refresh_btn)

        layout.addWidget(tree_header)

        # 目录树
        self.directory_tree = DirectoryTree(self.project_id, self)
        self.directory_tree.fileSelected.connect(self._on_file_selected)
        layout.addWidget(self.directory_tree, stretch=1)

    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f"""
            CodingSidebar {{
                background-color: {theme_manager.book_bg_secondary()};
                border-right: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
        """)

        tree_title = self.findChild(QLabel, "tree_title")
        if tree_title:
            tree_title.setStyleSheet(f"""
                font-size: {dp(13)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        refresh_btn = self.findChild(QPushButton, "refresh_btn")
        if refresh_btn:
            refresh_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px {dp(10)}px;
                    font-size: {dp(11)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY}10;
                }}
            """)

    def set_project_data(self, data: Dict[str, Any]):
        """设置项目数据"""
        self._project_data = data
        self.project_card.set_project_data(data)

        # 获取模块列表
        blueprint = data.get('blueprint', {})
        self._modules = blueprint.get('modules', [])

    def set_tree_data(self, tree_data: Dict[str, Any]):
        """设置目录树数据"""
        self._tree_data = tree_data

        # 更新统计
        total_dirs = tree_data.get('total_directories', 0)
        total_files = tree_data.get('total_files', 0)
        self.project_card.set_stats(len(self._modules), total_dirs, total_files)

        # 加载目录树（直接传递tree_data，显示真实目录结构）
        self.directory_tree.load_data(tree_data)

    def select_file(self, file_id: int):
        """选中指定文件"""
        self.directory_tree.select_file(file_id)

    def update_file_status(self, file_id: int, status: str):
        """更新文件状态"""
        self.directory_tree.update_file_status(file_id, status)

    def _on_file_selected(self, file_data: Dict):
        """文件选中处理"""
        self.fileSelected.emit(file_data)

    def _on_refresh(self):
        """刷新目录树"""
        self.directory_tree.refresh()
        self.refreshRequested.emit()

    def refresh(self):
        """刷新整个侧边栏"""
        self.directory_tree.refresh()

    def cleanup(self):
        """清理资源"""
        if self._worker:
            try:
                if self._worker.isRunning():
                    self._worker.cancel()
            except RuntimeError:
                pass
        self.directory_tree.cleanup()


__all__ = ["CodingSidebar"]
