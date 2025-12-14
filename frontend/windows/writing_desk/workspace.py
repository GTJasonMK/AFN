"""
写作台主工作区 - 现代化设计

功能：章节内容展示、版本管理、章节编辑
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QStackedWidget, QScrollArea, QTextEdit, QTabWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from components.empty_state import EmptyStateWithIllustration
from themes.theme_manager import theme_manager
from themes.book_theme_styler import BookThemeStyler
from themes.modern_effects import ModernEffects
from api.manager import APIClientManager
from utils.error_handler import handle_errors
from utils.formatters import count_chinese_characters, format_word_count
from utils.dpi_utils import dp, sp
from utils.constants import VersionConstants
from .panels import (
    AnalysisPanelBuilder,
    VersionPanelBuilder,
    ReviewPanelBuilder,
    SummaryPanelBuilder,
    ContentPanelBuilder,
)
from .panels.manga_panel import MangaPanelBuilder


class WDWorkspace(ThemeAwareFrame):
    """主工作区 - 章节内容与版本管理"""

    generateChapterRequested = pyqtSignal(int)  # chapter_number
    previewPromptRequested = pyqtSignal(int)  # chapter_number - 预览提示词
    saveContentRequested = pyqtSignal(int, str)  # chapter_number, content
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

        # 面板构建器 - 使用回调函数模式处理用户交互
        self._analysis_builder = AnalysisPanelBuilder()
        self._version_builder = VersionPanelBuilder(
            on_select_version=lambda idx: self.selectVersion.emit(idx),
            on_retry_version=lambda idx: self.retryVersion.emit(idx)
        )
        self._review_builder = ReviewPanelBuilder(
            on_evaluate_chapter=lambda: self.evaluateChapter.emit()
        )
        self._summary_builder = SummaryPanelBuilder()
        self._content_builder = ContentPanelBuilder(
            on_save_content=self.saveContent
        )

        # 漫画面板构建器
        self._manga_builder = MangaPanelBuilder(
            on_generate=self._onGenerateMangaPrompt,
            on_copy_prompt=self._onCopyPrompt,
            on_delete=self._onDeleteMangaPrompt,
            on_generate_image=self._onGenerateImage,
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
            illustration_char='📝',
            title='准备开始创作',
            description='从左侧选择一个章节，开始你的写作之旅',
            parent=self
        )

        # 内容区域（堆叠布局）
        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty_state)

        layout.addWidget(self.stack)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 刷新样式器的缓存值
        self._styler.refresh()

        # 刷新所有 Panel Builders 的样式器缓存
        # 这样在重建章节内容时，Panel Builders 会使用新主题的颜色
        self._analysis_builder.refresh_theme()
        self._version_builder.refresh_theme()
        self._review_builder.refresh_theme()
        self._summary_builder.refresh_theme()
        self._content_builder.refresh_theme()
        self._manga_builder.refresh_theme()

        self.setStyleSheet(f"""
            WDWorkspace {{
                background-color: transparent;
            }}
        """)

        # 如果有显示中的章节内容，重建章节内容以应用新主题
        # 重建比逐一更新样式更可靠，因为很多动态创建的子组件没有objectName
        if self.current_chapter_data:
            # 保存当前tab索引，以便重建后恢复
            current_tab_index = self.tab_widget.currentIndex() if self.tab_widget else 0

            # 重建章节内容
            self.displayChapter(self.current_chapter_data)

            # 恢复tab索引
            if self.tab_widget and current_tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(current_tab_index)

    def setProjectId(self, project_id):
        """设置项目ID"""
        self.project_id = project_id

    def _refresh_content_styles(self):
        """刷新内容区域的主题样式（主题切换时调用） - 书香风格"""
        if not self.content_widget:
            return

        # 使用缓存的样式器属性（避免重复调用theme_manager）
        s = self._styler

        # 更新章节标题卡片 - 简约风格
        if chapter_header := self.content_widget.findChild(QFrame, "chapter_header"):
            chapter_header.setStyleSheet(f"""
                QFrame#chapter_header {{
                    background-color: {s.bg_primary};
                    border-bottom: 1px solid {s.border_color};
                    border-radius: 0px;
                    padding: {dp(12)}px;
                }}
            """)
            chapter_header.setGraphicsEffect(None)

        # 更新章节标题文字
        if self.chapter_title:
            self.chapter_title.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(20)}px;
                font-weight: bold;
                color: {s.text_primary};
            """)

        # 更新章节元信息标签
        if meta_label := self.content_widget.findChild(QLabel, "chapter_meta_label"):
            meta_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                font-style: italic;
            """)

        # 更新生成按钮
        if self.generate_btn:
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {s.accent_color};
                    color: {s.button_text};
                    border: 1px solid {s.accent_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {s.ui_font};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {s.text_primary};
                    border-color: {s.text_primary};
                }}
            """)

        # 更新TabWidget
        if self.tab_widget:
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: none;
                    background: transparent;
                }}
                QTabBar::tab {{
                    background: transparent;
                    color: {s.text_secondary};
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {s.ui_font};
                    border-bottom: 2px solid transparent;
                }}
                QTabBar::tab:selected {{
                    color: {s.accent_color};
                    border-bottom: 2px solid {s.accent_color};
                    font-weight: bold;
                }}
                QTabBar::tab:hover {{
                    color: {s.text_primary};
                }}
            """)

        # 更新文本编辑器 - 纸张效果
        if self.content_text:
            self.content_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {s.bg_secondary};
                    border: none;
                    padding: {dp(32)}px;
                    font-family: {s.serif_font};
                    font-size: {sp(16)}px;
                    color: {s.text_primary};
                    line-height: 1.8;
                    selection-background-color: {s.accent_color};
                    selection-color: {s.button_text};
                }}
                {s.scrollbar_style()}
            """)

        # 更新编辑器容器 - 去除玻璃态，改为边框
        if editor_container := self.content_widget.findChild(QFrame, "editor_container"):
            editor_container.setStyleSheet(f"""
                QFrame#editor_container {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(2)}px;
                }}
            """)

        # 更新工具栏样式
        if toolbar := self.content_widget.findChild(QFrame, "content_toolbar"):
            toolbar.setStyleSheet(f"""
                QFrame#content_toolbar {{
                    background-color: transparent;
                    border-bottom: 1px solid {s.border_color};
                    border-radius: 0;
                    padding: {dp(6)}px {dp(10)}px;
                }}
            """)

        # 更新字数统计标签
        if word_count_label := self.content_widget.findChild(QLabel, "word_count_label"):
            word_count_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                color: {s.text_secondary};
            """)

        # 更新状态标签
        if status_label := self.content_widget.findChild(QLabel, "status_label"):
            status_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                color: {s.accent_color};
            """)

        # 更新保存按钮
        if save_btn := self.content_widget.findChild(QPushButton, "save_btn"):
            save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {s.text_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px {dp(12)}px;
                    font-family: {s.ui_font};
                }}
                QPushButton:hover {{
                    color: {s.accent_color};
                    border-color: {s.accent_color};
                }}
            """)

        # 更新滚动区域的样式
        for scroll_area in self.content_widget.findChildren(QScrollArea):
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {s.scrollbar_style()}
            """)

        # 更新版本卡片样式
        self._refresh_version_cards_styles()

        # 更新评审卡片样式
        self._refresh_review_styles()

        # 更新摘要标签页样式
        self._refresh_summary_styles()

        # 更新分析标签页样式
        self._refresh_analysis_styles()

    def _refresh_summary_styles(self):
        """刷新摘要标签页的主题样式"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新说明卡片
        if info_card := self.content_widget.findChild(QFrame, "summary_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#summary_info_card {{
                    background-color: {s.info_bg};
                    border: 1px solid {s.info};
                    border-left: 4px solid {s.info};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新说明标题
        if info_title := self.content_widget.findChild(QLabel, "summary_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_info};
            """)

        # 更新说明描述
        if info_desc := self.content_widget.findChild(QLabel, "summary_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            """)

        # 更新摘要内容卡片
        if summary_card := self.content_widget.findChild(QFrame, "summary_content_card"):
            summary_card.setStyleSheet(f"""
                QFrame#summary_content_card {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(2)}px;
                }}
            """)

        # 更新摘要文本编辑器
        if summary_text := self.content_widget.findChild(QTextEdit, "summary_text_edit"):
            summary_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {s.bg_secondary};
                    border: none;
                    padding: {dp(16)}px;
                    font-family: {s.serif_font};
                    font-size: {sp(15)}px;
                    color: {s.text_primary};
                    line-height: 1.8;
                }}
                {s.scrollbar_style()}
            """)

        # 更新字数统计标签
        if word_count := self.content_widget.findChild(QLabel, "summary_word_count"):
            word_count.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                padding: {dp(4)}px 0;
            """)

    def _refresh_analysis_styles(self):
        """刷新分析标签页的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新滚动区域
        if scroll_area := self.content_widget.findChild(QScrollArea, "analysis_scroll_area"):
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                {s.scrollbar_style()}
            """)

        # 更新分析说明卡片
        if info_card := self.content_widget.findChild(QFrame, "analysis_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#analysis_info_card {{
                    background-color: {s.info_bg};
                    border: 1px solid {s.info};
                    border-left: 4px solid {s.info};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新分析说明标题
        if info_title := self.content_widget.findChild(QLabel, "analysis_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_info};
            """)

        # 更新分析说明描述
        if info_desc := self.content_widget.findChild(QLabel, "analysis_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            """)

        # 更新各个分区卡片
        section_names = ["summaries", "metadata", "character_states", "key_events", "foreshadowing"]
        for section_name in section_names:
            if section_card := self.content_widget.findChild(QFrame, f"analysis_section_{section_name}"):
                section_card.setStyleSheet(f"""
                    QFrame#analysis_section_{section_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新分区标题
                if title_label := section_card.findChild(QLabel, f"section_title_{section_name}"):
                    title_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(14)}px;
                        font-weight: 600;
                        color: {s.text_primary};
                    """)

                # 更新分区图标
                if icon_label := section_card.findChild(QLabel, f"section_icon_{section_name}"):
                    icon_label.setStyleSheet(f"""
                        font-size: {sp(16)}px;
                        color: {s.accent_color};
                    """)

        # 更新所有子标签的样式
        for label in self.content_widget.findChildren(QLabel):
            obj_name = label.objectName()
            if obj_name.startswith("analysis_label_"):
                # 特殊处理语义标签 - 使用对应的语义文字色
                if obj_name == "analysis_label_planted":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_warning};
                    """)
                elif obj_name == "analysis_label_resolved":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_success};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name == "analysis_label_tensions":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_error};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name in ["analysis_label_tone", "analysis_label_timeline"]:
                    # 情感基调和时间标记的小标签使用三级文字色
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(11)}px;
                        color: {s.text_tertiary};
                    """)
                else:
                    # 其他标签使用次要文字色
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_secondary};
                    """)
            elif obj_name.startswith("analysis_text_"):
                # 特殊处理语义文字
                if obj_name == "analysis_text_tone":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {s.text_warning};
                    """)
                elif obj_name == "analysis_text_timeline":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {s.text_info};
                    """)
                else:
                    label.setStyleSheet(f"""
                        font-family: {s.serif_font};
                        font-size: {sp(13)}px;
                        color: {s.text_primary};
                        line-height: 1.6;
                    """)
            elif obj_name.startswith("analysis_highlight_"):
                # 高亮框：透明背景+彩色边框
                label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(14)}px;
                    color: {s.accent_color};
                    font-weight: 500;
                    padding: {dp(10)}px;
                    background-color: transparent;
                    border: 1px solid {s.accent_color};
                    border-left: 3px solid {s.accent_color};
                    border-radius: {dp(4)}px;
                """)

        # 更新角色状态卡片
        for char_card in self.content_widget.findChildren(QFrame):
            if char_card.objectName().startswith("char_state_card_"):
                char_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(10)}px;
                    }}
                """)

        # 更新事件卡片
        for event_card in self.content_widget.findChildren(QFrame):
            if event_card.objectName().startswith("event_card_"):
                event_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {s.bg_secondary};
                        border-left: 3px solid {s.accent_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(8)}px;
                    }}
                """)

        # 更新伏笔卡片
        for fs_card in self.content_widget.findChildren(QFrame):
            if fs_card.objectName().startswith("foreshadow_card_"):
                fs_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {s.warning}08;
                        border-left: 2px solid {s.warning};
                        border-radius: {dp(4)}px;
                        padding: {dp(8)}px;
                    }}
                """)

    def _refresh_version_cards_styles(self):
        """刷新版本卡片的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 查找所有 QTabWidget，排除主TabWidget，应用简约Tab样式
        for tab_widget in self.content_widget.findChildren(QTabWidget):
            if tab_widget != self.tab_widget:
                tab_widget.setStyleSheet(f"""
                    QTabWidget::pane {{ border: none; background: transparent; }}
                    QTabBar::tab {{
                        background: transparent; color: {s.text_secondary};
                        padding: {dp(6)}px {dp(12)}px; font-family: {s.ui_font};
                        border-bottom: 2px solid transparent;
                    }}
                    QTabBar::tab:selected {{
                        color: {s.accent_color}; border-bottom: 2px solid {s.accent_color};
                    }}
                """)

        # 查找所有版本卡片并更新样式
        for i in range(VersionConstants.MAX_VERSION_CARDS):
            card_name = f"version_card_{i}"
            if version_card := self.content_widget.findChild(QFrame, card_name):
                version_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(2)}px;
                        padding: {dp(2)}px;
                    }}
                """)

                # 更新版本卡片内的文本编辑器
                for text_edit in version_card.findChildren(QTextEdit):
                    text_edit.setStyleSheet(f"""
                        QTextEdit {{
                            background-color: transparent;
                            border: none;
                            padding: {dp(16)}px;
                            font-family: {s.serif_font};
                            font-size: {sp(14)}px;
                            color: {s.text_primary};
                            line-height: 1.6;
                        }}
                        {s.scrollbar_style()}
                    """)

            # 更新版本信息栏
            info_bar_name = f"version_info_bar_{i}"
            if info_bar := self.content_widget.findChild(QFrame, info_bar_name):
                info_bar.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                        border-top: 1px solid {s.border_color};
                        border-radius: 0;
                        padding: {dp(8)}px {dp(12)}px;
                    }}
                """)

                # 更新信息栏内的标签
                for label in info_bar.findChildren(QLabel):
                    if "info_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.ui_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                        """)

                # 更新按钮样式 - 简约风
                btn_style = f"""
                    QPushButton {{
                        background: transparent;
                        color: {s.text_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(4)}px {dp(8)}px;
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                    }}
                    QPushButton:hover {{
                        color: {s.accent_color};
                        border-color: {s.accent_color};
                    }}
                """

                for btn in info_bar.findChildren(QPushButton):
                    if "select_btn" in btn.objectName():
                        if btn.isEnabled():
                            btn.setStyleSheet(btn_style)
                        else:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    background: transparent;
                                    color: {s.accent_color};
                                    border: none;
                                    font-family: {s.ui_font};
                                    font-weight: bold;
                                }}
                            """)
                    elif "retry_btn" in btn.objectName():
                        btn.setStyleSheet(btn_style)

    def _refresh_review_styles(self):
        """刷新评审区域的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新推荐卡片
        if recommendation_card := self.content_widget.findChild(QFrame, "recommendation_card"):
            recommendation_card.setStyleSheet(f"""
                QFrame#recommendation_card {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.accent_color};
                    border-left: 4px solid {s.accent_color};
                    border-radius: {dp(2)}px;
                    padding: {dp(14)}px;
                }}
            """)

            # 更新推荐卡片内的标题
            for label in recommendation_card.findChildren(QLabel):
                if "rec_title" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(16)}px;
                        font-weight: bold;
                        color: {s.accent_color};
                    """)
                elif "rec_reason" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {s.serif_font};
                        font-size: {sp(14)}px;
                        color: {s.text_primary};
                        line-height: 1.6;
                    """)

        # 更新评审卡片样式
        for i in range(1, 10):
            card_name = f"eval_card_{i}"
            if eval_card := self.content_widget.findChild(QFrame, card_name):
                eval_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(2)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新评审卡片内的标题
                for label in eval_card.findChildren(QLabel):
                    if "eval_title" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.ui_font};
                            font-size: {sp(14)}px;
                            font-weight: bold;
                            color: {s.text_primary};
                        """)
                    elif "eval_badge" in label.objectName():
                        label.setStyleSheet(f"""
                            background: transparent;
                            color: {s.accent_color};
                            border: 1px solid {s.accent_color};
                            padding: {dp(2)}px {dp(8)}px;
                            border-radius: {dp(2)}px;
                            font-family: {s.ui_font};
                            font-size: {sp(11)}px;
                        """)
                    elif "pros_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.serif_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                            padding: {dp(4)}px 0;
                        """)
                    elif "cons_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.serif_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                            padding: {dp(4)}px 0;
                        """)

        # 更新重新评审按钮
        if reeval_btn := self.content_widget.findChild(QPushButton, "reeval_btn"):
            reeval_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {s.text_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {s.ui_font};
                }}
                QPushButton:hover {{
                    color: {s.accent_color};
                    border-color: {s.accent_color};
                }}
            """)

        # 更新开始评审按钮
        if evaluate_btn := self.content_widget.findChild(QPushButton, "evaluate_btn"):
            evaluate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {s.accent_color};
                    color: {s.button_text};
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {s.ui_font};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {s.text_primary};
                }}
            """)

    @handle_errors("加载章节")
    def loadChapter(self, chapter_number):
        """加载章节"""
        self.current_chapter = chapter_number

        if not self.project_id:
            return

        # 从API加载章节数据
        chapter_data = self.api_client.get_chapter(self.project_id, chapter_number)
        self.displayChapter(chapter_data)

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
        """创建章节内容widget"""
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

        # TabWidget：正文、版本、评审、摘要
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(theme_manager.tabs())

        # Tab 1: 正文 - 使用 ContentPanelBuilder
        content_tab = self._content_builder.create_content_tab(chapter_data)
        self.content_text = self._content_builder.content_text  # 保存引用用于主题切换
        self.tab_widget.addTab(content_tab, "正文")

        # Tab 2: 版本历史 - 使用 VersionPanelBuilder
        versions_tab = self._version_builder.create_versions_tab(chapter_data, self)
        self.tab_widget.addTab(versions_tab, "版本")

        # Tab 3: 评审 - 使用 ReviewPanelBuilder
        review_tab = self._review_builder.create_review_tab(chapter_data, self)
        self.tab_widget.addTab(review_tab, "评审")

        # Tab 4: 章节摘要（用于RAG上下文）- 使用 SummaryPanelBuilder
        summary_tab = self._summary_builder.create_summary_tab(chapter_data, self)
        self.tab_widget.addTab(summary_tab, "摘要")

        # Tab 5: 章节分析（结构化信息）- 使用 AnalysisPanelBuilder
        analysis_tab = self._analysis_builder.create_analysis_tab(chapter_data)
        self.tab_widget.addTab(analysis_tab, "分析")

        # Tab 6: 漫画提示词 - 使用 MangaPanelBuilder
        manga_data = self._prepareMangaData(chapter_data)
        manga_tab = self._manga_builder.create_manga_tab(manga_data, self)
        self.tab_widget.addTab(manga_tab, "漫画")

        layout.addWidget(self.tab_widget, stretch=1)

        return widget

    def saveContent(self):
        """保存章节内容"""
        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.saveContentRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示

    def applySuggestion(self, suggestion: dict):
        """
        应用修改建议 - 在正文中显示内联diff

        显示方式：
        - 原文：红色背景 + 删除线
        - 新文本：绿色背景
        - 浮动确认按钮

        Args:
            suggestion: 建议数据，包含 original_text, suggested_text, paragraph_index
        """
        if not self.content_text:
            return

        original_text = suggestion.get("original_text", "")
        suggested_text = suggestion.get("suggested_text", "")

        if not original_text or not suggested_text:
            return

        # 获取当前正文内容
        current_content = self.content_text.toPlainText()

        # 查找原文位置
        start_pos = current_content.find(original_text)
        if start_pos == -1:
            # 如果找不到完全匹配，尝试模糊匹配（去除首尾空白）
            trimmed_original = original_text.strip()
            start_pos = current_content.find(trimmed_original)
            if start_pos == -1:
                return
            original_text = trimmed_original

        # 切换到正文标签页
        if self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

        # 显示内联diff
        self._showInlineDiff(start_pos, original_text, suggested_text)

    def _showInlineDiff(self, start_pos: int, original_text: str, suggested_text: str):
        """
        在正文中显示内联diff

        Args:
            start_pos: 原文开始位置
            original_text: 原文
            suggested_text: 新文本
        """
        from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont

        if not self.content_text:
            return

        # 获取文本光标
        cursor = self.content_text.textCursor()

        # 1. 先选中原文并设置删除线+红色背景格式
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(original_text), QTextCursor.MoveMode.KeepAnchor)

        delete_format = QTextCharFormat()
        delete_format.setBackground(QColor("#FFCDD2"))  # 浅红色背景
        delete_format.setForeground(QColor("#B71C1C"))  # 深红色文字
        delete_format.setFontStrikeOut(True)  # 删除线

        cursor.mergeCharFormat(delete_format)

        # 2. 在原文后插入新文本（绿色高亮）
        cursor.setPosition(start_pos + len(original_text))

        add_format = QTextCharFormat()
        add_format.setBackground(QColor("#C8E6C9"))  # 浅绿色背景
        add_format.setForeground(QColor("#1B5E20"))  # 深绿色文字
        add_format.setFontStrikeOut(False)

        cursor.insertText(suggested_text, add_format)

        # 3. 保存待确认的修改信息
        pending_change = {
            "start_pos": start_pos,
            "original_text": original_text,
            "original_length": len(original_text),
            "suggested_text": suggested_text,
            "suggested_length": len(suggested_text),
        }

        if not hasattr(self, '_pending_changes'):
            self._pending_changes = []
        self._pending_changes.append(pending_change)

        # 4. 显示确认面板
        self._showConfirmPanel(pending_change, len(self._pending_changes) - 1)

        # 5. 跳转到修改位置 - 将光标定位到修改开始处并确保可见
        cursor.setPosition(start_pos)
        self.content_text.setTextCursor(cursor)
        self.content_text.ensureCursorVisible()

        # 额外滚动调整，确保修改内容在视口中间位置
        self._scrollToPosition(start_pos)

    def _scrollToPosition(self, position: int):
        """
        滚动到指定位置，使其在视口中间

        Args:
            position: 文本位置
        """
        if not self.content_text:
            return

        # 获取位置对应的矩形区域
        cursor = self.content_text.textCursor()
        cursor.setPosition(position)
        self.content_text.setTextCursor(cursor)

        # 获取光标位置的矩形
        cursor_rect = self.content_text.cursorRect(cursor)

        # 获取视口高度
        viewport_height = self.content_text.viewport().height()

        # 计算目标滚动位置（使修改内容在视口中上部）
        scrollbar = self.content_text.verticalScrollBar()
        target_scroll = scrollbar.value() + cursor_rect.top() - int(viewport_height * 0.3)

        # 确保不超出范围
        target_scroll = max(0, min(target_scroll, scrollbar.maximum()))

        scrollbar.setValue(target_scroll)

    def _showConfirmPanel(self, change: dict, change_index: int):
        """
        显示确认修改的浮动面板

        Args:
            change: 待确认的修改信息
            change_index: 修改索引
        """
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
        from PyQt6.QtCore import Qt

        # 如果已有确认面板，先移除
        if hasattr(self, '_confirm_panel') and self._confirm_panel:
            self._confirm_panel.deleteLater()

        # 创建确认面板
        self._confirm_panel = QFrame(self.content_text)
        self._confirm_panel.setObjectName("confirm_panel")
        self._confirm_panel.setStyleSheet(f"""
            QFrame#confirm_panel {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
            }}
        """)

        layout = QHBoxLayout(self._confirm_panel)
        layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        layout.setSpacing(dp(8))

        # 提示文字
        hint_label = QLabel("修改预览")
        hint_label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(hint_label)

        layout.addStretch()

        # 撤销按钮
        cancel_btn = QPushButton("撤销")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {theme_manager.ui_font()};
                font-size: {sp(12)}px;
                color: {theme_manager.ERROR};
                background-color: transparent;
                border: 1px solid {theme_manager.ERROR};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR}20;
            }}
        """)
        cancel_btn.clicked.connect(lambda: self._revertChange(change_index))
        layout.addWidget(cancel_btn)

        # 确认按钮
        confirm_btn = QPushButton("确认修改")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {theme_manager.ui_font()};
                font-size: {sp(12)}px;
                color: {theme_manager.BUTTON_TEXT};
                background-color: {theme_manager.SUCCESS};
                border: 1px solid {theme_manager.SUCCESS};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS}dd;
            }}
        """)
        confirm_btn.clicked.connect(lambda: self._confirmChange(change_index))
        layout.addWidget(confirm_btn)

        # 定位面板到编辑器顶部
        self._confirm_panel.setFixedWidth(dp(280))
        self._confirm_panel.move(
            self.content_text.width() - dp(290),
            dp(10)
        )
        self._confirm_panel.show()

    def _confirmChange(self, change_index: int):
        """
        确认修改 - 删除原文，保留新文本，移除高亮

        Args:
            change_index: 修改索引
        """
        from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

        if not hasattr(self, '_pending_changes') or change_index >= len(self._pending_changes):
            return

        change = self._pending_changes[change_index]
        start_pos = change["start_pos"]
        original_length = change["original_length"]
        suggested_length = change["suggested_length"]

        cursor = self.content_text.textCursor()

        # 1. 删除原文（带删除线的部分）
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + original_length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # 2. 移除新文本的高亮格式
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + suggested_length, QTextCursor.MoveMode.KeepAnchor)

        normal_format = QTextCharFormat()
        normal_format.setBackground(QColor("transparent"))
        normal_format.setForeground(QColor(theme_manager.TEXT_PRIMARY))
        normal_format.setFontStrikeOut(False)

        cursor.setCharFormat(normal_format)

        # 3. 清理
        self._pending_changes.pop(change_index)
        self._hideConfirmPanel()

        # 4. 更新后续修改的位置偏移
        offset = original_length  # 删除了原文，位置需要调整
        for i, c in enumerate(self._pending_changes):
            if c["start_pos"] > start_pos:
                c["start_pos"] -= offset

    def _revertChange(self, change_index: int):
        """
        撤销修改 - 删除新文本，恢复原文格式

        Args:
            change_index: 修改索引
        """
        from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

        if not hasattr(self, '_pending_changes') or change_index >= len(self._pending_changes):
            return

        change = self._pending_changes[change_index]
        start_pos = change["start_pos"]
        original_length = change["original_length"]
        suggested_length = change["suggested_length"]

        cursor = self.content_text.textCursor()

        # 1. 删除新文本（在原文之后）
        cursor.setPosition(start_pos + original_length)
        cursor.setPosition(start_pos + original_length + suggested_length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # 2. 恢复原文格式（移除删除线和红色背景）
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + original_length, QTextCursor.MoveMode.KeepAnchor)

        normal_format = QTextCharFormat()
        normal_format.setBackground(QColor("transparent"))
        normal_format.setForeground(QColor(theme_manager.TEXT_PRIMARY))
        normal_format.setFontStrikeOut(False)

        cursor.setCharFormat(normal_format)

        # 3. 清理
        self._pending_changes.pop(change_index)
        self._hideConfirmPanel()

        # 4. 更新后续修改的位置偏移
        offset = suggested_length  # 删除了新文本，位置需要调整
        for i, c in enumerate(self._pending_changes):
            if c["start_pos"] > start_pos:
                c["start_pos"] -= offset

    def _hideConfirmPanel(self):
        """隐藏确认面板"""
        if hasattr(self, '_confirm_panel') and self._confirm_panel:
            self._confirm_panel.deleteLater()
            self._confirm_panel = None

        # 如果还有其他待确认的修改，显示下一个
        if hasattr(self, '_pending_changes') and self._pending_changes:
            self._showConfirmPanel(self._pending_changes[0], 0)

    # ==================== 漫画面板相关方法 ====================

    def _prepareMangaData(self, chapter_data: dict) -> dict:
        """
        准备漫画面板数据

        Args:
            chapter_data: 章节数据

        Returns:
            漫画面板所需的数据字典
        """
        manga_data = {
            'has_manga_prompt': False,
            'scenes': [],
            'character_profiles': {},
            'style_guide': '',
        }

        # 尝试从API获取已保存的漫画提示词
        if self.project_id and self.current_chapter:
            try:
                result = self.api_client.get_manga_prompts(
                    self.project_id, self.current_chapter
                )
                if result:
                    manga_data['has_manga_prompt'] = True
                    manga_data['scenes'] = result.get('scenes', [])
                    manga_data['character_profiles'] = result.get('character_profiles', {})
                    manga_data['style_guide'] = result.get('style_guide', '')
            except Exception:
                # 如果获取失败，保持默认空状态
                pass

        return manga_data

    def _onGenerateMangaPrompt(self, style: str, scene_count: int):
        """
        生成漫画提示词回调

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            scene_count: 场景数量
        """
        from utils.async_worker import AsyncWorker
        from utils.message_service import MessageService

        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        def do_generate():
            return self.api_client.generate_manga_prompts(
                self.project_id,
                self.current_chapter,
                style=style,
                scene_count=scene_count,
            )

        def on_success(result):
            MessageService.show_success(self, "漫画提示词生成成功")
            # 重新加载章节以刷新漫画面板
            self.loadChapter(self.current_chapter)

        def on_error(error):
            MessageService.show_error(self, f"生成失败: {error}")

        # 开始异步生成（不阻塞UI显示加载信息）
        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._manga_worker = worker

    def _onCopyPrompt(self, prompt: str):
        """
        复制提示词到剪贴板

        Args:
            prompt: 要复制的提示词内容
        """
        from utils.message_service import MessageService

        if not prompt:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(prompt)
        MessageService.show_success(self, "已复制到剪贴板")

    def _onDeleteMangaPrompt(self):
        """删除漫画提示词回调"""
        from utils.async_worker import AsyncWorker
        from utils.message_service import MessageService

        if not self.project_id or not self.current_chapter:
            return

        if not MessageService.confirm(self, "确定要删除漫画提示词吗?", "此操作不可恢复"):
            return

        def do_delete():
            return self.api_client.delete_manga_prompts(
                self.project_id, self.current_chapter
            )

        def on_success(result):
            MessageService.show_success(self, "漫画提示词已删除")
            # 重新加载章节以刷新漫画面板
            self.loadChapter(self.current_chapter)

        def on_error(error):
            MessageService.show_error(self, f"删除失败: {error}")

        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        self._manga_delete_worker = worker

    def _onGenerateImage(self, scene_id: int, prompt: str, negative_prompt: str):
        """
        生成图片回调

        Args:
            scene_id: 场景ID
            prompt: 正面提示词
            negative_prompt: 负面提示词
        """
        from utils.async_worker import AsyncWorker
        from utils.message_service import MessageService

        if not self.project_id or not self.current_chapter:
            return

        MessageService.show_info(self, f"正在为场景 {scene_id} 生成图片...")

        def do_generate():
            return self.api_client.generate_scene_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                scene_id=scene_id,
                prompt=prompt,
            )

        def on_success(result):
            if result.get('success', False):
                image_url = result.get('image_url', '')
                MessageService.show_success(
                    self,
                    f"场景 {scene_id} 图片生成成功"
                )
            else:
                error_msg = result.get('error_message', '未知错误')
                MessageService.show_error(self, f"生成失败: {error_msg}")

        def on_error(error):
            MessageService.show_error(self, f"图片生成失败: {error}")

        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._image_gen_worker = worker
