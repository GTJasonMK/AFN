"""
写作台主工作区 - 核心模块

包含 WDWorkspace 主类定义、信号、初始化和基础方法。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QStackedWidget, QApplication
)
from PyQt6.QtCore import pyqtSignal

from components.base import ThemeAwareFrame
from components.empty_state import EmptyStateWithIllustration
from themes.book_theme_styler import BookThemeStyler
from api.manager import APIClientManager

from ..panels import (
    AnalysisPanelBuilder,
    VersionPanelBuilder,
    ReviewPanelBuilder,
    SummaryPanelBuilder,
    ContentPanelBuilder,
)
from ..panels.manga import MangaPanelBuilder

from .theme_refresh import ThemeRefreshMixin
from .chapter_display import ChapterDisplayMixin
from .inline_diff import InlineDiffMixin
from .manga_handlers import MangaHandlersMixin
from .generation_handlers import GenerationHandlersMixin


class WDWorkspace(
    ThemeRefreshMixin,
    ChapterDisplayMixin,
    InlineDiffMixin,
    MangaHandlersMixin,
    GenerationHandlersMixin,
    ThemeAwareFrame
):
    """主工作区 - 章节内容与版本管理"""

    # 信号定义
    generateChapterRequested = pyqtSignal(int)  # chapter_number
    previewPromptRequested = pyqtSignal(int)  # chapter_number - 预览提示词
    saveContentRequested = pyqtSignal(int, str)  # chapter_number, content（仅保存内容）
    ragIngestRequested = pyqtSignal(int, str)  # chapter_number, content（保存并执行RAG处理）
    selectVersion = pyqtSignal(int)  # version_index
    evaluateChapter = pyqtSignal()  # 评审当前章节
    retryVersion = pyqtSignal(int)  # version_index
    editContent = pyqtSignal(str)  # new_content
    chapterContentLoaded = pyqtSignal(int, str)  # chapter_number, content - 章节内容加载完成

    def __init__(self, parent=None):
        self.api_client = APIClientManager.get_client()
        self.current_chapter = None
        self.project_id = None
        self.current_chapter_data = None  # 保存当前章节数据用于主题切换时重建

        # 版本切换保护：防止在版本切换期间保存导致内容覆盖错误版本
        self._version_switching = False
        # 记录当前编辑器对应的版本ID，用于保存时验证
        self._current_version_id = None

        # 样式器 - 缓存主题值，避免重复调用theme_manager
        self._styler = BookThemeStyler()

        # 面板构建器 - 使用方法引用处理用户交互（避免Lambda捕获self导致的内存泄漏风险）
        self._analysis_builder = AnalysisPanelBuilder()
        self._version_builder = VersionPanelBuilder(
            on_select_version=self._emitSelectVersion,
            on_retry_version=self._emitRetryVersion
        )
        self._review_builder = ReviewPanelBuilder(
            on_evaluate_chapter=self._emitEvaluateChapter
        )
        self._summary_builder = SummaryPanelBuilder()
        self._content_builder = ContentPanelBuilder(
            on_save_content=self.saveContent,
            on_rag_ingest=self.ragIngest
        )

        # 漫画面板构建器
        self._manga_builder = MangaPanelBuilder(
            on_generate=self._onGenerateMangaPrompt,
            on_copy_prompt=self._onCopyPrompt,
            on_delete=self._onDeleteMangaPrompt,
            on_generate_image=self._onGenerateImage,
            on_load_images=self._loadChapterImages,
            on_generate_pdf=self._onGenerateMangaPDF,
            on_load_pdf=self._loadChapterMangaPDF,
            on_download_pdf=self._onDownloadPDF,
            on_generate_all_images=self._onGenerateAllImages,
            on_preview_prompt=self._onPreviewPrompt,
        )

        # 漫画生成状态标志（记录正在生成的章节号，None表示没有生成）
        self._manga_generating_chapter = None

        # 保存组件引用
        self.empty_state = None
        self.content_widget = None
        self.chapter_title = None
        self.tab_widget = None
        self.content_text = None
        self.generate_btn = None
        self.preview_btn = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 空状态提示 - 使用专业空状态组件
        self.empty_state = EmptyStateWithIllustration(
            illustration_char='P',
            title='准备开始创作',
            description='从左侧选择一个章节，开始你的写作之旅',
            parent=self
        )

        # 内容区域（堆叠布局）
        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty_state)

        layout.addWidget(self.stack)

    def setProjectId(self, project_id):
        """设置项目ID"""
        # 如果项目ID变化，清空旧项目的缓存
        if self.project_id and self.project_id != project_id:
            from utils.chapter_cache import get_chapter_cache
            get_chapter_cache().invalidate(self.project_id)

        self.project_id = project_id

    # ==================== 信号发射包装方法 ====================
    # 这些方法用于替代Lambda回调，避免Lambda捕获self导致的潜在内存泄漏

    def _emitSelectVersion(self, idx: int):
        """发射选择版本信号"""
        self.selectVersion.emit(idx)

    def _emitRetryVersion(self, idx: int):
        """发射重试版本信号"""
        self.retryVersion.emit(idx)

    def _emitEvaluateChapter(self):
        """发射评审章节信号"""
        self.evaluateChapter.emit()

    def setVersionSwitching(self, switching: bool):
        """设置版本切换状态

        在版本切换期间禁用保存操作，防止内容覆盖错误版本。

        Args:
            switching: True表示正在切换版本，False表示切换完成
        """
        self._version_switching = switching
        # 更新保存按钮状态
        self._updateSaveButtonState()

    def _updateSaveButtonState(self):
        """更新保存按钮的启用状态"""
        if hasattr(self, '_content_builder') and self._content_builder:
            # 版本切换期间禁用保存按钮
            enabled = not self._version_switching
            self._content_builder.set_save_enabled(enabled)

    def saveContent(self):
        """保存章节内容（仅保存，不触发RAG处理）"""
        # 版本切换保护：防止在版本切换期间保存
        if self._version_switching:
            from utils.message_service import MessageService
            MessageService.show_warning(self, "正在切换版本，请稍后再保存")
            return

        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.saveContentRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示

    def ragIngest(self):
        """保存章节内容并执行RAG处理（摘要、分析、索引、向量入库）"""
        # 版本切换保护：防止在版本切换期间保存
        if self._version_switching:
            from utils.message_service import MessageService
            MessageService.show_warning(self, "正在切换版本，请稍后再操作")
            return

        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.ragIngestRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示
