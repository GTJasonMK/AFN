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


class WDWorkspace(
    ThemeRefreshMixin,
    ChapterDisplayMixin,
    InlineDiffMixin,
    MangaHandlersMixin,
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
        )

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

    def saveContent(self):
        """保存章节内容（仅保存，不触发RAG处理）"""
        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.saveContentRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示

    def ragIngest(self):
        """保存章节内容并执行RAG处理（摘要、分析、索引、向量入库）"""
        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.ragIngestRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示
