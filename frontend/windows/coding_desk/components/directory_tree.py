"""
目录树组件

显示项目的完整目录结构，支持展开/折叠和文件选择。
目录结构与最终开发完成的项目目录完全一致。
"""

import logging
from typing import Dict, List, Optional, Set, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class TreeNodeItem(ThemeAwareFrame):
    """树节点项

    可以是目录或文件，支持展开/折叠和选中状态。
    """

    clicked = pyqtSignal(dict)  # 点击信号，传递节点数据
    toggleExpand = pyqtSignal(int)  # 展开/折叠信号，传递节点ID

    def __init__(
        self,
        data: Dict[str, Any],
        node_type: str = "file",  # "directory" or "file"
        depth: int = 0,
        is_expanded: bool = False,
        is_selected: bool = False,
        parent=None
    ):
        self.data = data
        self.node_type = node_type
        self.depth = depth
        self._is_expanded = is_expanded
        self._is_selected = is_selected

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedHeight(dp(28))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        # 根据深度设置左边距（模拟树形缩进）
        left_margin = dp(8) + self.depth * dp(16)
        layout.setContentsMargins(left_margin, dp(2), dp(8), dp(2))
        layout.setSpacing(dp(4))

        # 展开/折叠图标（仅目录有）
        if self.node_type == "directory":
            self.expand_icon = QLabel("v" if self._is_expanded else ">")
            self.expand_icon.setObjectName("expand_icon")
            self.expand_icon.setFixedWidth(dp(12))
            self.expand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.expand_icon)
        else:
            # 文件用空白占位
            spacer = QLabel("")
            spacer.setFixedWidth(dp(12))
            layout.addWidget(spacer)

        # 节点图标
        icon_text = self._get_icon_text()
        self.icon_label = QLabel(icon_text)
        self.icon_label.setObjectName(f"icon_{self.node_type}")
        self.icon_label.setFixedWidth(dp(16))
        layout.addWidget(self.icon_label)

        # 名称
        name = self._get_display_name()
        self.name_label = QLabel(name)
        self.name_label.setObjectName("name_label")
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.name_label)

        # 状态标签（仅文件有）
        if self.node_type == "file":
            status = self.data.get('status', 'not_generated')
            status_text = self._get_status_text(status)
            if status_text:
                self.status_label = QLabel(status_text)
                self.status_label.setObjectName(f"status_{status}")
                layout.addWidget(self.status_label)

    def _get_icon_text(self) -> str:
        """获取节点图标"""
        if self.node_type == "directory":
            return "[D]" if self._is_expanded else "[D]"
        else:
            # 文件根据状态显示不同图标
            status = self.data.get('status', 'not_generated')
            if status == 'generated':
                return "[+]"
            elif status == 'generating':
                return "[~]"
            elif status == 'failed':
                return "[!]"
            else:
                return "[ ]"

    def _get_display_name(self) -> str:
        """获取显示名称"""
        if self.node_type == "directory":
            return self.data.get('name', '')
        else:
            return self.data.get('filename', '')

    def _get_status_text(self, status: str) -> str:
        """获取状态显示文本"""
        mapping = {
            'not_generated': '',
            'pending': '',
            'generating': '...',
            'generated': '',
            'failed': 'x',
        }
        return mapping.get(status, '')

    def _apply_theme(self):
        """应用主题"""
        bg_color = theme_manager.PRIMARY + "15" if self._is_selected else "transparent"
        hover_color = theme_manager.PRIMARY + "08"

        self.setStyleSheet(f"""
            TreeNodeItem {{
                background-color: {bg_color};
                border-radius: {dp(3)}px;
            }}
            TreeNodeItem:hover {{
                background-color: {hover_color};
            }}
        """)

        # 展开图标
        if hasattr(self, 'expand_icon'):
            self.expand_icon.setStyleSheet(f"""
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(10)}px;
                font-family: Consolas, monospace;
            """)

        # 节点图标颜色
        if self.node_type == "directory":
            icon_color = theme_manager.WARNING
        else:
            status = self.data.get('status', 'not_generated')
            if status == 'generated':
                icon_color = theme_manager.SUCCESS
            elif status == 'failed':
                icon_color = theme_manager.ERROR
            elif status == 'generating':
                icon_color = theme_manager.WARNING
            else:
                icon_color = theme_manager.TEXT_TERTIARY

        if hasattr(self, 'icon_label'):
            self.icon_label.setStyleSheet(f"""
                color: {icon_color};
                font-size: {dp(10)}px;
                font-family: Consolas, monospace;
            """)

        # 名称
        if hasattr(self, 'name_label'):
            name_color = theme_manager.TEXT_PRIMARY if self.node_type == "directory" else theme_manager.TEXT_SECONDARY
            self.name_label.setStyleSheet(f"""
                color: {name_color};
                font-size: {dp(12)}px;
            """)

        # 状态标签
        if hasattr(self, 'status_label'):
            status = self.data.get('status', 'not_generated')
            status_colors = {
                'generating': theme_manager.WARNING,
                'failed': theme_manager.ERROR,
            }
            status_color = status_colors.get(status, theme_manager.TEXT_TERTIARY)
            self.status_label.setStyleSheet(f"""
                color: {status_color};
                font-size: {dp(10)}px;
            """)

    def setSelected(self, selected: bool):
        """设置选中状态"""
        self._is_selected = selected
        self._apply_theme()

    def setExpanded(self, expanded: bool):
        """设置展开状态"""
        self._is_expanded = expanded
        if hasattr(self, 'expand_icon'):
            self.expand_icon.setText("v" if expanded else ">")

    def update_status(self, status: str):
        """更新文件状态"""
        self.data['status'] = status
        # 更新图标
        if hasattr(self, 'icon_label'):
            self.icon_label.setText(self._get_icon_text())
        # 更新状态标签
        if hasattr(self, 'status_label'):
            self.status_label.setText(self._get_status_text(status))
        self._apply_theme()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.node_type == "directory":
                node_id = self.data.get('id')
                self.toggleExpand.emit(node_id)
            else:
                self.clicked.emit(self.data)
        super().mousePressEvent(event)


