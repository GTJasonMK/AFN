"""
写作台主工作区 - 章节显示 Mixin

包含章节加载、显示和创建章节Widget相关的方法。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QTabWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from utils.error_handler import handle_errors
from utils.formatters import count_chinese_characters, format_word_count
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker
from components.loading_spinner import LoadingOverlay


class ChapterDisplayMixin:
    """章节显示相关方法的 Mixin"""

    def _ensure_loading_overlay(self):
        """确保加载覆盖层已创建"""
        if not hasattr(self, '_chapter_loading_overlay') or self._chapter_loading_overlay is None:
            self._chapter_loading_overlay = LoadingOverlay(
                text="正在加载章节...",
                parent=self,
                translucent=True
            )

    def loadChapter(self, chapter_number):
        """异步加载章节（带加载动画）"""
        self.current_chapter = chapter_number

        if not self.project_id:
            return

        # 显示加载动画
        self._ensure_loading_overlay()
        self._chapter_loading_overlay.show_with_animation("正在加载章节...")

        # 异步加载章节数据
        worker = AsyncAPIWorker(
            self.api_client.get_chapter,
            self.project_id,
            chapter_number
        )
        worker.success.connect(self._onChapterLoaded)
        worker.error.connect(self._onChapterLoadError)

        # 保存worker引用避免被垃圾回收
        self._chapter_load_worker = worker
        worker.start()

    def _onChapterLoaded(self, chapter_data):
        """章节数据加载成功回调"""
        # 隐藏加载动画
        if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
            self._chapter_loading_overlay.hide_with_animation()

        # 显示章节内容
        self.displayChapter(chapter_data)

    def _onChapterLoadError(self, error_msg):
        """章节数据加载失败回调"""
        # 隐藏加载动画
        if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
            self._chapter_loading_overlay.hide_with_animation()

        # 显示错误提示
        from utils.message_service import MessageService
        MessageService.show_error(self, f"加载章节失败：{error_msg}")

    def displayChapter(self, chapter_data):
        """显示章节内容"""
        # 保存章节数据用于主题切换
        self.current_chapter_data = chapter_data

        # 移除旧的内容widget
        if self.content_widget:
            self.stack.removeWidget(self.content_widget)
            self.content_widget.deleteLater()

        # 创建新的内容widget
        self.content_widget = self.createChapterWidget(chapter_data)
        self.stack.addWidget(self.content_widget)
        self.stack.setCurrentWidget(self.content_widget)

        # 发射章节内容加载完成信号（用于优化面板）
        chapter_number = chapter_data.get('chapter_number')
        # 注意：get('content', '') 在 content 为 None 时仍返回 None，需要用 or
        content = chapter_data.get('content') or ''
        if chapter_number:
            # 即使内容为空也发射信号，让优化面板显示正确的状态
            self.chapterContentLoaded.emit(chapter_number, content)

    def createChapterWidget(self, chapter_data):
        """创建章节内容widget（优化版：分步创建，避免UI卡顿）"""
        from PyQt6.QtWidgets import QApplication

        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        widget = QWidget()
        # 设置明确的颜色以避免系统默认
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))  # 压缩外边距
        layout.setSpacing(dp(12))  # 减少间距

        # 章节标题卡片 - 紧凑版渐变设计
        header = QFrame()
        header.setObjectName("chapter_header")

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(dp(12))
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, dp(2))
        header.setGraphicsEffect(shadow)

        # 应用渐变背景
        gradient = ModernEffects.linear_gradient(
            theme_manager.PRIMARY_GRADIENT,
            135
        )
        header.setStyleSheet(f"""
            QFrame#chapter_header {{
                background: {gradient};
                border: none;
                border-radius: {theme_manager.RADIUS_MD};
                padding: {dp(12)}px;
            }}
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(dp(12))
        header_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))  # 紧凑内边距

        # 左侧：章节信息
        info_widget = QWidget()
        # 确保透明背景以显示父元素的渐变背景
        info_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        self.chapter_title = QLabel(chapter_data.get('title', f"第{chapter_data.get('chapter_number', '')}章"))
        self.chapter_title.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(18)}px;
            font-weight: 700;
            color: {theme_manager.BUTTON_TEXT};
        """)
        info_layout.addWidget(self.chapter_title)

        # 章节元信息
        meta_text = f"第 {chapter_data.get('chapter_number', '')} 章"
        content = chapter_data.get('content', '')
        if content:
            word_count = count_chinese_characters(content)
            meta_text += f" | {format_word_count(word_count)}"

        meta_label = QLabel(meta_text)
        meta_label.setObjectName("chapter_meta_label")  # 添加objectName用于主题切换
        meta_label.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(12)}px;
            color: {theme_manager.BUTTON_TEXT};
            opacity: 0.85;
        """)
        info_layout.addWidget(meta_label)

        header_layout.addWidget(info_widget, stretch=1)

        # 右侧：按钮组 - 紧凑版
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(8))

        # 预览提示词按钮
        self.preview_btn = QPushButton("预览提示词")
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {serif_font};
                background-color: transparent;
                color: {theme_manager.BUTTON_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(12)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        self.preview_btn.clicked.connect(lambda: self.previewPromptRequested.emit(self.current_chapter))
        btn_layout.addWidget(self.preview_btn)

        # 生成章节按钮
        self.generate_btn = QPushButton("生成章节")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {serif_font};
                background-color: rgba(255, 255, 255, 0.2);
                color: {theme_manager.BUTTON_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)
        self.generate_btn.clicked.connect(lambda: self.generateChapterRequested.emit(self.current_chapter))
        btn_layout.addWidget(self.generate_btn)

        header_layout.addWidget(btn_widget)

        layout.addWidget(header)

        # 让出事件循环，让动画能够更新
        QApplication.processEvents()

        # TabWidget：正文、版本、评审、摘要
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(theme_manager.tabs())

        # Tab 1: 正文 - 使用 ContentPanelBuilder（最重要，先创建）
        content_tab = self._content_builder.create_content_tab(chapter_data)
        self.content_text = self._content_builder.content_text  # 保存引用用于主题切换
        self.tab_widget.addTab(content_tab, "正文")
        QApplication.processEvents()  # 让动画更新

        # Tab 2: 版本历史 - 使用 VersionPanelBuilder
        versions_tab = self._version_builder.create_versions_tab(chapter_data, self)
        self.tab_widget.addTab(versions_tab, "版本")
        QApplication.processEvents()  # 让动画更新

        # Tab 3: 评审 - 使用 ReviewPanelBuilder
        review_tab = self._review_builder.create_review_tab(chapter_data, self)
        self.tab_widget.addTab(review_tab, "评审")
        QApplication.processEvents()  # 让动画更新

        # Tab 4: 章节摘要（用于RAG上下文）- 使用 SummaryPanelBuilder
        summary_tab = self._summary_builder.create_summary_tab(chapter_data, self)
        self.tab_widget.addTab(summary_tab, "摘要")
        QApplication.processEvents()  # 让动画更新

        # Tab 5: 章节分析（结构化信息）- 使用 AnalysisPanelBuilder
        analysis_tab = self._analysis_builder.create_analysis_tab(chapter_data)
        self.tab_widget.addTab(analysis_tab, "分析")
        QApplication.processEvents()  # 让动画更新

        # Tab 6: 漫画提示词 - 使用 MangaPanelBuilder
        # 先创建空状态的漫画Tab，避免同步API调用阻塞UI
        empty_manga_data = {
            'has_manga_prompt': False,
            'scenes': [],
            'character_profiles': {},
            'style_guide': '',
            'images': [],
            'pdf_info': {},
            '_is_loading': True,  # 标记正在加载
        }
        manga_tab = self._manga_builder.create_manga_tab(empty_manga_data, self)
        self.tab_widget.addTab(manga_tab, "漫画")

        layout.addWidget(self.tab_widget, stretch=1)

        # 异步加载漫画数据，避免UI阻塞
        self._loadMangaDataAsync()

        return widget
