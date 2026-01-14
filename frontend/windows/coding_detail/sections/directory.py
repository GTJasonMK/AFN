"""
目录结构Section - 展示和管理项目目录结构

显示实际的项目文件树结构（类似IDE的文件浏览器），支持Agent规划和文件管理。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QTextEdit, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class DirectorySection(BaseSection):
    """目录结构Section

    展示项目的实际文件树结构（类似IDE文件浏览器）。
    """

    # 额外信号（refreshRequested继承自BaseSection）
    loadingRequested = pyqtSignal(str)
    loadingFinished = pyqtSignal()
    fileClicked = pyqtSignal(int)  # file_id - 用于跳转到文件Prompt生成页面

    def __init__(
        self,
        modules: List[Dict] = None,
        directory_tree: Dict[str, Any] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.modules = modules or []
        self.directory_tree = directory_tree or {}
        self._workers = []
        self.api_client = APIClientManager.get_client()
        self._data_loaded = False
        self._has_paused_state = False  # 是否有暂停的Agent状态
        self._paused_state_info = {}  # 暂停状态的详细信息
        self._detailed_mode = False  # Agent输出详细模式
        self._tree_refresh_pending = False  # 是否有待处理的树刷新
        self._tree_refresh_timer = None  # 防抖定时器

        super().__init__([], editable, parent)
        self.setupUI()

        # 初始化后自动加载目录树数据和Agent状态
        if self.project_id:
            if not self.directory_tree.get('root_nodes'):
                self._load_directory_tree()
            self._check_agent_state()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("目录结构")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        # 统计信息
        total_dirs = self.directory_tree.get('total_directories', 0)
        total_files = self.directory_tree.get('total_files', 0)
        stats_text = f"{total_dirs} 目录 / {total_files} 文件"
        stats_label = QLabel(stats_text)
        stats_label.setObjectName("stats_label")
        header_layout.addWidget(stats_label)
        self.stats_label = stats_label

        header_layout.addStretch()

        # 继续规划按钮（默认隐藏）
        self.agent_continue_btn = QPushButton("继续规划")
        self.agent_continue_btn.setObjectName("agent_continue_btn")
        self.agent_continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_continue_btn.clicked.connect(self._on_agent_continue)
        self.agent_continue_btn.setVisible(False)
        header_layout.addWidget(self.agent_continue_btn)

        # 放弃暂停状态按钮（默认隐藏）
        self.agent_discard_btn = QPushButton("重新开始")
        self.agent_discard_btn.setObjectName("agent_discard_btn")
        self.agent_discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_discard_btn.clicked.connect(self._on_agent_discard)
        self.agent_discard_btn.setVisible(False)
        header_layout.addWidget(self.agent_discard_btn)

        # Agent规划按钮
        self.agent_plan_btn = QPushButton("Agent规划整个项目")
        self.agent_plan_btn.setObjectName("agent_plan_btn")
        self.agent_plan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_plan_btn.clicked.connect(self._on_agent_plan)
        header_layout.addWidget(self.agent_plan_btn)

        # 仅优化目录按钮（当有目录结构时显示）
        self.agent_optimize_btn = QPushButton("仅优化目录")
        self.agent_optimize_btn.setObjectName("agent_optimize_btn")
        self.agent_optimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_optimize_btn.clicked.connect(self._on_agent_optimize)
        self.agent_optimize_btn.setVisible(False)  # 默认隐藏，有目录时显示
        header_layout.addWidget(self.agent_optimize_btn)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        # Agent思考过程面板（默认隐藏）
        self.agent_panel = QFrame()
        self.agent_panel.setObjectName("agent_panel")
        self.agent_panel.setVisible(False)
        agent_panel_layout = QVBoxLayout(self.agent_panel)
        agent_panel_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        agent_panel_layout.setSpacing(dp(8))

        # Agent面板标题栏
        agent_header = QHBoxLayout()
        agent_title = QLabel("Agent思考过程")
        agent_title.setObjectName("agent_title")
        agent_header.addWidget(agent_title)

        self.agent_status_label = QLabel("准备中...")
        self.agent_status_label.setObjectName("agent_status")
        agent_header.addWidget(self.agent_status_label)

        agent_header.addStretch()

        # 详细模式复选框
        self.detailed_mode_checkbox = QCheckBox("详细模式")
        self.detailed_mode_checkbox.setObjectName("detailed_mode_checkbox")
        self.detailed_mode_checkbox.setChecked(self._detailed_mode)
        self.detailed_mode_checkbox.toggled.connect(self._on_detailed_mode_toggled)
        agent_header.addWidget(self.detailed_mode_checkbox)

        self.agent_stop_btn = QPushButton("停止")
        self.agent_stop_btn.setObjectName("agent_stop_btn")
        self.agent_stop_btn.clicked.connect(self._on_agent_stop)
        agent_header.addWidget(self.agent_stop_btn)

        self.agent_close_btn = QPushButton("关闭")
        self.agent_close_btn.setObjectName("agent_close_btn")
        self.agent_close_btn.clicked.connect(self._on_agent_panel_close)
        agent_header.addWidget(self.agent_close_btn)

        agent_panel_layout.addLayout(agent_header)

        # Agent输出文本框
        self.agent_output = QTextEdit()
        self.agent_output.setObjectName("agent_output")
        self.agent_output.setReadOnly(True)
        self.agent_output.setMinimumHeight(dp(200))
        self.agent_output.setMaximumHeight(dp(300))
        agent_panel_layout.addWidget(self.agent_output)

        layout.addWidget(self.agent_panel)

        # 目录树容器
        tree_container = QWidget()
        tree_container.setObjectName("tree_container")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        # 创建目录树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setObjectName("directory_tree")
        self.tree_widget.setHeaderLabels(["名称", "类型", "状态"])
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setExpandsOnDoubleClick(True)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        # 设置列宽
        header_view = self.tree_widget.header()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree_widget.setColumnWidth(1, dp(80))
        self.tree_widget.setColumnWidth(2, dp(80))

        tree_layout.addWidget(self.tree_widget)
        layout.addWidget(tree_container, 1)  # 让树占用剩余空间

        # 填充目录树
        self._populate_tree()

        self._apply_styles()

    def _populate_tree(self):
        """填充目录树"""
        self.tree_widget.clear()

        root_nodes = self.directory_tree.get('root_nodes', [])

        if not root_nodes:
            # 空状态
            empty_item = QTreeWidgetItem(self.tree_widget)
            empty_item.setText(0, "暂无目录结构")
            empty_item.setText(1, "")
            empty_item.setText(2, "点击「Agent规划整个项目」生成")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # 递归添加节点
        for node in root_nodes:
            self._add_tree_node(self.tree_widget.invisibleRootItem(), node)

        # 展开第一层
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                item.setExpanded(True)

    def _add_tree_node(self, parent_item, node_data: Dict):
        """递归添加树节点"""
        item = QTreeWidgetItem(parent_item)

        # 设置节点数据
        item.setData(0, Qt.ItemDataRole.UserRole, node_data)

        node_type = node_data.get('node_type', 'directory')
        name = node_data.get('name', '')

        # 根据类型设置显示
        if node_type == 'root':
            item.setText(0, f"[R] {name}/")
            item.setText(1, "项目根目录")
            item.setText(2, "")
        elif node_type in ('directory', 'module', 'package', 'config'):
            item.setText(0, f"[D] {name}/")
            item.setText(1, self._get_type_display(node_type))
            item.setText(2, "")
        else:
            item.setText(0, f"[D] {name}/")
            item.setText(1, node_type)
            item.setText(2, "")

        # 添加该目录下的文件
        files = node_data.get('files', [])
        for file_data in files:
            self._add_file_node(item, file_data)

        # 递归添加子目录
        children = node_data.get('children', [])
        for child in children:
            self._add_tree_node(item, child)

    def _add_file_node(self, parent_item, file_data: Dict):
        """添加文件节点"""
        item = QTreeWidgetItem(parent_item)
        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'file', 'data': file_data})

        filename = file_data.get('filename', '')
        file_type = file_data.get('file_type', 'source')
        status = file_data.get('status', 'pending')

        item.setText(0, f"    {filename}")
        item.setText(1, self._get_file_type_display(file_type))
        item.setText(2, self._get_status_display(status))

    def _get_type_display(self, node_type: str) -> str:
        """获取目录类型显示文本"""
        mapping = {
            'root': '项目根目录',
            'directory': '目录',
            'module': '模块',
            'package': '包',
            'config': '配置',
        }
        return mapping.get(node_type, node_type)

    def _get_file_type_display(self, file_type: str) -> str:
        """获取文件类型显示文本"""
        mapping = {
            'source': '源代码',
            'config': '配置',
            'test': '测试',
            'doc': '文档',
            'resource': '资源',
        }
        return mapping.get(file_type, file_type)

    def _get_status_display(self, status: str) -> str:
        """获取状态显示文本"""
        mapping = {
            'pending': '待生成',
            'generating': '生成中',
            'generated': '已生成',
            'reviewed': '已审查',
            'error': '失败',
        }
        return mapping.get(status, status)

    def _on_context_menu(self, position):
        """右键菜单"""
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        node_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_data:
            return

        menu = QMenu(self)

        # 判断是文件还是目录
        if isinstance(node_data, dict) and node_data.get('type') == 'file':
            # 文件节点
            file_data = node_data.get('data', {})
            file_id = file_data.get('id')
            status = file_data.get('status', 'pending')

            if status == 'pending':
                action = QAction("生成Prompt", self)
                action.triggered.connect(lambda: self._on_generate_file(file_id))
                menu.addAction(action)
            else:
                action = QAction("编辑Prompt", self)
                action.triggered.connect(lambda: self._on_edit_file(file_id))
                menu.addAction(action)
        else:
            # 目录节点
            dir_id = node_data.get('id')
            module_number = node_data.get('module_number')

            if module_number:
                action = QAction("重新生成该模块目录", self)
                action.triggered.connect(lambda: self._on_regenerate_module_directory(module_number))
                menu.addAction(action)

        if menu.actions():
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击项目"""
        node_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_data:
            return

        # 如果是文件节点，跳转到编辑
        if isinstance(node_data, dict) and node_data.get('type') == 'file':
            file_data = node_data.get('data', {})
            file_id = file_data.get('id')
            if file_id:
                self.fileClicked.emit(file_id)

    def _on_generate_file(self, file_id: int):
        """生成文件Prompt"""
        logger.info(f"生成文件Prompt: file_id={file_id}")
        self.fileClicked.emit(file_id)

    def _on_edit_file(self, file_id: int):
        """编辑文件Prompt"""
        logger.info(f"编辑文件Prompt: file_id={file_id}")
        self.fileClicked.emit(file_id)

    def _on_regenerate_module_directory(self, module_number: int):
        """重新生成模块目录"""
        from components.dialogs import get_regenerate_preference

        module_name = next(
            (m.get('name', f'模块{module_number}')
             for m in self.modules if m.get('module_number') == module_number),
            f'模块{module_number}'
        )

        preference, ok = get_regenerate_preference(
            self,
            title=f"重新生成目录结构 - {module_name}",
            message=f"模块 [{module_name}] 的目录结构将被重新生成。",
            placeholder="例如：增加测试目录、调整目录层级、添加配置文件等"
        )
        if not ok:
            return

        self.loadingRequested.emit(f"正在为 {module_name} 生成目录结构...")

        worker = AsyncAPIWorker(
            self.api_client.generate_directory_structure,
            self.project_id,
            module_number,
            preference=preference,
            clear_existing=True
        )
        worker.success.connect(self._on_directory_generated)
        worker.error.connect(self._on_generate_error)
        self._workers.append(worker)
        worker.start()

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(18)}px;
                font-weight: 600;
            }}
            QLabel#stats_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(12)}px;
            }}
            QPushButton#agent_plan_btn {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QPushButton#agent_plan_btn:hover {{
                background-color: {theme_manager.SUCCESS}DD;
            }}
            QPushButton#agent_plan_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QPushButton#agent_optimize_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QPushButton#agent_optimize_btn:hover {{
                background-color: {theme_manager.PRIMARY}DD;
            }}
            QPushButton#agent_optimize_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QPushButton#agent_continue_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QPushButton#agent_continue_btn:hover {{
                background-color: {theme_manager.PRIMARY}DD;
            }}
            QPushButton#agent_discard_btn {{
                background-color: transparent;
                color: {theme_manager.WARNING};
                border: 1px solid {theme_manager.WARNING};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#agent_discard_btn:hover {{
                background-color: {theme_manager.WARNING}10;
            }}
            QPushButton#refresh_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#refresh_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QFrame#agent_panel {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.PRIMARY}40;
                border-radius: {dp(8)}px;
            }}
            QLabel#agent_title {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#agent_status {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                margin-left: {dp(8)}px;
            }}
            QPushButton#agent_stop_btn {{
                background-color: {theme_manager.WARNING};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#agent_stop_btn:hover {{
                background-color: {theme_manager.WARNING}DD;
            }}
            QCheckBox#detailed_mode_checkbox {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(11)}px;
                margin-right: {dp(8)}px;
            }}
            QCheckBox#detailed_mode_checkbox::indicator {{
                width: {dp(14)}px;
                height: {dp(14)}px;
            }}
            QCheckBox#detailed_mode_checkbox::indicator:unchecked {{
                border: 1px solid {theme_manager.TEXT_TERTIARY};
                border-radius: {dp(3)}px;
                background-color: transparent;
            }}
            QCheckBox#detailed_mode_checkbox::indicator:checked {{
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(3)}px;
                background-color: {theme_manager.PRIMARY};
            }}
            QPushButton#agent_close_btn {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.TEXT_TERTIARY};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#agent_close_btn:hover {{
                background-color: {theme_manager.TEXT_TERTIARY}20;
            }}
            QTextEdit#agent_output {{
                background-color: {theme_manager.BG_PRIMARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: {dp(11)}px;
                padding: {dp(8)}px;
            }}
            QTreeWidget#directory_tree {{
                background-color: {theme_manager.book_bg_secondary()};
                color: {theme_manager.book_text_primary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: {dp(12)}px;
                padding: {dp(8)}px;
            }}
            QTreeWidget#directory_tree::item {{
                color: {theme_manager.book_text_primary()};
                padding: {dp(4)}px 0;
                border-radius: {dp(4)}px;
            }}
            QTreeWidget#directory_tree::item:hover {{
                background-color: {theme_manager.PRIMARY}15;
            }}
            QTreeWidget#directory_tree::item:selected {{
                background-color: {theme_manager.PRIMARY}25;
                color: {theme_manager.book_text_primary()};
            }}
            QTreeWidget#directory_tree::branch {{
                background-color: transparent;
            }}
            QHeaderView::section {{
                background-color: {theme_manager.book_bg_primary()};
                color: {theme_manager.book_text_secondary()};
                border: none;
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
                padding: {dp(8)}px;
                font-size: {dp(11)}px;
                font-weight: 500;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_styles()

    def _on_refresh(self):
        """刷新"""
        self._load_directory_tree()

    def _load_directory_tree_debounced(self, delay_ms: int = 500):
        """
        防抖加载目录树

        避免Agent快速创建文件时频繁刷新UI
        """
        from PyQt6.QtCore import QTimer

        # 如果已有定时器，取消它
        if self._tree_refresh_timer:
            self._tree_refresh_timer.stop()

        # 标记有待处理的刷新
        self._tree_refresh_pending = True

        # 创建新的定时器
        self._tree_refresh_timer = QTimer(self)
        self._tree_refresh_timer.setSingleShot(True)
        self._tree_refresh_timer.timeout.connect(self._do_debounced_refresh)
        self._tree_refresh_timer.start(delay_ms)

    def _do_debounced_refresh(self):
        """执行防抖刷新"""
        self._tree_refresh_pending = False
        self._tree_refresh_timer = None
        self._load_directory_tree()

    def _load_directory_tree(self):
        """加载目录树数据"""
        if not self.project_id:
            return

        logger.info(f"加载目录树: project_id={self.project_id}")

        worker = AsyncAPIWorker(
            self.api_client.get_directory_tree,
            self.project_id
        )
        worker.success.connect(self._on_directory_tree_loaded)
        worker.error.connect(self._on_directory_tree_error)
        self._workers.append(worker)
        worker.start()

    def _on_directory_tree_loaded(self, result):
        """目录树加载成功"""
        logger.info(f"目录树加载成功: {result.get('total_directories', 0)} 目录, {result.get('total_files', 0)} 文件")
        self.directory_tree = result
        self._data_loaded = True

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            total_dirs = result.get('total_directories', 0)
            total_files = result.get('total_files', 0)
            stats_text = f"{total_dirs} 目录 / {total_files} 文件"
            self.stats_label.setText(stats_text)

        # 根据是否有目录结构来显示/隐藏优化按钮
        has_directories = result.get('total_directories', 0) > 0
        if hasattr(self, 'agent_optimize_btn'):
            self.agent_optimize_btn.setVisible(has_directories and not self._has_paused_state)

        # 重新填充目录树
        self._populate_tree()

    def _on_directory_tree_error(self, error_msg: str):
        """目录树加载失败"""
        logger.warning(f"目录树加载失败: {error_msg}")
        # 不显示错误，可能只是还没有生成目录结构

    def _on_directory_generated(self, result):
        """目录生成完成"""
        self.loadingFinished.emit()
        dirs_created = result.get('directories_created', 0)
        files_created = result.get('files_created', 0)
        logger.info(f"目录生成完成: {dirs_created} 目录, {files_created} 文件")
        MessageService.show_success(
            self,
            f"成功生成 {dirs_created} 个目录和 {files_created} 个文件"
        )
        self.refreshRequested.emit()

    def _on_generate_error(self, error_msg: str):
        """生成失败"""
        self.loadingFinished.emit()
        logger.error(f"目录生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败：{error_msg}")

    def updateData(
        self,
        modules: List[Dict] = None,
        directory_tree: Dict[str, Any] = None
    ):
        """更新数据"""
        if modules is not None:
            self.modules = modules
        if directory_tree is not None:
            self.directory_tree = directory_tree

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            total_dirs = self.directory_tree.get('total_directories', 0)
            total_files = self.directory_tree.get('total_files', 0)
            stats_text = f"{total_dirs} 目录 / {total_files} 文件"
            self.stats_label.setText(stats_text)

        self._populate_tree()

    # ==================== Agent规划相关方法 ====================

    def _on_agent_plan(self):
        """开始Agent规划"""
        if not self.project_id:
            MessageService.show_warning(self, "请先保存项目")
            return

        # 检查是否有模块
        if not self.modules:
            MessageService.show_warning(
                self,
                "请先在「架构设计」Tab中生成系统和模块划分"
            )
            return

        # 检查是否已有目录结构
        total_dirs = self.directory_tree.get('total_directories', 0)
        if total_dirs > 0:
            from PyQt6.QtWidgets import QDialog
            from components.dialogs import ConfirmDialog
            dialog = ConfirmDialog(
                self,
                title="重新规划目录结构",
                message="项目已有目录结构，重新规划将清除现有的所有目录和文件。\n\n确定要继续吗？",
                confirm_text="确定",
                cancel_text="取消"
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

        logger.info(f"开始Agent规划: project_id={self.project_id}")

        # 显示Agent面板
        self.agent_panel.setVisible(True)
        self.agent_output.clear()
        self.agent_status_label.setText("正在连接...")
        self.agent_plan_btn.setEnabled(False)
        self.agent_stop_btn.setEnabled(True)

        # 启动SSE连接，设置clear_existing=True清除旧目录
        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"clear_existing": True})
        # 连接所有必要的信号
        # progress_received: SSEWorker内置的progress事件处理
        self._sse_worker.progress_received.connect(self._on_progress_received)
        # complete: SSEWorker内置的complete事件处理
        self._sse_worker.complete.connect(self._on_complete_received)
        # event_received: 自定义事件（structure, state_saved等）
        self._sse_worker.event_received.connect(self._on_agent_event)
        self._sse_worker.error.connect(self._on_agent_error)
        self._sse_worker.finished.connect(self._on_agent_finished)
        self._sse_worker.start()

    def _on_agent_optimize(self):
        """仅优化现有目录结构"""
        if not self.project_id:
            MessageService.show_warning(self, "请先保存项目")
            return

        # 检查是否有模块
        if not self.modules:
            MessageService.show_warning(
                self,
                "请先在「架构设计」Tab中生成系统和模块划分"
            )
            return

        # 检查是否有目录结构
        total_dirs = self.directory_tree.get('total_directories', 0)
        if total_dirs == 0:
            MessageService.show_warning(
                self,
                "项目没有目录结构，请先使用「Agent规划整个项目」生成"
            )
            return

        logger.info(f"开始优化目录结构: project_id={self.project_id}")

        # 显示Agent面板
        self.agent_panel.setVisible(True)
        self.agent_output.clear()
        self.agent_status_label.setText("正在连接...")
        self.agent_plan_btn.setEnabled(False)
        self.agent_optimize_btn.setEnabled(False)
        self.agent_stop_btn.setEnabled(True)

        self._append_agent_output("[系统] 从现有目录结构开始优化...\n", "info")

        # 启动SSE连接，使用plan-v2端点但不清除现有结构
        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"clear_existing": False})
        # 连接所有必要的信号
        self._sse_worker.progress_received.connect(self._on_progress_received)
        self._sse_worker.complete.connect(self._on_complete_received)
        self._sse_worker.event_received.connect(self._on_agent_event)
        self._sse_worker.error.connect(self._on_agent_error)
        self._sse_worker.finished.connect(self._on_agent_finished)
        self._sse_worker.start()

    def _on_progress_received(self, data: dict):
        """处理SSEWorker的progress_received信号"""
        self._on_agent_event("progress", data)

    def _on_complete_received(self, data: dict):
        """处理SSEWorker的complete信号"""
        self._on_agent_event("complete", data)

    def _on_agent_event(self, event_type: str, data: dict):
        """处理Agent事件（兼容新V2 API和旧API事件）"""
        # ============ 新V2 API ReAct事件 ============

        # 阶段变化事件
        if event_type == "phase":
            phase = data.get("phase", "")
            message = data.get("message", "")
            phase_names = {
                "gathering": "信息收集",
                "analyzing": "结构分析",
                "optimizing": "优化中",
                "finalizing": "最终验证",
            }
            phase_name = phase_names.get(phase, phase)
            self.agent_status_label.setText(phase_name)
            self._append_agent_output(f"\n{'='*40}\n", "phase")
            self._append_agent_output(f"[阶段] {message}\n", "phase")

        # Agent思考过程事件
        elif event_type == "thought":
            iteration = data.get("iteration", 0)
            thought = data.get("thought", "")
            thought_type = data.get("type", "reasoning")

            if thought_type == "reasoning":
                # 推理思考
                if self._detailed_mode:
                    display_thought = thought
                else:
                    display_thought = thought[:300] + "..." if len(thought) > 300 else thought
                self._append_agent_output(f"[思考#{iteration}] {display_thought}\n", "thinking")
            elif thought_type == "conclusion":
                # 结论
                self._append_agent_output(f"[结论] {thought}\n", "success")

        # Agent反思事件
        elif event_type == "reflection":
            iteration = data.get("iteration", 0)
            message = data.get("message", "")
            self._append_agent_output(f"\n[反思#{iteration}] {message}\n", "warning")

        # 信息收集事件
        elif event_type == "info_gathered":
            tool = data.get("tool", "")
            reason = data.get("reason", "")
            success = data.get("success", False)
            round_num = data.get("round", 1)

            status = "成功" if success else "失败"
            tool_display = tool.replace("get_", "").replace("_", " ").title()
            self._append_agent_output(f"[收集#{round_num}] {tool_display}: {status}\n", "info")
            if reason and self._detailed_mode:
                self._append_agent_output(f"  原因: {reason}\n", "thinking")

        # 信息收集完成
        elif event_type == "gathering_complete":
            items = data.get("items_collected", 0)
            types = data.get("collected_types", [])
            self._append_agent_output(f"[收集完成] 共收集 {items} 项信息\n", "success")
            if types and self._detailed_mode:
                type_list = ", ".join([t.replace("get_", "") for t in types])
                self._append_agent_output(f"  类型: {type_list}\n", "info")

        # 分析结果事件
        elif event_type == "analysis":
            coverage = data.get("coverage_rate", 0) * 100
            issues = data.get("total_issues", 0)
            missing = data.get("missing_modules", [])
            self._append_agent_output(f"[分析结果] 覆盖率: {coverage:.1f}%, 问题数: {issues}\n", "info")
            if missing:
                self._append_agent_output(f"[分析结果] 未覆盖模块: {missing[:10]}\n", "warning")

        # 工具执行事件（优化阶段）
        elif event_type == "action":
            iteration = data.get("iteration", 0)
            tool = data.get("tool", "")
            reasoning = data.get("reasoning", "")

            # 简化工具名显示
            tool_display = tool.replace("_", " ").title()
            self._append_agent_output(f"[动作#{iteration}] {tool_display}\n", "action")
            if reasoning and self._detailed_mode:
                self._append_agent_output(f"  理由: {reasoning}\n", "info")

        # ============ V2 API基础事件 ============
        elif event_type == "progress":
            stage = data.get("stage", "")
            message = data.get("message", "")

            stage_names = {
                "phase1": "第一阶段：生成目录结构",
                "phase1_complete": "第一阶段完成",
                "phase2": "第二阶段：优化结构",
                "phase2_complete": "第二阶段完成",
                "saving": "保存到数据库",
                "resuming": "正在恢复",
            }
            stage_name = stage_names.get(stage, stage)
            self.agent_status_label.setText(stage_name)
            self._append_agent_output(f"[进度] {message}\n", "phase")

            # 显示覆盖率信息
            if "coverage_rate" in data:
                coverage = data.get("coverage_rate", 0) * 100
                self._append_agent_output(f"[统计] 模块覆盖率: {coverage:.1f}%\n", "info")
            if "total_directories" in data:
                dirs = data.get("total_directories", 0)
                files = data.get("total_files", 0)
                self._append_agent_output(f"[统计] 目录: {dirs}, 文件: {files}\n", "info")

        elif event_type == "state_saved":
            # 状态已保存事件
            phase = data.get("phase", "")
            message = data.get("message", "状态已保存")
            self._append_agent_output(f"[保存] {message}\n", "success")

        elif event_type == "structure":
            dirs = len(data.get("directories", []))
            files = len(data.get("files", []))
            shared = data.get("shared_modules", [])
            self._append_agent_output(f"\n[结构] 生成了 {dirs} 个目录和 {files} 个文件\n", "success")
            if shared:
                self._append_agent_output(f"[结构] 共享模块: {', '.join(shared)}\n", "info")
            # 立即刷新目录树显示
            self._load_directory_tree()

        elif event_type == "structure_update":
            # 实时目录结构更新（Agent执行操作工具后触发）
            stats = data.get("stats", {})
            dirs_count = stats.get("total_directories", 0)
            files_count = stats.get("total_files", 0)
            covered = stats.get("covered_modules", 0)
            total = stats.get("total_modules", 0)

            # 更新统计显示
            if hasattr(self, 'stats_label') and self.stats_label:
                self.stats_label.setText(f"{dirs_count} 目录 / {files_count} 文件")

            # 显示进度信息（非详细模式下简化显示）
            if self._detailed_mode:
                coverage_pct = (covered / total * 100) if total > 0 else 0
                self._append_agent_output(
                    f"[更新] 目录: {dirs_count}, 文件: {files_count}, 覆盖率: {coverage_pct:.0f}%\n",
                    "info"
                )

            # 使用防抖刷新目录树，避免频繁API调用
            self._load_directory_tree_debounced()

        elif event_type == "complete":
            self.agent_status_label.setText("规划完成")
            dirs = data.get("directories_created", 0)
            files = data.get("files_created", 0)
            coverage = data.get("coverage_rate", 0) * 100
            message = data.get("message", "")
            self._append_agent_output(f"\n[完成] {message}\n", "success")
            self._append_agent_output(f"[统计] 保存了 {dirs} 个目录和 {files} 个文件，覆盖率 {coverage:.1f}%\n", "success")
            self.agent_stop_btn.setEnabled(False)
            # 立即刷新目录树显示
            self._load_directory_tree()

        elif event_type == "error":
            error_msg = data.get("message", "未知错误")
            stage = data.get("stage", "")
            self.agent_status_label.setText("发生错误")
            self._append_agent_output(f"\n[错误] {error_msg}\n", "error")
            if stage:
                self._append_agent_output(f"[错误] 发生在: {stage}\n", "error")
            self.agent_stop_btn.setEnabled(False)

        # ============ 旧API事件（保留兼容） ============
        elif event_type == "workflow_start":
            self.agent_status_label.setText("开始规划...")
            self._append_agent_output("[系统] 开始规划目录结构\n", "info")

        elif event_type == "phase_start":
            phase = data.get("phase", "")
            phase_names = {
                "analyzing": "分析阶段",
                "designing": "设计阶段",
                "planning": "规划阶段",
                "validating": "验证阶段",
                "outputting": "输出阶段",
            }
            phase_name = phase_names.get(phase, phase)
            self.agent_status_label.setText(f"{phase_name}...")
            self._append_agent_output(f"\n[阶段] 进入{phase_name}\n", "phase")

        elif event_type == "phase_complete":
            phase = data.get("phase", "")
            self._append_agent_output(f"[阶段] {phase}完成\n", "phase")

        elif event_type == "thinking":
            thinking = data.get("content", "")
            if thinking:
                if self._detailed_mode:
                    display_thinking = thinking
                else:
                    display_thinking = thinking[:200] + "..." if len(thinking) > 200 else thinking
                self._append_agent_output(f"[思考] {display_thinking}\n", "thinking")

        elif event_type == "action":
            tool_name = data.get("tool_name", "")
            self._append_agent_output(f"[行动] 调用工具: {tool_name}\n", "action")

        elif event_type == "observation":
            if self._detailed_mode:
                result = data.get("full_result", "") or data.get("result", "")
            else:
                result = data.get("result", "")
            if result:
                self._append_agent_output(f"[观察] {result}\n", "observation")

        elif event_type == "directory_planned":
            dir_path = data.get("path", "")
            self._append_agent_output(f"[目录] 规划目录: {dir_path}\n", "directory")

        elif event_type == "file_planned":
            file_path = data.get("path", "")
            self._append_agent_output(f"[文件] 规划文件: {file_path}\n", "file")

        elif event_type == "structure_ready":
            self._append_agent_output("\n[系统] 目录结构规划完成\n", "success")

        elif event_type == "save_complete":
            dirs = data.get("directories_created", 0)
            files = data.get("files_created", 0)
            self._append_agent_output(
                f"\n[保存] 已保存 {dirs} 个目录和 {files} 个文件到数据库\n",
                "success"
            )

        elif event_type == "workflow_complete":
            self.agent_status_label.setText("规划完成")
            self._append_agent_output("\n[系统] 规划完成!\n", "success")
            self.agent_stop_btn.setEnabled(False)

        elif event_type == "workflow_error":
            error_msg = data.get("message", "未知错误")
            self.agent_status_label.setText("发生错误")
            self._append_agent_output(f"\n[错误] {error_msg}\n", "error")
            self.agent_stop_btn.setEnabled(False)

    def _on_detailed_mode_toggled(self, checked: bool):
        """详细模式切换"""
        self._detailed_mode = checked
        mode_text = "详细模式已开启，将显示完整的思考和观察内容" if checked else "详细模式已关闭，内容将被截断显示"
        self._append_agent_output(f"[系统] {mode_text}\n", "info")

    def _append_agent_output(self, text: str, style: str = "normal"):
        """追加Agent输出，带样式"""
        cursor = self.agent_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        color_map = {
            "info": theme_manager.TEXT_SECONDARY,
            "phase": theme_manager.PRIMARY,
            "thinking": theme_manager.TEXT_TERTIARY,
            "action": theme_manager.WARNING,
            "observation": theme_manager.TEXT_SECONDARY,
            "directory": theme_manager.SUCCESS,
            "file": theme_manager.SUCCESS,
            "success": theme_manager.SUCCESS,
            "warning": theme_manager.WARNING,
            "error": theme_manager.ERROR,
            "normal": theme_manager.TEXT_PRIMARY,
        }
        color = color_map.get(style, theme_manager.TEXT_PRIMARY)

        # 将换行符转换为HTML换行标签
        html_text = text.replace('\n', '<br>')
        cursor.insertHtml(f'<span style="color: {color};">{html_text}</span>')

        self.agent_output.verticalScrollBar().setValue(
            self.agent_output.verticalScrollBar().maximum()
        )

    def _on_agent_error(self, error_msg: str):
        """Agent错误处理"""
        logger.error(f"Agent SSE错误: {error_msg}")
        self.agent_status_label.setText("连接错误")
        self._append_agent_output(f"\n[错误] 连接失败: {error_msg}\n", "error")
        self.agent_plan_btn.setEnabled(True)
        self.agent_optimize_btn.setEnabled(True)
        self.agent_stop_btn.setEnabled(False)

    def _on_agent_finished(self):
        """Agent完成处理"""
        logger.info("Agent规划流程结束")
        self.agent_plan_btn.setEnabled(True)
        self.agent_optimize_btn.setEnabled(True)
        self.agent_continue_btn.setEnabled(True)
        self.agent_discard_btn.setEnabled(True)
        self.agent_stop_btn.setEnabled(False)
        # 刷新目录树和Agent状态
        self._load_directory_tree()
        self._check_agent_state()

    def _on_agent_stop(self):
        """停止Agent"""
        if not self.project_id:
            return

        # 先调用API保存状态为暂停
        self._append_agent_output("\n[系统] 正在保存进度...\n", "info")
        self.agent_stop_btn.setEnabled(False)

        worker = AsyncAPIWorker(
            self.api_client.pause_directory_agent,
            self.project_id,
            "用户手动停止"
        )
        worker.success.connect(self._on_agent_pause_success)
        worker.error.connect(self._on_agent_pause_error)
        self._workers.append(worker)
        worker.start()

    def _on_agent_pause_success(self, result):
        """暂停成功，断开SSE连接"""
        if hasattr(self, '_sse_worker') and self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None

        self.agent_status_label.setText("已暂停")

        total_dirs = result.get('total_directories', 0)
        total_files = result.get('total_files', 0)
        phase = result.get('current_phase', '')

        self._append_agent_output(
            f"\n[系统] 进度已保存 ({total_dirs}目录/{total_files}文件)\n",
            "success"
        )
        self._append_agent_output("[系统] 可以稍后点击「继续规划」继续\n", "info")

        self.agent_plan_btn.setEnabled(True)
        self.agent_continue_btn.setEnabled(True)
        self.agent_discard_btn.setEnabled(True)
        self.agent_stop_btn.setEnabled(False)

        # 更新状态信息并刷新按钮
        self._has_paused_state = True
        self._paused_state_info = {
            'has_paused_state': True,
            'current_phase': phase,
            'total_directories': total_dirs,
            'total_files': total_files,
        }
        self._update_buttons_for_state()

    def _on_agent_pause_error(self, error_msg: str):
        """暂停失败，仍然断开连接"""
        logger.warning(f"暂停Agent失败: {error_msg}")

        # 即使保存失败，也要断开连接
        if hasattr(self, '_sse_worker') and self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None

        self.agent_status_label.setText("已停止(未保存)")
        self._append_agent_output(f"\n[警告] 保存进度失败: {error_msg}\n", "warning")
        self._append_agent_output("[系统] 连接已断开，进度可能丢失\n", "warning")

        self.agent_plan_btn.setEnabled(True)
        self.agent_stop_btn.setEnabled(False)

        # 延迟检查状态
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._check_agent_state)

    def _on_agent_panel_close(self):
        """关闭Agent面板"""
        # 如果Agent正在运行，先暂停保存状态
        if hasattr(self, '_sse_worker') and self._sse_worker:
            # 异步保存状态后再关闭
            worker = AsyncAPIWorker(
                self.api_client.pause_directory_agent,
                self.project_id,
                "用户关闭面板"
            )
            worker.success.connect(self._on_panel_close_pause_success)
            worker.error.connect(self._on_panel_close_pause_error)
            self._workers.append(worker)
            worker.start()
        else:
            # 没有运行中的Agent，直接关闭
            self.agent_panel.setVisible(False)
            self._check_agent_state()

    def _on_panel_close_pause_success(self, result):
        """面板关闭暂停成功"""
        if hasattr(self, '_sse_worker') and self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None
        self.agent_panel.setVisible(False)
        self.agent_plan_btn.setEnabled(True)
        self._check_agent_state()

    def _on_panel_close_pause_error(self, error_msg: str):
        """面板关闭暂停失败"""
        logger.warning(f"关闭面板时暂停Agent失败: {error_msg}")
        if hasattr(self, '_sse_worker') and self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None
        self.agent_panel.setVisible(False)
        self.agent_plan_btn.setEnabled(True)
        self._check_agent_state()

    # ==================== Agent状态检查和继续规划 ====================

    def _check_agent_state(self):
        """检查是否有暂停的Agent状态"""
        if not self.project_id:
            self._has_paused_state = False
            self._paused_state_info = {}
            self._update_buttons_for_state()
            return

        worker = AsyncAPIWorker(
            self.api_client.get_directory_agent_state,
            self.project_id
        )
        worker.success.connect(self._on_agent_state_loaded)
        worker.error.connect(lambda e: logger.warning(f"检查Agent状态失败: {e}"))
        self._workers.append(worker)
        worker.start()

    def _on_agent_state_loaded(self, result):
        """Agent状态加载完成"""
        self._has_paused_state = result.get('has_paused_state', False)
        self._paused_state_info = result

        if self._has_paused_state:
            logger.info(
                "检测到暂停的Agent状态: phase=%s, dirs=%d, files=%d",
                result.get('current_phase', ''),
                result.get('total_directories', 0),
                result.get('total_files', 0)
            )

        self._update_buttons_for_state()

    def _update_buttons_for_state(self):
        """根据Agent状态更新按钮显示"""
        has_directories = self.directory_tree.get('total_directories', 0) > 0

        if self._has_paused_state:
            # 有暂停状态：显示继续和放弃按钮
            self.agent_continue_btn.setVisible(True)
            self.agent_discard_btn.setVisible(True)
            self.agent_plan_btn.setVisible(False)
            self.agent_optimize_btn.setVisible(False)  # 暂停状态时隐藏优化按钮

            # 更新继续按钮文本，显示进度信息
            dirs = self._paused_state_info.get('total_directories', 0)
            files = self._paused_state_info.get('total_files', 0)
            phase = self._paused_state_info.get('current_phase', '')
            if dirs > 0 or files > 0:
                self.agent_continue_btn.setText(f"继续规划 ({dirs}目录/{files}文件)")
            else:
                self.agent_continue_btn.setText("继续规划")
        else:
            # 无暂停状态：显示规划按钮
            self.agent_continue_btn.setVisible(False)
            self.agent_discard_btn.setVisible(False)
            self.agent_plan_btn.setVisible(True)
            # 只有在有目录结构时才显示优化按钮
            self.agent_optimize_btn.setVisible(has_directories)

    def _on_agent_continue(self):
        """继续规划"""
        if not self.project_id:
            return

        logger.info(f"继续Agent规划: project_id={self.project_id}")

        # 显示Agent面板
        self.agent_panel.setVisible(True)
        self.agent_output.clear()
        self.agent_status_label.setText("正在恢复...")
        self.agent_continue_btn.setEnabled(False)
        self.agent_discard_btn.setEnabled(False)
        self.agent_stop_btn.setEnabled(True)

        self._append_agent_output("[系统] 正在从上次中断处继续...\n", "info")

        # 启动SSE连接（带resume参数）
        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"resume": True})
        # 连接所有必要的信号（与_on_agent_plan保持一致）
        self._sse_worker.progress_received.connect(self._on_progress_received)
        self._sse_worker.complete.connect(self._on_complete_received)
        self._sse_worker.event_received.connect(self._on_agent_event)
        self._sse_worker.error.connect(self._on_agent_error)
        self._sse_worker.finished.connect(self._on_agent_finished)
        self._sse_worker.start()

    def _on_agent_discard(self):
        """放弃暂停状态，重新开始"""
        from PyQt6.QtWidgets import QDialog
        from components.dialogs import ConfirmDialog

        dialog = ConfirmDialog(
            self,
            title="放弃已有进度",
            message="确定要放弃已有的规划进度吗？\n\n这将删除保存的状态，您需要重新开始规划。",
            confirm_text="确定放弃",
            cancel_text="取消"
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        logger.info(f"放弃Agent状态: project_id={self.project_id}")

        worker = AsyncAPIWorker(
            self.api_client.clear_directory_agent_state,
            self.project_id
        )
        worker.success.connect(self._on_agent_state_cleared)
        worker.error.connect(lambda e: MessageService.show_error(self, f"清除状态失败: {e}"))
        self._workers.append(worker)
        worker.start()

    def _on_agent_state_cleared(self, result):
        """Agent状态已清除"""
        logger.info("Agent状态已清除")
        self._has_paused_state = False
        self._paused_state_info = {}
        self._update_buttons_for_state()
        MessageService.show_success(self, "已清除保存的进度，可以重新开始规划")

    def cleanup(self):
        """清理资源"""
        # 停止防抖定时器
        if self._tree_refresh_timer:
            self._tree_refresh_timer.stop()
            self._tree_refresh_timer = None

        if hasattr(self, '_sse_worker') and self._sse_worker:
            try:
                self._sse_worker.stop()
            except Exception:
                pass
            self._sse_worker = None

        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()


__all__ = ["DirectorySection"]