class DirectoryTree(ThemeAwareWidget):
    """项目目录树组件

    显示真实的项目目录结构，与最终开发完成的项目目录一致。
    支持：
    - 目录展开/折叠
    - 文件状态显示
    - 文件选择
    """

    fileSelected = pyqtSignal(dict)  # 文件选中信号
    loadingStarted = pyqtSignal()
    loadingFinished = pyqtSignal()

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = APIClientManager.get_client()

        # 数据
        self._tree_data: Dict[str, Any] = {}

        # 状态
        self._expanded_dirs: Set[int] = set()  # 展开的目录ID
        self._selected_file_id: Optional[int] = None

        # UI组件引用
        self._tree_items: List[TreeNodeItem] = []
        self._file_items_map: Dict[int, TreeNodeItem] = {}  # file_id -> TreeNodeItem
        self._worker: Optional[AsyncAPIWorker] = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 树容器
        self.tree_container = QWidget()
        self.tree_layout = QVBoxLayout(self.tree_container)
        self.tree_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        self.tree_layout.setSpacing(dp(1))
        self.tree_layout.addStretch()

        self.scroll_area.setWidget(self.tree_container)
        layout.addWidget(self.scroll_area)

    def _apply_theme(self):
        """应用主题"""
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)
        self.tree_container.setStyleSheet("background-color: transparent;")

    def load_data(self, tree_data: Dict[str, Any]):
        """加载目录树数据

        Args:
            tree_data: 目录树数据，包含 root_nodes
        """
        self._tree_data = tree_data

        # 默认展开第一层目录
        root_nodes = tree_data.get('root_nodes', [])
        for node in root_nodes:
            self._expanded_dirs.add(node.get('id'))

        self._rebuild_tree()

    def refresh(self):
        """刷新目录树"""
        self.loadingStarted.emit()

        self._cleanup_worker()
        self._worker = AsyncAPIWorker(
            self.api_client.get_directory_tree,
            self.project_id
        )
        self._worker.success.connect(self._on_tree_loaded)
        self._worker.error.connect(self._on_tree_error)
        self._worker.start()

    def _on_tree_loaded(self, data: Dict):
        """目录树加载完成"""
        self._tree_data = data
        self._rebuild_tree()
        self.loadingFinished.emit()

    def _on_tree_error(self, error: str):
        """目录树加载失败"""
        logger.warning(f"加载目录树失败: {error}")
        self.loadingFinished.emit()

    def _rebuild_tree(self):
        """重建树形结构"""
        # 清除现有节点
        for item in self._tree_items:
            try:
                item.deleteLater()
            except RuntimeError:
                pass
        self._tree_items.clear()
        self._file_items_map.clear()

        # 移除所有组件（除了最后的stretch）
        while self.tree_layout.count() > 1:
            item = self.tree_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 递归构建树
        root_nodes = self._tree_data.get('root_nodes', [])
        self._add_nodes_recursive(root_nodes, 0)

    def _add_nodes_recursive(self, nodes: List[Dict], depth: int):
        """递归添加节点"""
        for node in nodes:
            node_id = node.get('id')
            is_expanded = node_id in self._expanded_dirs

            # 目录节点
            dir_item = TreeNodeItem(
                data=node,
                node_type="directory",
                depth=depth,
                is_expanded=is_expanded
            )
            dir_item.toggleExpand.connect(self._toggle_directory)
            self.tree_layout.insertWidget(self.tree_layout.count() - 1, dir_item)
            self._tree_items.append(dir_item)

            if is_expanded:
                # 添加子目录
                children = node.get('children', [])
                self._add_nodes_recursive(children, depth + 1)

                # 添加文件
                files = node.get('files', [])
                for file_data in files:
                    is_selected = file_data.get('id') == self._selected_file_id
                    file_item = TreeNodeItem(
                        data=file_data,
                        node_type="file",
                        depth=depth + 1,
                        is_selected=is_selected
                    )
                    file_item.clicked.connect(self._on_file_clicked)
                    self.tree_layout.insertWidget(self.tree_layout.count() - 1, file_item)
                    self._tree_items.append(file_item)
                    self._file_items_map[file_data.get('id')] = file_item

    def _toggle_directory(self, dir_id: int):
        """切换目录展开状态"""
        if dir_id in self._expanded_dirs:
            self._expanded_dirs.remove(dir_id)
        else:
            self._expanded_dirs.add(dir_id)
        self._rebuild_tree()

    def _on_file_clicked(self, file_data: Dict):
        """文件点击处理"""
        self._selected_file_id = file_data.get('id')

        # 更新选中状态
        for item in self._tree_items:
            if item.node_type == "file":
                is_selected = item.data.get('id') == self._selected_file_id
                item.setSelected(is_selected)

        self.fileSelected.emit(file_data)

    def select_file(self, file_id: int):
        """选中指定文件"""
        self._selected_file_id = file_id

        # 更新选中状态
        for item in self._tree_items:
            if item.node_type == "file":
                is_selected = item.data.get('id') == file_id
                item.setSelected(is_selected)

    def update_file_status(self, file_id: int, status: str):
        """更新文件状态"""
        if file_id in self._file_items_map:
            self._file_items_map[file_id].update_status(status)

    def _cleanup_worker(self):
        """清理异步Worker"""
        if self._worker is None:
            return
        try:
            if self._worker.isRunning():
                self._worker.cancel()
                self._worker.quit()
                self._worker.wait(3000)
        except RuntimeError:
            pass
        finally:
            self._worker = None

    def cleanup(self):
        """清理资源"""
        self._cleanup_worker()
        for item in self._tree_items:
            try:
                item.deleteLater()
            except RuntimeError:
                pass
        self._tree_items.clear()
        self._file_items_map.clear()


__all__ = ["DirectoryTree", "TreeNodeItem"]
