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


class WDWorkspace(ThemeAwareFrame):
    """主工作区 - 章节内容与版本管理"""

    generateChapterRequested = pyqtSignal(int)  # chapter_number
    previewPromptRequested = pyqtSignal(int)  # chapter_number - 预览提示词
    saveContentRequested = pyqtSignal(int, str)  # chapter_number, content
    selectVersion = pyqtSignal(int)  # version_index
    evaluateChapter = pyqtSignal()  # 评审当前章节
    retryVersion = pyqtSignal(int)  # version_index
    editContent = pyqtSignal(str)  # new_content

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

        layout.addWidget(self.tab_widget, stretch=1)

        return widget

    def saveContent(self):
        """保存章节内容"""
        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.saveContentRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示
