"""
编程项目Prompt生成工作台主类

提供文件Prompt的生成、编辑和版本管理功能。
采用 Mixin 架构，参考 WritingDesk 的布局模式。
"""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSplitter
from PyQt6.QtCore import Qt

from pages.base_page import BasePage
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.worker_manager import WorkerManager
from utils.message_service import MessageService
from utils.dpi_utils import dp
from themes.theme_manager import theme_manager

from .header import CodingDeskHeader
from .sidebar import CodingSidebar
from .workspace import CodingWorkspace
from .assistant_panel import CodingAssistantPanel
from .mixins import FileGenerationMixin, ContentManagementMixin

logger = logging.getLogger(__name__)


class CodingDesk(FileGenerationMixin, ContentManagementMixin, BasePage):
    """编程项目Prompt生成工作台

    布局（参考WritingDesk）：
    +------------------------------------------------------------------+
    | Header (56dp): 返回 | 项目标题 | 文件路径 | RAG切换              |
    +------------------------------------------------------------------+
    | Sidebar (280dp)    | MainSplitter                                |
    | - ProjectInfoCard  | - Workspace (7)     | AssistantPanel (3)   |
    | - DirectoryTree    |   (Prompt编辑器)     |   (RAG检索)          |
    +------------------------------------------------------------------+
    """

    def __init__(self, project_id: str, file_id: int = None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.initial_file_id = file_id

        self.api_client = APIClientManager.get_client()
        self.worker_manager = WorkerManager(self)

        # 项目数据
        self._project_data: Optional[Dict[str, Any]] = None
        self._tree_data: Optional[Dict[str, Any]] = None

        # 初始化Mixin
        self._init_generation_mixin()
        self._init_content_mixin()

        # UI组件
        self.header: Optional[CodingDeskHeader] = None
        self.sidebar: Optional[CodingSidebar] = None
        self.workspace: Optional[CodingWorkspace] = None
        self.assistant_panel: Optional[CodingAssistantPanel] = None

        self._assistant_visible = True

        self.setupUI()
        self._load_project()

    def setupUI(self):
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = CodingDeskHeader(self)
        self.header.goBackClicked.connect(self._go_back)
        self.header.goToDetailClicked.connect(self._go_to_detail)
        self.header.toggleAssistantClicked.connect(self._toggle_assistant)
        main_layout.addWidget(self.header)

        # 主内容区
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        content_layout.setSpacing(dp(12))

        # Sidebar
        self.sidebar = CodingSidebar(self.project_id, self)
        self.sidebar.setFixedWidth(dp(280))
        self.sidebar.fileSelected.connect(self._on_file_selected)
        self.sidebar.refreshRequested.connect(self._refresh_directory_tree)
        content_layout.addWidget(self.sidebar)

        # MainSplitter (Workspace + AssistantPanel)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(dp(4))

        # Workspace
        self.workspace = CodingWorkspace(self)
        self.workspace.generateRequested.connect(self.start_file_generation)
        self.workspace.saveRequested.connect(self.save_file_content)
        self.workspace.generateReviewRequested.connect(self.start_review_generation)
        self.main_splitter.addWidget(self.workspace)

        # AssistantPanel
        self.assistant_panel = CodingAssistantPanel(self.project_id, self)
        self.assistant_panel.setMinimumWidth(dp(280))
        self.assistant_panel.setMaximumWidth(dp(500))
        self.main_splitter.addWidget(self.assistant_panel)

        # 设置Splitter比例 (7:3)
        self.main_splitter.setSizes([dp(700), dp(300)])
        self.main_splitter.setStretchFactor(0, 7)
        self.main_splitter.setStretchFactor(1, 3)

        content_layout.addWidget(self.main_splitter, stretch=1)
        main_layout.addWidget(content, stretch=1)

    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f"""
            CodingDesk {{
                background-color: {theme_manager.book_bg_primary()};
            }}
            QSplitter::handle {{
                background-color: {theme_manager.BORDER_DEFAULT};
            }}
            QSplitter::handle:hover {{
                background-color: {theme_manager.PRIMARY};
            }}
            {theme_manager.scrollbar()}
        """)

    # ========== 数据加载 ==========

    def _load_project(self):
        """加载项目信息"""
        worker = AsyncAPIWorker(self.api_client.get_coding_project, self.project_id)
        worker.success.connect(self._on_project_loaded)
        worker.error.connect(self._on_load_error)
        self.worker_manager.start(worker, 'load_project')

    def _on_project_loaded(self, data: Dict[str, Any]):
        """项目加载完成"""
        self._project_data = data

        # 更新Header标题
        title = data.get('title', '未命名项目')
        self.header.set_project_title(title)

        # 更新Sidebar项目信息
        self.sidebar.set_project_data(data)

        # 加载目录树
        self._load_directory_tree()

    def _load_directory_tree(self):
        """加载目录树"""
        worker = AsyncAPIWorker(self.api_client.get_directory_tree, self.project_id)
        worker.success.connect(self._on_tree_loaded)
        worker.error.connect(self._on_load_error)
        self.worker_manager.start(worker, 'load_tree')

    def _on_tree_loaded(self, data: Dict[str, Any]):
        """目录树加载完成"""
        self._tree_data = data

        # 更新Sidebar目录树
        self.sidebar.set_tree_data(data)

        # 如果有初始文件ID，选中它
        if self.initial_file_id:
            self.sidebar.select_file(self.initial_file_id)
            self._load_initial_file()

    def _load_initial_file(self):
        """加载初始文件"""
        worker = AsyncAPIWorker(
            self.api_client.get_source_file,
            self.project_id,
            self.initial_file_id
        )
        worker.success.connect(self._on_initial_file_loaded)
        worker.error.connect(self._on_load_error)
        self.worker_manager.start(worker, 'load_initial_file')

    def _on_initial_file_loaded(self, data: Dict[str, Any]):
        """初始文件加载完成"""
        self.load_file_content(data)

    def _on_load_error(self, error_msg: str):
        """加载失败"""
        logger.error(f"加载失败: {error_msg}")
        MessageService.show_error(self, f"加载失败: {error_msg}")

    def _refresh_directory_tree(self):
        """刷新目录树"""
        self._load_directory_tree()

    # ========== 事件处理 ==========

    def _on_file_selected(self, file_data: Dict[str, Any]):
        """文件选中事件"""
        self.load_file_content(file_data)

    def _toggle_assistant(self, visible: bool):
        """切换助手面板显示"""
        self._assistant_visible = visible
        if self.assistant_panel:
            self.assistant_panel.setVisible(visible)

    def _go_back(self):
        """返回项目详情页"""
        self.navigateTo('CODING_DETAIL', project_id=self.project_id)

    def _go_to_detail(self):
        """进入项目详情页"""
        self.navigateTo('CODING_DETAIL', project_id=self.project_id)

    # ========== 生命周期 ==========

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            # 更新Sidebar的project_id
            if self.sidebar:
                self.sidebar.project_id = self.project_id
            if self.assistant_panel:
                self.assistant_panel.project_id = self.project_id

        if 'file_id' in params:
            self.initial_file_id = params['file_id']

        self._load_project()

    def onHide(self):
        """页面隐藏时清理"""
        # 停止生成
        self.stop_generation()

        # 停止所有Worker
        self.worker_manager.stop_all()

        # 清理助手面板
        if self.assistant_panel:
            self.assistant_panel.cleanup()

        # 清理Sidebar
        if self.sidebar:
            self.sidebar.cleanup()

    def onShow(self):
        """页面显示时"""
        pass


__all__ = ["CodingDesk"]
