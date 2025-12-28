"""
写作台主类

集成Header、Sidebar、Workspace，提供完整的章节写作功能。
采用Mixin架构拆分功能模块：
- ChapterGenerationMixin: 章节生成相关
- ContentManagementMixin: 内容保存、RAG入库、编辑
- VersionManagementMixin: 版本选择、重试
- EvaluationMixin: 章节评估
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QSizePolicy,
)
from pages.base_page import BasePage
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.worker_manager import WorkerManager
from utils.message_service import MessageService
from utils.dpi_utils import dp
from themes.theme_manager import theme_manager

from .header import WDHeader
from .sidebar import WDSidebar
from .workspace import WDWorkspace
from .assistant_panel import AssistantPanel

# 导入Mixin模块（从 mixins/ 子目录）
from .mixins import (
    ChapterGenerationMixin,
    ContentManagementMixin,
    VersionManagementMixin,
    EvaluationMixin,
)

logger = logging.getLogger(__name__)


class WritingDesk(
    ChapterGenerationMixin,
    ContentManagementMixin,
    VersionManagementMixin,
    EvaluationMixin,
    BasePage,
):
    """写作台页面 - 禅意风格

    采用Mixin架构组织功能：
    - ChapterGenerationMixin: 章节生成、SSE流式处理、提示词预览
    - ContentManagementMixin: 内容保存、RAG入库、编辑
    - VersionManagementMixin: 版本选择、重试生成
    - EvaluationMixin: 章节分析评估
    """

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = APIClientManager.get_client()
        self.project = None
        self.selected_chapter_number = None
        self.generating_chapter = None

        # 异步任务管理 - 使用 WorkerManager 统一管理
        self.worker_manager = WorkerManager(self)
        self._sse_worker = None  # SSE Worker 单独管理（需要特殊的 stop 方法）
        self._progress_dialog = None  # 进度对话框

        self.setupUI()
        self.loadProject()

    def setupUI(self):
        """初始化UI"""
        logger.info("WritingDesk.setupUI 被调用")
        # 如果布局不存在，创建UI结构
        if not self.layout():
            logger.info("布局不存在，调用 _create_ui_structure")
            self._create_ui_structure()
        else:
            logger.info("布局已存在，跳过 _create_ui_structure")
        # 总是应用主题样式
        logger.info("应用主题样式")
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次，优化版：批量创建后处理事件）"""
        from PyQt6.QtWidgets import QApplication

        logger.info("WritingDesk._create_ui_structure 开始执行")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header（轻量组件，快速创建）
        self.header = WDHeader()
        main_layout.addWidget(self.header)

        # 主内容区
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        content_layout.setSpacing(dp(12))

        # Sidebar（固定宽度）- 可能包含大量章节卡片
        self.sidebar = WDSidebar()
        content_layout.addWidget(self.sidebar)

        # Workspace（占据剩余空间）
        self.workspace = WDWorkspace()
        self.workspace.setProjectId(self.project_id)
        self.workspace.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.workspace, stretch=1)

        # RAG Assistant Panel（固定宽度，初始隐藏）
        self.assistant_panel = AssistantPanel(self.project_id)
        self.assistant_panel.setFixedWidth(dp(320))
        self.assistant_panel.setVisible(False)
        content_layout.addWidget(self.assistant_panel, stretch=0)

        main_layout.addWidget(self.content_widget, stretch=1)

        # 所有主要组件创建完成后，处理一次事件循环
        QApplication.processEvents()

        # 统一连接所有信号
        self._connect_signals()

    def _connect_signals(self):
        """统一管理所有信号连接"""
        # Header 信号
        self.header.goBackClicked.connect(self.goBackToWorkspace)
        self.header.viewDetailClicked.connect(self.openProjectDetail)
        self.header.exportClicked.connect(self.exportNovel)
        self.header.toggleAssistantClicked.connect(self.toggleAssistant)

        # Sidebar 信号
        self.sidebar.chapterSelected.connect(self.onChapterSelected)
        self.sidebar.generateChapter.connect(self.onGenerateChapter)
        self.sidebar.generateOutline.connect(self.onGenerateOutline)
        self.sidebar.createChapter.connect(self.onCreateChapter)
        self.sidebar.viewProtagonistProfile.connect(self.onViewProtagonistProfile)

        # Workspace 信号
        self.workspace.generateChapterRequested.connect(self.onGenerateChapter)
        self.workspace.previewPromptRequested.connect(self.onPreviewPrompt)
        self.workspace.saveContentRequested.connect(self.onSaveContent)
        self.workspace.ragIngestRequested.connect(self.onRagIngest)
        self.workspace.selectVersion.connect(self.onSelectVersion)
        self.workspace.evaluateChapter.connect(self.onEvaluateChapter)
        self.workspace.retryVersion.connect(self.onRetryVersion)
        self.workspace.editContent.connect(self.onEditContent)
        self.workspace.chapterContentLoaded.connect(self.onChapterContentLoaded)

        # Assistant Panel 信号
        self.assistant_panel.suggestion_applied.connect(self.onSuggestionApplied)

    def toggleAssistant(self, show: bool):
        """切换RAG助手显示状态"""
        self.assistant_panel.setVisible(show)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        from PyQt6.QtCore import Qt
        from themes.modern_effects import ModernEffects

        bg_color = theme_manager.book_bg_primary()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = transparency_config.get("content_opacity", 0.95)

        if transparency_enabled:
            # 透明模式：使用RGBA背景色实现半透明效果
            # 当content_opacity=0时，页面完全透明，能看到桌面
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")

            # 设置WA_TranslucentBackground使透明生效（真正的窗口透明）
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            # 指定容器设置透明（不使用findChildren避免影响其他页面）
            transparent_containers = ['header', 'content_widget', 'sidebar', 'workspace', 'assistant_panel']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)

            # content_widget 必须完全透明
            if hasattr(self, 'content_widget') and self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")
        else:
            # 普通模式：使用实色背景，恢复背景填充
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            # 恢复容器的背景填充
            containers_to_restore = ['header', 'content_widget', 'sidebar', 'workspace', 'assistant_panel']
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

            # content_widget 恢复透明样式（因为它是内容容器）
            if hasattr(self, 'content_widget') and self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")

    # ==================== 项目加载 ====================

    def loadProject(self):
        """加载项目数据（异步非阻塞，带加载指示器）"""
        logger.info(f"WritingDesk.loadProject被调用, project_id={self.project_id}")

        # 显示加载动画
        self.show_loading("正在加载项目数据...")

        worker = AsyncAPIWorker(self.api_client.get_novel, self.project_id)
        worker.success.connect(self._onProjectLoaded)
        worker.error.connect(self._onProjectLoadError)
        self.worker_manager.start(worker, 'load_project')

    def _onProjectLoaded(self, project_data):
        """项目数据加载成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        self.project = project_data
        logger.info("项目数据加载成功")

        self.header.setProject(self.project)
        self.sidebar.setProject(self.project)

    def _onProjectLoadError(self, error_msg):
        """项目数据加载失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        logger.error(f"项目加载失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    # ==================== 章节事件 ====================

    def onChapterSelected(self, chapter_number):
        """章节被选中"""
        self.selected_chapter_number = chapter_number
        self.workspace.loadChapter(chapter_number)

    def onChapterContentLoaded(self, chapter_number: int, content: str):
        """章节内容加载完成 - 更新优化面板"""
        if self.assistant_panel:
            self.assistant_panel.set_chapter_for_optimization(chapter_number, content)

    def onSuggestionApplied(self, suggestion: dict):
        """处理修改建议被应用"""
        if self.workspace:
            self.workspace.applySuggestion(suggestion)

    def onGenerateOutline(self):
        """跳转到大纲生成"""
        MessageService.show_info(self, "大纲生成功能请在项目详情页面操作")

    def onCreateChapter(self):
        """手动创建新章节（用于空白项目）

        章节编号自动分配为当前最大章节号+1，确保连续性。
        """
        from components.dialogs import InputDialog

        # 计算下一个章节编号（必须连续）
        chapters = self.project.get('chapters', []) if self.project else []
        blueprint = self.project.get('blueprint', {}) if self.project else {}
        outlines = blueprint.get('chapter_outline', [])

        # 获取已有的最大章节号
        existing_nums = set()
        for ch in chapters:
            existing_nums.add(ch.get('chapter_number', 0))
        for o in outlines:
            existing_nums.add(o.get('chapter_number', 0))

        # 下一个章节号 = 最大章节号 + 1（确保连续）
        next_chapter_num = max(existing_nums, default=0) + 1

        # 弹出输入对话框让用户输入标题
        title, ok = InputDialog.getTextStatic(
            parent=self,
            title=f"新增第{next_chapter_num}章",
            label=f"请输入第{next_chapter_num}章的标题：",
            text=f"第{next_chapter_num}章"
        )
        if not ok:
            return

        # 创建章节（内容为空，用户稍后编辑）
        self._doCreateChapter(next_chapter_num, title)

    def _doCreateChapter(self, chapter_number: int, title: str):
        """执行创建章节（异步）"""
        self.show_loading(f"正在创建第{chapter_number}章...")

        def _on_success(result):
            self.hide_loading()
            MessageService.show_success(self, f"第{chapter_number}章已创建")
            # 重新加载项目数据以刷新侧边栏
            self.loadProject()
            # 自动选中新创建的章节
            self.selected_chapter_number = chapter_number
            self.workspace.loadChapter(chapter_number)

        def _on_error(error_msg):
            self.hide_loading()
            MessageService.show_error(self, f"创建章节失败：{error_msg}")

        # 使用import_chapter API创建带标题的新章节
        worker = AsyncAPIWorker(
            self.api_client.import_chapter,
            self.project_id,
            chapter_number,
            title,
            ""  # 空内容，用户稍后编辑
        )
        worker.success.connect(_on_success)
        worker.error.connect(_on_error)
        self.worker_manager.start(worker, 'create_chapter')

    def onViewProtagonistProfile(self):
        """查看主角档案"""
        if not self.project:
            MessageService.show_warning(self, "请先加载项目")
            return

        project_id = self.project.get('id')
        if not project_id:
            return

        # 使用辅助函数获取主角名称
        from .utils import extract_protagonist_name
        protagonist_name = extract_protagonist_name(self.project)

        # 显示主角档案对话框
        from .dialogs import ProtagonistProfileDialog
        dialog = ProtagonistProfileDialog(project_id, protagonist_name, self)
        dialog.exec()

    # ==================== 导航 ====================

    def openProjectDetail(self):
        """打开项目详情"""
        self.navigateTo("DETAIL", project_id=self.project_id)

    def goBackToWorkspace(self):
        """返回首页（直接导航，避免循环历史）"""
        self.navigateTo("HOME")

    def exportNovel(self, format_type):
        """导出小说（异步非阻塞）"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出小说",
            f"{self.project.get('title', '未命名')}.{format_type}",
            f"{format_type.upper()} Files (*.{format_type})"
        )
        if not file_path:
            return

        self.show_loading("正在导出...")

        def _on_export_success(result):
            self.hide_loading()
            MessageService.show_success(self, f"导出成功：{file_path}")

        def _on_export_error(error_msg):
            self.hide_loading()
            MessageService.show_error(self, f"导出失败：{error_msg}")

        worker = AsyncAPIWorker(
            self.api_client.export_novel,
            self.project_id,
            format_type,
            file_path
        )
        worker.success.connect(_on_export_success)
        worker.error.connect(_on_export_error)
        self.worker_manager.start(worker, 'export_novel')

    # ==================== 生命周期 ====================

    def onHide(self):
        """页面隐藏时停止运行中的任务（但保持manager可复用）"""
        self._cleanup_workers(full_cleanup=False)

    def _cleanup_workers(self, full_cleanup: bool = True):
        """清理所有异步任务

        Args:
            full_cleanup: True表示完全清理（组件销毁时），False表示只停止当前任务（页面隐藏时）
        """
        # 清理SSE Worker
        self._cleanup_chapter_gen_sse()

        # 清理WorkerManager中的所有任务
        if hasattr(self, 'worker_manager') and self.worker_manager:
            if full_cleanup:
                # 完全清理：标记为已清理，不再接受新任务
                self.worker_manager.cleanup_all()
            else:
                # 只停止运行中的任务，保持manager可复用
                self.worker_manager.stop_all()

        # 清理进度对话框
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def __del__(self):
        """析构时清理资源"""
        try:
            self._cleanup_workers(full_cleanup=True)
        except (RuntimeError, AttributeError):
            pass

    def closeEvent(self, event):
        """窗口关闭时清理"""
        self._cleanup_workers(full_cleanup=True)
        super().closeEvent(event)

    def refresh(self, **params):
        """刷新页面"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            if hasattr(self, 'workspace'):
                self.workspace.setProjectId(self.project_id)
            if hasattr(self, 'assistant_panel'):
                self.assistant_panel.project_id = self.project_id
        self.loadProject()
