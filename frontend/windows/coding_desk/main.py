"""
编程项目Prompt生成工作台主类

提供文件Prompt的生成、编辑和版本管理功能。
采用 Mixin 架构，参考 WritingDesk 的布局模式。
"""

import logging
from typing import Optional, Dict, Any

from windows.base import BaseWorkspacePage
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from utils.dpi_utils import dp
from themes.theme_manager import theme_manager

from .header import CodingDeskHeader
from .sidebar import CodingSidebar
from .workspace import CodingWorkspace
from .assistant_panel import CodingAssistantPanel
from .mixins import FileGenerationMixin, ContentManagementMixin

logger = logging.getLogger(__name__)


class CodingDesk(FileGenerationMixin, ContentManagementMixin, BaseWorkspacePage):
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
        super().__init__(project_id, parent)
        self.initial_file_id = file_id

        self.api_client = APIClientManager.get_client()

        # 项目数据
        self._project_data: Optional[Dict[str, Any]] = None
        self._tree_data: Optional[Dict[str, Any]] = None

        # 初始化Mixin
        self._init_generation_mixin()
        self._init_content_mixin()

        self._assistant_visible = True

        self.setupUI()
        self._load_project()

    def setupUI(self):
        super().setupUI()

    def create_header(self):
        """创建Header组件"""
        return CodingDeskHeader(self)

    def create_sidebar(self):
        """创建Sidebar组件"""
        sidebar = CodingSidebar(self.project_id, self)
        sidebar.setFixedWidth(dp(280))
        return sidebar

    def create_workspace(self):
        """创建Workspace组件"""
        return CodingWorkspace(self)

    def create_assistant_panel(self):
        """创建辅助面板组件"""
        panel = CodingAssistantPanel(self.project_id, self)
        panel.setMinimumWidth(dp(280))
        panel.setMaximumWidth(dp(500))
        panel.setVisible(self._assistant_visible)
        return panel

    def _configure_splitter(self, splitter):
        """配置分割器"""
        splitter.setHandleWidth(dp(4))
        splitter.setSizes([dp(700), dp(300)])
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

    def _connect_signals(self):
        """连接信号"""
        if self.header:
            self.header.goBackClicked.connect(self._go_back)
            self.header.goToDetailClicked.connect(self._go_to_detail)
            self.header.toggleAssistantClicked.connect(self._toggle_assistant)

        if self.sidebar:
            self.sidebar.fileSelected.connect(self._on_file_selected)
            self.sidebar.refreshRequested.connect(self._refresh_directory_tree)

        if self.workspace:
            self.workspace.generateRequested.connect(self.start_file_generation)
            self.workspace.saveRequested.connect(self.save_file_content)
            self.workspace.generateReviewRequested.connect(self.start_review_generation)

        if self.assistant_panel:
            self.assistant_panel.structureUpdated.connect(self._on_structure_updated)
            self.assistant_panel.refreshTreeRequested.connect(self._refresh_directory_tree)
            self.assistant_panel.planningStarted.connect(self._on_planning_started)
            self.assistant_panel.planningCompleted.connect(self._on_planning_completed)

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

        # 更新助手面板的目录状态（用于显示优化按钮）
        if self.assistant_panel:
            has_directories = data.get('total_directories', 0) > 0
            self.assistant_panel.set_has_directories(has_directories)

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

    # ========== Agent信号处理 ==========

    def _on_structure_updated(self, directories: list, files: list):
        """Agent结构更新事件

        Agent规划过程中实时更新目录树，数据还未保存到数据库。
        """
        if self.sidebar:
            self.sidebar.update_tree_from_agent_data(directories, files)

    def _on_planning_started(self):
        """Agent规划开始"""
        logger.info("Agent目录规划已开始")
        # 可以在这里添加UI反馈，如禁用某些按钮

    def _on_planning_completed(self):
        """Agent规划完成"""
        logger.info("Agent目录规划已完成")
        # 规划完成后刷新目录树（从数据库获取最新数据）
        self._refresh_directory_tree()
        # 更新助手面板的目录状态
        if self.assistant_panel:
            has_directories = bool(self._tree_data and self._tree_data.get('total_directories', 0) > 0)
            self.assistant_panel.set_has_directories(has_directories)

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
