"""
写作台主工作区 - 现代化设计

功能：章节内容展示、版本管理、章节编辑
"""

import json
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QStackedWidget, QScrollArea, QTextEdit, QTabWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from components.empty_state import EmptyStateWithIllustration
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from themes.modern_effects import ModernEffects
from api.client import ArborisAPIClient
from utils.error_handler import handle_errors
from utils.message_service import MessageService
from utils.formatters import count_chinese_characters, format_word_count
from utils.dpi_utils import dp, sp


class WDWorkspace(ThemeAwareFrame):
    """主工作区 - 章节内容与版本管理"""

    generateChapterRequested = pyqtSignal(int)  # chapter_number
    saveContentRequested = pyqtSignal(int, str)  # chapter_number, content
    selectVersion = pyqtSignal(int)  # version_index
    evaluateChapter = pyqtSignal()  # 评审当前章节
    retryVersion = pyqtSignal(int)  # version_index
    editContent = pyqtSignal(str)  # new_content

    def __init__(self, parent=None):
        self.api_client = ArborisAPIClient()
        self.current_chapter = None
        self.project_id = None
        self.current_chapter_data = None  # 保存当前章节数据用于主题切换时重建

        # 保存组件引用
        self.empty_state = None
        self.content_widget = None
        self.chapter_title = None
        self.tab_widget = None
        self.content_text = None
        self.generate_btn = None

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

        # 使用 theme_manager 的书香风格便捷方法
        bg_color = theme_manager.book_bg_primary()
        editor_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 更新章节标题卡片 - 简约风格
        if chapter_header := self.content_widget.findChild(QFrame, "chapter_header"):
            chapter_header.setStyleSheet(f"""
                QFrame#chapter_header {{
                    background-color: {bg_color};
                    border-bottom: 1px solid {border_color};
                    border-radius: 0px;
                    padding: {dp(12)}px;
                }}
            """)
            # 移除阴影
            chapter_header.setGraphicsEffect(None)

        # 更新章节标题文字
        if self.chapter_title:
            self.chapter_title.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(20)}px;
                font-weight: bold;
                color: {text_primary};
            """)

        # 更新章节元信息标签
        if meta_label := self.content_widget.findChild(QLabel, "chapter_meta_label"):
            meta_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                font-style: italic;
            """)

        # 更新生成按钮
        if self.generate_btn:
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid {highlight_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {ui_font};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)

        # 更新TabWidget
        if self.tab_widget:
            # 使用与详情页类似的Tab样式
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: none;
                    background: transparent;
                }}
                QTabBar::tab {{
                    background: transparent;
                    color: {text_secondary};
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {ui_font};
                    border-bottom: 2px solid transparent;
                }}
                QTabBar::tab:selected {{
                    color: {highlight_color};
                    border-bottom: 2px solid {highlight_color};
                    font-weight: bold;
                }}
                QTabBar::tab:hover {{
                    color: {text_primary};
                }}
            """)

        # 更新文本编辑器 - 纸张效果
        if self.content_text:
            self.content_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {editor_bg};
                    border: none;
                    padding: {dp(32)}px;
                    font-family: {serif_font};
                    font-size: {sp(16)}px;
                    color: {text_primary};
                    line-height: 1.8;
                    selection-background-color: {highlight_color};
                    selection-color: {theme_manager.BUTTON_TEXT};
                }}
                {theme_manager.scrollbar()}
            """)

        # 更新编辑器容器 - 去除玻璃态，改为边框
        if editor_container := self.content_widget.findChild(QFrame, "editor_container"):
            editor_container.setStyleSheet(f"""
                QFrame#editor_container {{
                    background-color: {editor_bg};
                    border: 1px solid {border_color};
                    border-radius: {dp(2)}px;
                }}
            """)

        # 更新工具栏样式
        if toolbar := self.content_widget.findChild(QFrame, "content_toolbar"):
            toolbar.setStyleSheet(f"""
                QFrame#content_toolbar {{
                    background-color: transparent;
                    border-bottom: 1px solid {border_color};
                    border-radius: 0;
                    padding: {dp(6)}px {dp(10)}px;
                }}
            """)

        # 更新字数统计标签
        if word_count_label := self.content_widget.findChild(QLabel, "word_count_label"):
            word_count_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_secondary};
            """)

        # 更新状态标签
        if status_label := self.content_widget.findChild(QLabel, "status_label"):
            status_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {highlight_color};
            """)

        # 更新保存按钮
        if save_btn := self.content_widget.findChild(QPushButton, "save_btn"):
            save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px {dp(12)}px;
                    font-family: {ui_font};
                }}
                QPushButton:hover {{
                    color: {highlight_color};
                    border-color: {highlight_color};
                }}
            """)

        # 更新滚动区域的样式
        for scroll_area in self.content_widget.findChildren(QScrollArea):
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {theme_manager.scrollbar()}
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

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        editor_bg = theme_manager.book_bg_secondary()

        # 更新说明卡片
        if info_card := self.content_widget.findChild(QFrame, "summary_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#summary_info_card {{
                    background-color: {theme_manager.INFO_BG};
                    border: 1px solid {theme_manager.INFO};
                    border-left: 4px solid {theme_manager.INFO};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新说明标题
        if info_title := self.content_widget.findChild(QLabel, "summary_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {theme_manager.text_info()};
            """)

        # 更新说明描述
        if info_desc := self.content_widget.findChild(QLabel, "summary_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
            """)

        # 更新摘要内容卡片
        if summary_card := self.content_widget.findChild(QFrame, "summary_content_card"):
            summary_card.setStyleSheet(f"""
                QFrame#summary_content_card {{
                    background-color: {editor_bg};
                    border: 1px solid {border_color};
                    border-radius: {dp(2)}px;
                }}
            """)

        # 更新摘要文本编辑器
        if summary_text := self.content_widget.findChild(QTextEdit, "summary_text_edit"):
            summary_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {editor_bg};
                    border: none;
                    padding: {dp(16)}px;
                    font-family: {serif_font};
                    font-size: {sp(15)}px;
                    color: {text_primary};
                    line-height: 1.8;
                }}
                {theme_manager.scrollbar()}
            """)

        # 更新字数统计标签
        if word_count := self.content_widget.findChild(QLabel, "summary_word_count"):
            word_count.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                padding: {dp(4)}px 0;
            """)

    def _refresh_analysis_styles(self):
        """刷新分析标签页的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        # 使用 theme_manager 的书香风格便捷方法
        card_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 更新滚动区域
        if scroll_area := self.content_widget.findChild(QScrollArea, "analysis_scroll_area"):
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                {theme_manager.scrollbar()}
            """)

        # 更新分析说明卡片
        if info_card := self.content_widget.findChild(QFrame, "analysis_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#analysis_info_card {{
                    background-color: {theme_manager.INFO_BG};
                    border: 1px solid {theme_manager.INFO};
                    border-left: 4px solid {theme_manager.INFO};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新分析说明标题
        if info_title := self.content_widget.findChild(QLabel, "analysis_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {theme_manager.text_info()};
            """)

        # 更新分析说明描述
        if info_desc := self.content_widget.findChild(QLabel, "analysis_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
            """)

        # 更新各个分区卡片
        section_names = ["summaries", "metadata", "character_states", "key_events", "foreshadowing"]
        for section_name in section_names:
            if section_card := self.content_widget.findChild(QFrame, f"analysis_section_{section_name}"):
                section_card.setStyleSheet(f"""
                    QFrame#analysis_section_{section_name} {{
                        background-color: {card_bg};
                        border: 1px solid {border_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新分区标题
                if title_label := section_card.findChild(QLabel, f"section_title_{section_name}"):
                    title_label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(14)}px;
                        font-weight: 600;
                        color: {text_primary};
                    """)

                # 更新分区图标
                if icon_label := section_card.findChild(QLabel, f"section_icon_{section_name}"):
                    icon_label.setStyleSheet(f"""
                        font-size: {sp(16)}px;
                        color: {highlight_color};
                    """)

        # 使用书香风格三级文字色
        text_tertiary = theme_manager.book_text_tertiary()

        # 更新所有子标签的样式
        for label in self.content_widget.findChildren(QLabel):
            obj_name = label.objectName()
            if obj_name.startswith("analysis_label_"):
                # 特殊处理语义标签 - 使用对应的语义文字色
                if obj_name == "analysis_label_planted":
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {theme_manager.text_warning()};
                    """)
                elif obj_name == "analysis_label_resolved":
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {theme_manager.text_success()};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name == "analysis_label_tensions":
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {theme_manager.text_error()};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name in ["analysis_label_tone", "analysis_label_timeline"]:
                    # 情感基调和时间标记的小标签使用三级文字色
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(11)}px;
                        color: {text_tertiary};
                    """)
                else:
                    # 其他标签使用次要文字色
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {text_secondary};
                    """)
            elif obj_name.startswith("analysis_text_"):
                # 特殊处理语义文字
                if obj_name == "analysis_text_tone":
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {theme_manager.text_warning()};
                    """)
                elif obj_name == "analysis_text_timeline":
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {theme_manager.text_info()};
                    """)
                else:
                    label.setStyleSheet(f"""
                        font-family: {serif_font};
                        font-size: {sp(13)}px;
                        color: {text_primary};
                        line-height: 1.6;
                    """)
            elif obj_name.startswith("analysis_highlight_"):
                # 高亮框：透明背景+彩色边框
                label.setStyleSheet(f"""
                    font-family: {serif_font};
                    font-size: {sp(14)}px;
                    color: {highlight_color};
                    font-weight: 500;
                    padding: {dp(10)}px;
                    background-color: transparent;
                    border: 1px solid {highlight_color};
                    border-left: 3px solid {highlight_color};
                    border-radius: {dp(4)}px;
                """)

        # 更新角色状态卡片
        for char_card in self.content_widget.findChildren(QFrame):
            if char_card.objectName().startswith("char_state_card_"):
                char_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {card_bg};
                        border: 1px solid {border_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(10)}px;
                    }}
                """)

        # 更新事件卡片
        for event_card in self.content_widget.findChildren(QFrame):
            if event_card.objectName().startswith("event_card_"):
                # 保持左边框颜色（根据重要性），只更新背景
                current_style = event_card.styleSheet()
                event_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {card_bg};
                        border-left: 3px solid {highlight_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(8)}px;
                    }}
                """)

        # 更新伏笔卡片
        for fs_card in self.content_widget.findChildren(QFrame):
            if fs_card.objectName().startswith("foreshadow_card_"):
                fs_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {theme_manager.WARNING}08;
                        border-left: 2px solid {theme_manager.WARNING};
                        border-radius: {dp(4)}px;
                        padding: {dp(8)}px;
                    }}
                """)

    def _refresh_version_cards_styles(self):
        """刷新版本卡片的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        # 使用 theme_manager 的书香风格便捷方法
        card_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 查找所有 QTabWidget，排除主TabWidget，应用简约Tab样式
        for tab_widget in self.content_widget.findChildren(QTabWidget):
            if tab_widget != self.tab_widget:
                tab_widget.setStyleSheet(f"""
                    QTabWidget::pane {{ border: none; background: transparent; }}
                    QTabBar::tab {{
                        background: transparent; color: {text_secondary};
                        padding: {dp(6)}px {dp(12)}px; font-family: {ui_font};
                        border-bottom: 2px solid transparent;
                    }}
                    QTabBar::tab:selected {{
                        color: {highlight_color}; border-bottom: 2px solid {highlight_color};
                    }}
                """)

        # 查找所有版本卡片并更新样式
        for i in range(10):
            card_name = f"version_card_{i}"
            if version_card := self.content_widget.findChild(QFrame, card_name):
                version_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {card_bg};
                        border: 1px solid {border_color};
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
                            font-family: {serif_font};
                            font-size: {sp(14)}px;
                            color: {text_primary};
                            line-height: 1.6;
                        }}
                        {theme_manager.scrollbar()}
                    """)

            # 更新版本信息栏
            info_bar_name = f"version_info_bar_{i}"
            if info_bar := self.content_widget.findChild(QFrame, info_bar_name):
                info_bar.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                        border-top: 1px solid {border_color};
                        border-radius: 0;
                        padding: {dp(8)}px {dp(12)}px;
                    }}
                """)

                # 更新信息栏内的标签
                for label in info_bar.findChildren(QLabel):
                    if "info_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {ui_font};
                            font-size: {sp(12)}px;
                            color: {text_secondary};
                        """)

                # 更新按钮样式 - 简约风
                btn_style = f"""
                    QPushButton {{
                        background: transparent;
                        color: {text_secondary};
                        border: 1px solid {border_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(4)}px {dp(8)}px;
                        font-family: {ui_font};
                        font-size: {sp(12)}px;
                    }}
                    QPushButton:hover {{
                        color: {highlight_color};
                        border-color: {highlight_color};
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
                                    color: {highlight_color};
                                    border: none;
                                    font-family: {ui_font};
                                    font-weight: bold;
                                }}
                            """)
                    elif "retry_btn" in btn.objectName():
                        btn.setStyleSheet(btn_style)

    def _refresh_review_styles(self):
        """刷新评审区域的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        # 使用 theme_manager 的书香风格便捷方法
        card_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 更新推荐卡片
        if recommendation_card := self.content_widget.findChild(QFrame, "recommendation_card"):
            recommendation_card.setStyleSheet(f"""
                QFrame#recommendation_card {{
                    background-color: {card_bg};
                    border: 1px solid {highlight_color};
                    border-left: 4px solid {highlight_color};
                    border-radius: {dp(2)}px;
                    padding: {dp(14)}px;
                }}
            """)

            # 更新推荐卡片内的标题
            for label in recommendation_card.findChildren(QLabel):
                if "rec_title" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {ui_font};
                        font-size: {sp(16)}px;
                        font-weight: bold;
                        color: {highlight_color};
                    """)
                elif "rec_reason" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {serif_font};
                        font-size: {sp(14)}px;
                        color: {text_primary};
                        line-height: 1.6;
                    """)

        # 更新评审卡片样式
        for i in range(1, 10):
            card_name = f"eval_card_{i}"
            if eval_card := self.content_widget.findChild(QFrame, card_name):
                # 检查是否为推荐版本
                current_style = eval_card.styleSheet()
                # 简化判断逻辑，推荐版本用highlight_color边框，否则用普通border
                # 这里简单重置所有为普通样式，如果需要区分可以在创建时打标记
                
                eval_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {card_bg};
                        border: 1px solid {border_color};
                        border-radius: {dp(2)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新评审卡片内的标题
                for label in eval_card.findChildren(QLabel):
                    if "eval_title" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {ui_font};
                            font-size: {sp(14)}px;
                            font-weight: bold;
                            color: {text_primary};
                        """)
                    elif "eval_badge" in label.objectName():
                        label.setStyleSheet(f"""
                            background: transparent;
                            color: {highlight_color};
                            border: 1px solid {highlight_color};
                            padding: {dp(2)}px {dp(8)}px;
                            border-radius: {dp(2)}px;
                            font-family: {ui_font};
                            font-size: {sp(11)}px;
                        """)
                    elif "pros_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {serif_font};
                            font-size: {sp(12)}px;
                            color: {text_secondary};
                            padding: {dp(4)}px 0;
                        """)
                    elif "cons_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {serif_font};
                            font-size: {sp(12)}px;
                            color: {text_secondary};
                            padding: {dp(4)}px 0;
                        """)

        # 更新重新评审按钮
        if reeval_btn := self.content_widget.findChild(QPushButton, "reeval_btn"):
            reeval_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {ui_font};
                }}
                QPushButton:hover {{
                    color: {highlight_color};
                    border-color: {highlight_color};
                }}
            """)

        # 更新开始评审按钮
        if evaluate_btn := self.content_widget.findChild(QPushButton, "evaluate_btn"):
            evaluate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {ui_font};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
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

        # 右侧：生成按钮 - 紧凑版
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
        header_layout.addWidget(self.generate_btn)

        layout.addWidget(header)

        # TabWidget：正文、版本、评审、摘要
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(theme_manager.tabs())

        # Tab 1: 正文
        content_tab = self.createContentTab(chapter_data)
        self.tab_widget.addTab(content_tab, "正文")

        # Tab 2: 版本历史
        versions_tab = self.createVersionsTab(chapter_data)
        self.tab_widget.addTab(versions_tab, "版本")

        # Tab 3: 评审
        review_tab = self.createReviewTab(chapter_data)
        self.tab_widget.addTab(review_tab, "评审")

        # Tab 4: 章节摘要（用于RAG上下文）
        summary_tab = self.createRealSummaryTab(chapter_data)
        self.tab_widget.addTab(summary_tab, "摘要")

        # Tab 5: 章节分析（结构化信息）
        analysis_tab = self.createAnalysisTab(chapter_data)
        self.tab_widget.addTab(analysis_tab, "分析")

        layout.addWidget(self.tab_widget, stretch=1)

        return widget

    def createContentTab(self, chapter_data):
        """创建正文标签页 - 现代化设计（内容优先）"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        container = QWidget()
        # 设置明确的颜色以避免系统默认
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 压缩边距
        layout.setSpacing(dp(10))  # 减少间距

        # 工具栏 - 紧凑版
        toolbar = QFrame()
        toolbar.setObjectName("content_toolbar")
        toolbar.setStyleSheet(f"""
            QFrame#content_toolbar {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(6)}px {dp(10)}px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setSpacing(dp(10))
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # 字数统计
        content = chapter_data.get('content', '')
        word_count = count_chinese_characters(content) if content else 0
        word_count_label = QLabel(f"字数：{format_word_count(word_count)}")
        word_count_label.setObjectName("word_count_label")
        word_count_label.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
            font-weight: 500;
        """)
        toolbar_layout.addWidget(word_count_label)

        # 状态提示
        if not content:
            status_label = QLabel("* 尚未生成")
            status_label.setObjectName("status_label")  # 添加objectName
            status_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(13)}px;
                color: {theme_manager.text_warning()};
            """)
            toolbar_layout.addWidget(status_label)

        toolbar_layout.addStretch()

        # 保存按钮
        save_btn = QPushButton("保存内容")
        save_btn.setObjectName("save_btn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(ButtonStyles.primary('SM'))
        save_btn.clicked.connect(self.saveContent)
        toolbar_layout.addWidget(save_btn)

        layout.addWidget(toolbar)

        # 章节内容编辑器 - 玻璃拟态效果（最大化内容区域）
        editor_container = QFrame()
        editor_container.setObjectName("editor_container")

        # 应用玻璃拟态效果 - 使用 theme_manager 的统一方法
        glass_bg = theme_manager.glassmorphism_bg(0.72)

        editor_container.setStyleSheet(f"""
            QFrame#editor_container {{
                background-color: {glass_bg};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(2)}px;
            }}
        """)

        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # 文本编辑器 - 最大化阅读/编辑体验
        self.content_text = QTextEdit()
        self.content_text.setPlainText(content if content else '暂无内容，请点击"生成章节"按钮')
        self.content_text.setReadOnly(False)

        # 简单的StyleSheet设置（学习其他组件的做法）
        self.content_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_manager.BG_CARD};
                border: none;
                padding: {dp(16)}px;
                font-family: {serif_font};
                font-size: {sp(15)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.8;
            }}
            {theme_manager.scrollbar()}
        """)
        editor_layout.addWidget(self.content_text)

        layout.addWidget(editor_container, stretch=1)

        return container

    def saveContent(self):
        """保存章节内容"""
        if self.current_chapter and self.content_text:
            content = self.content_text.toPlainText()
            self.saveContentRequested.emit(self.current_chapter, content)
            # 注意：成功消息由 main.py 的异步回调显示，此处不显示

    def createVersionsTab(self, chapter_data):
        """创建版本对比标签页 - 现代化设计"""
        versions = chapter_data.get('versions', [])
        selected_idx = chapter_data.get('selected_version')

        # 如果没有版本数据，使用专业空状态组件
        if not versions:
            return EmptyStateWithIllustration(
                illustration_char='📑',
                title='暂无版本',
                description='生成章节后，AI会创建3个候选版本供你选择\n请点击顶部的"生成章节"按钮',
                parent=self
            )

        # 创建版本对比容器（设置明确的颜色以避免系统默认）
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 压缩边距
        layout.setSpacing(dp(10))  # 减少间距

        # 版本TabWidget（移除了提示卡片，直接显示版本内容）
        version_tabs = QTabWidget()
        version_tabs.setStyleSheet(theme_manager.tabs())

        for idx, version_content in enumerate(versions):
            # 创建单个版本widget
            version_widget = self.createSingleVersionWidget(idx, version_content, selected_idx)

            # Tab标题
            tab_title = f"版本 {idx + 1}"
            if idx == selected_idx:
                tab_title += " ✓"

            version_tabs.addTab(version_widget, tab_title)

        layout.addWidget(version_tabs, stretch=1)
        return container

    def createSingleVersionWidget(self, version_index, content, selected_idx):
        """创建单个版本的widget - 精简设计"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        widget = QWidget()
        # 设置透明背景，不设置color避免固定值
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))  # 减少间距

        # 内容显示区 - 使用玻璃拟态卡片
        content_card = QFrame()
        content_card.setObjectName(f"version_card_{version_index}")

        # 使用 theme_manager 的统一玻璃态方法
        glass_bg = theme_manager.glassmorphism_bg(0.72)

        content_card.setStyleSheet(f"""
            QFrame#version_card_{version_index} {{
                background-color: {glass_bg};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(2)}px;
            }}
        """)

        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 文本显示（只读）
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)

        # 简单的StyleSheet设置（学习其他组件的做法）
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_manager.BG_CARD};
                border: none;
                padding: {dp(16)}px;
                font-family: {serif_font};
                font-size: {sp(15)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.8;
            }}
            {theme_manager.scrollbar()}
        """)
        content_layout.addWidget(text_edit)

        layout.addWidget(content_card, stretch=1)

        # 底部信息栏 - 紧凑版
        info_bar = QFrame()
        info_bar.setObjectName(f"version_info_bar_{version_index}")
        info_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(8)}px {dp(12)}px;
            }}
        """)

        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(8))

        # 字数统计
        word_count = count_chinese_characters(content)
        info_label = QLabel(f"{format_word_count(word_count)}")
        info_label.setObjectName(f"version_info_label_{version_index}")  # 添加objectName
        info_label.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        info_layout.addWidget(info_label)
        info_layout.addStretch()

        # 操作按钮
        if version_index == selected_idx:
            select_btn = QPushButton("已选择")
            select_btn.setObjectName(f"version_select_btn_{version_index}")  # 添加objectName
            select_btn.setEnabled(False)
            select_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {serif_font};
                    background: {theme_manager.SUCCESS};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {sp(12)}px;
                }}
            """)
        else:
            select_btn = QPushButton("选择")
            select_btn.setObjectName(f"version_select_btn_{version_index}")  # 添加objectName
            select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            select_btn.setStyleSheet(ButtonStyles.primary('SM'))
            select_btn.clicked.connect(lambda checked, idx=version_index: self.selectVersion.emit(idx))

        info_layout.addWidget(select_btn)

        # 重新生成按钮
        retry_btn = QPushButton("重新生成")
        retry_btn.setObjectName(f"version_retry_btn_{version_index}")  # 添加objectName
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.setStyleSheet(ButtonStyles.secondary('SM'))
        retry_btn.clicked.connect(lambda checked, idx=version_index: self.retryVersion.emit(idx))
        info_layout.addWidget(retry_btn)

        layout.addWidget(info_bar)

        return widget

    def createReviewTab(self, chapter_data):
        """创建评审结果标签页 - 现代化设计"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        evaluation_str = chapter_data.get('evaluation')

        # 如果没有评审数据，使用专业空状态组件
        if not evaluation_str:
            empty_widget = QWidget()
            # 设置明确的颜色以避免系统默认
            empty_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setContentsMargins(dp(32), dp(32), dp(32), dp(32))
            empty_layout.setSpacing(dp(24))

            # 空状态
            empty_state = EmptyStateWithIllustration(
                illustration_char='🤖',
                title='暂无评审结果',
                description='AI可以分析各版本优缺点并推荐最佳版本',
                parent=empty_widget
            )
            empty_layout.addWidget(empty_state)

            # 开始评审按钮
            evaluate_btn = QPushButton("开始评审")
            evaluate_btn.setObjectName("evaluate_btn")  # 添加objectName
            evaluate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            evaluate_btn.setStyleSheet(ButtonStyles.primary())
            evaluate_btn.clicked.connect(self.evaluateChapter.emit)
            evaluate_btn.setFixedWidth(dp(160))
            empty_layout.addWidget(evaluate_btn, alignment=Qt.AlignmentFlag.AlignCenter)

            return empty_widget

        # 解析评审JSON
        try:
            evaluation_data = json.loads(evaluation_str)
        except json.JSONDecodeError:
            error_widget = QLabel("评审数据格式错误")
            error_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_widget.setStyleSheet(f"color: {theme_manager.TEXT_SECONDARY}; padding: {dp(40)}px;")
            return error_widget

        # 创建评审结果展示容器
        container = QWidget()
        # 设置明确的颜色以避免系统默认
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 压缩边距
        layout.setSpacing(dp(12))  # 减少间距

        # AI推荐区域 - 紧凑版
        best_choice = evaluation_data.get('best_choice', 1)
        reason = evaluation_data.get('reason_for_choice', '暂无说明')

        recommendation_card = QFrame()
        recommendation_card.setObjectName("recommendation_card")

        # 使用渐变背景（比Aurora更简洁）
        gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)
        recommendation_card.setStyleSheet(f"""
            QFrame#recommendation_card {{
                background: {gradient};
                border-radius: {theme_manager.RADIUS_MD};
                border: none;
                padding: {dp(14)}px;
            }}
        """)

        rec_layout = QHBoxLayout(recommendation_card)
        rec_layout.setSpacing(dp(12))
        rec_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：推荐信息
        rec_info = QWidget()
        # 确保透明背景以显示父元素的渐变背景
        rec_info.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        rec_info_layout = QVBoxLayout(rec_info)
        rec_info_layout.setContentsMargins(0, 0, 0, 0)
        rec_info_layout.setSpacing(dp(4))

        rec_title = QLabel(f"AI推荐: 版本 {best_choice}")
        rec_title.setObjectName("rec_title")  # 添加objectName
        rec_title.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(15)}px;
            font-weight: 700;
            color: {theme_manager.BUTTON_TEXT};
        """)
        rec_info_layout.addWidget(rec_title)

        rec_reason = QLabel(reason)
        rec_reason.setObjectName("rec_reason")  # 添加objectName
        rec_reason.setWordWrap(True)
        rec_reason.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(12)}px;
            color: {theme_manager.BUTTON_TEXT};
            opacity: 0.9;
        """)
        rec_info_layout.addWidget(rec_reason)

        rec_layout.addWidget(rec_info, stretch=1)

        layout.addWidget(recommendation_card)

        # 版本评审详情
        evaluation_details = evaluation_data.get('evaluation', {})

        details_scroll = QScrollArea()
        details_scroll.setObjectName("details_scroll")  # 添加objectName
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        details_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {theme_manager.scrollbar()}
        """)

        details_container = QWidget()
        # 设置明确的颜色以避免系统默认
        details_container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        details_layout = QVBoxLayout(details_container)
        details_layout.setSpacing(dp(10))  # 减少间距

        for version_key in sorted(evaluation_details.keys()):
            version_num = version_key.replace('version', '')
            version_data = evaluation_details[version_key]

            version_card = self.createVersionEvaluationCard(
                int(version_num),
                version_data,
                int(version_num) == best_choice
            )
            details_layout.addWidget(version_card)

        details_scroll.setWidget(details_container)
        layout.addWidget(details_scroll, stretch=1)

        # 底部重新评审按钮
        reeval_btn = QPushButton("重新评审")
        reeval_btn.setObjectName("reeval_btn")  # 添加objectName
        reeval_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reeval_btn.setStyleSheet(ButtonStyles.secondary())
        reeval_btn.clicked.connect(self.evaluateChapter.emit)
        layout.addWidget(reeval_btn)

        return container

    def createVersionEvaluationCard(self, version_num, version_data, is_recommended):
        """创建单个版本的评审卡片 - 紧凑设计"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        card = QFrame()
        card.setObjectName(f"eval_card_{version_num}")

        # 根据是否推荐使用不同样式
        border_style = f"2px solid {theme_manager.PRIMARY}" if is_recommended else f"1px solid {theme_manager.BORDER_DEFAULT}"
        card.setStyleSheet(f"""
            QFrame#eval_card_{version_num} {{
                background-color: {theme_manager.BG_CARD};
                border: {border_style};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(dp(8))
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        title = QLabel(f"版本 {version_num}")
        title.setObjectName(f"eval_title_{version_num}")  # 添加objectName
        title.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(14)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)

        if is_recommended:
            badge = QLabel("AI推荐")
            badge.setObjectName(f"eval_badge_{version_num}")  # 添加objectName
            badge.setStyleSheet(f"""
                font-family: {serif_font};
                background: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(11)}px;
            """)
            header_layout.addWidget(badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 优点区域 - 紧凑版
        pros = version_data.get('pros', [])
        if pros:
            pros_text = " | ".join(pros[:2])  # 只显示前2个优点
            if len(pros) > 2:
                pros_text += f" (+{len(pros)-2})"
            pros_label = QLabel(f"+ {pros_text}")
            pros_label.setObjectName(f"pros_label_{version_num}")  # 添加objectName
            pros_label.setWordWrap(True)
            pros_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(12)}px;
                color: {theme_manager.text_success()};
                padding: {dp(4)}px {dp(8)}px;
                background-color: {theme_manager.SUCCESS_BG};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(pros_label)

        # 缺点区域 - 紧凑版
        cons = version_data.get('cons', [])
        if cons:
            cons_text = " | ".join(cons[:2])  # 只显示前2个缺点
            if len(cons) > 2:
                cons_text += f" (+{len(cons)-2})"
            cons_label = QLabel(f"- {cons_text}")
            cons_label.setObjectName(f"cons_label_{version_num}")  # 添加objectName
            cons_label.setWordWrap(True)
            cons_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(12)}px;
                color: {theme_manager.text_warning()};
                padding: {dp(4)}px {dp(8)}px;
                background-color: {theme_manager.WARNING_BG};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(cons_label)

        return card

    def createRealSummaryTab(self, chapter_data):
        """创建章节摘要标签页 - 用于RAG上下文优化"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        real_summary = chapter_data.get('real_summary', '')

        # 如果没有摘要数据，显示空状态
        if not real_summary:
            empty_widget = QWidget()
            empty_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setContentsMargins(dp(32), dp(32), dp(32), dp(32))
            empty_layout.setSpacing(dp(24))

            # 空状态
            empty_state = EmptyStateWithIllustration(
                illustration_char='S',
                title='暂无章节摘要',
                description='选择版本后系统会自动生成章节摘要，用于优化后续章节的生成效果',
                parent=empty_widget
            )
            empty_layout.addWidget(empty_state)

            return empty_widget

        # 创建摘要展示容器
        container = QWidget()
        container.setObjectName("summary_container")
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 说明卡片
        info_card = QFrame()
        info_card.setObjectName("summary_info_card")
        info_card.setStyleSheet(f"""
            QFrame#summary_info_card {{
                background-color: {theme_manager.INFO_BG};
                border: 1px solid {theme_manager.INFO};
                border-left: 4px solid {theme_manager.INFO};
                border-radius: {dp(4)}px;
                padding: {dp(12)}px;
            }}
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        info_layout.setSpacing(dp(4))

        info_title = QLabel("RAG上下文摘要")
        info_title.setObjectName("summary_info_title")
        info_title.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.text_info()};
        """)
        info_layout.addWidget(info_title)

        info_desc = QLabel("此摘要由AI根据章节内容自动生成，用于为后续章节生成提供上下文参考，确保故事连贯性和设定一致性。")
        info_desc.setObjectName("summary_info_desc")
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        info_layout.addWidget(info_desc)

        layout.addWidget(info_card)

        # 摘要内容卡片
        summary_card = QFrame()
        summary_card.setObjectName("summary_content_card")

        # 使用玻璃拟态效果
        glass_bg = theme_manager.glassmorphism_bg(0.72)
        summary_card.setStyleSheet(f"""
            QFrame#summary_content_card {{
                background-color: {glass_bg};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(2)}px;
            }}
        """)

        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(0, 0, 0, 0)

        # 摘要文本显示（只读）
        summary_text = QTextEdit()
        summary_text.setObjectName("summary_text_edit")
        summary_text.setPlainText(real_summary)
        summary_text.setReadOnly(True)
        summary_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_manager.BG_CARD};
                border: none;
                padding: {dp(16)}px;
                font-family: {serif_font};
                font-size: {sp(15)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.8;
            }}
            {theme_manager.scrollbar()}
        """)
        summary_layout.addWidget(summary_text)

        layout.addWidget(summary_card, stretch=1)

        # 底部字数统计
        word_count = count_chinese_characters(real_summary)
        word_count_label = QLabel(f"摘要字数: {format_word_count(word_count)}")
        word_count_label.setObjectName("summary_word_count")
        word_count_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding: {dp(4)}px 0;
        """)
        layout.addWidget(word_count_label)

        return container

    def createAnalysisTab(self, chapter_data):
        """创建章节分析标签页 - 展示结构化分析数据"""
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        analysis_data = chapter_data.get('analysis_data')

        # 如果没有分析数据，显示空状态
        if not analysis_data:
            empty_widget = QWidget()
            empty_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setContentsMargins(dp(32), dp(32), dp(32), dp(32))
            empty_layout.setSpacing(dp(24))

            empty_state = EmptyStateWithIllustration(
                illustration_char='A',
                title='暂无章节分析',
                description='选择版本后系统会自动分析章节内容，提取角色状态、伏笔、关键事件等结构化信息',
                parent=empty_widget
            )
            empty_layout.addWidget(empty_state)

            return empty_widget

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("analysis_scroll_area")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        # 创建内容容器
        container = QWidget()
        container.setObjectName("analysis_container")
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(16))

        # 说明卡片
        info_card = self._create_analysis_info_card(ui_font)
        layout.addWidget(info_card)

        # 1. 分级摘要区域
        summaries = analysis_data.get('summaries')
        if summaries:
            summaries_section = self._create_summaries_section(summaries, ui_font, serif_font)
            layout.addWidget(summaries_section)

        # 2. 元数据区域（角色、地点、物品、标签等）
        metadata = analysis_data.get('metadata')
        if metadata:
            metadata_section = self._create_metadata_section(metadata, ui_font)
            layout.addWidget(metadata_section)

        # 3. 角色状态区域
        character_states = analysis_data.get('character_states')
        if character_states:
            char_section = self._create_character_states_section(character_states, ui_font, serif_font)
            layout.addWidget(char_section)

        # 4. 关键事件区域
        key_events = analysis_data.get('key_events')
        if key_events:
            events_section = self._create_key_events_section(key_events, ui_font, serif_font)
            layout.addWidget(events_section)

        # 5. 伏笔追踪区域
        foreshadowing = analysis_data.get('foreshadowing')
        if foreshadowing:
            foreshadow_section = self._create_foreshadowing_section(foreshadowing, ui_font, serif_font)
            layout.addWidget(foreshadow_section)

        # 添加底部弹性空间
        layout.addStretch()

        scroll_area.setWidget(container)
        return scroll_area

    def _create_analysis_info_card(self, ui_font):
        """创建分析说明卡片"""
        # 使用书香风格
        text_secondary = theme_manager.book_text_secondary()

        info_card = QFrame()
        info_card.setObjectName("analysis_info_card")
        info_card.setStyleSheet(f"""
            QFrame#analysis_info_card {{
                background-color: {theme_manager.INFO_BG};
                border: 1px solid {theme_manager.INFO};
                border-left: 4px solid {theme_manager.INFO};
                border-radius: {dp(4)}px;
                padding: {dp(12)}px;
            }}
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        info_layout.setSpacing(dp(4))

        info_title = QLabel("章节深度分析")
        info_title.setObjectName("analysis_info_title")
        info_title.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.text_info()};
        """)
        info_layout.addWidget(info_title)

        info_desc = QLabel("AI自动提取的结构化信息，包括角色状态、伏笔追踪、关键事件等，用于确保后续章节的连贯性。")
        info_desc.setObjectName("analysis_info_desc")
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {text_secondary};
        """)
        info_layout.addWidget(info_desc)

        return info_card

    def _create_section_card(self, title, icon_char, ui_font, section_id=None):
        """创建通用分区卡片"""
        # 使用section_id作为objectName，避免中文标题问题
        card_id = section_id or title.lower().replace(" ", "_")

        card = QFrame()
        card.setObjectName(f"analysis_section_{card_id}")

        # 使用书香风格
        card_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()
        card.setStyleSheet(f"""
            QFrame#analysis_section_{card_id} {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon_label = QLabel(icon_char)
        icon_label.setObjectName(f"section_icon_{card_id}")
        icon_label.setStyleSheet(f"""
            font-size: {sp(16)}px;
            color: {theme_manager.book_accent_color()};
        """)
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName(f"section_title_{card_id}")
        title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: 600;
            color: {theme_manager.book_text_primary()};
        """)
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)

        return card, layout

    def _create_tag_widget(self, text, tag_type="default", ui_font=None):
        """创建标签/徽章组件

        Args:
            text: 标签文本
            tag_type: 标签类型 (default/character/location/item/keyword/tag)
            ui_font: 字体
        """
        tag = QLabel(text)

        # 使用书香风格 - 透明背景+彩色边框，确保文字清晰可见
        border_color = theme_manager.book_border_color()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()

        # 根据类型选择边框颜色，文字统一使用 text_secondary 确保可读性
        type_colors = {
            "character": theme_manager.SUCCESS,      # 角色 - 绿色边框
            "location": theme_manager.INFO,          # 地点 - 蓝色边框
            "item": theme_manager.WARNING,           # 物品 - 橙色边框
            "keyword": highlight_color,              # 关键词 - 强调色边框
            "tag": theme_manager.PRIMARY,            # 标签 - 主色边框
            "default": border_color,                 # 默认 - 普通边框
        }

        tag_border = type_colors.get(tag_type, border_color)

        tag.setStyleSheet(f"""
            font-family: {ui_font or theme_manager.ui_font()};
            font-size: {sp(12)}px;
            color: {text_secondary};
            background-color: transparent;
            border: 1px solid {tag_border};
            border-radius: {dp(4)}px;
            padding: {dp(4)}px {dp(8)}px;
        """)
        return tag

    def _create_flow_layout(self, items, tag_type="default", ui_font=None):
        """创建流式布局的标签组

        Args:
            items: 标签文本列表
            tag_type: 标签类型 (character/location/item/keyword/tag/default)
            ui_font: 字体
        """
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(6))

        for item in items[:10]:  # 限制显示数量
            tag = self._create_tag_widget(str(item), tag_type, ui_font)
            layout.addWidget(tag)

        if len(items) > 10:
            more_tag = self._create_tag_widget(f"+{len(items) - 10}", "default", ui_font)
            layout.addWidget(more_tag)

        layout.addStretch()
        return container

    def _create_summaries_section(self, summaries, ui_font, serif_font):
        """创建分级摘要区域"""
        card, layout = self._create_section_card("分级摘要", "[S]", ui_font, section_id="summaries")

        # 使用书香风格
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()

        # 一句话概括
        one_line = summaries.get('one_line', '')
        if one_line:
            one_line_label = QLabel("一句话概括")
            one_line_label.setObjectName("analysis_label_one_line")
            one_line_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
            """)
            layout.addWidget(one_line_label)

            # 高亮框：使用透明背景+彩色边框，文字使用强调色
            one_line_text = QLabel(one_line)
            one_line_text.setObjectName("analysis_highlight_one_line")
            one_line_text.setWordWrap(True)
            one_line_text.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(14)}px;
                color: {highlight_color};
                font-weight: 500;
                padding: {dp(10)}px;
                background-color: transparent;
                border: 1px solid {highlight_color};
                border-left: 3px solid {highlight_color};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(one_line_text)

        # 压缩摘要
        compressed = summaries.get('compressed', '')
        if compressed:
            compressed_label = QLabel("压缩摘要")
            compressed_label.setObjectName("analysis_label_compressed")
            compressed_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
                margin-top: {dp(8)}px;
            """)
            layout.addWidget(compressed_label)

            compressed_text = QLabel(compressed)
            compressed_text.setObjectName("analysis_text_compressed")
            compressed_text.setWordWrap(True)
            compressed_text.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                line-height: 1.6;
            """)
            layout.addWidget(compressed_text)

        # 关键词
        keywords = summaries.get('keywords', [])
        if keywords:
            keywords_label = QLabel("关键词")
            keywords_label.setObjectName("analysis_label_keywords")
            keywords_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
                margin-top: {dp(8)}px;
            """)
            layout.addWidget(keywords_label)

            keywords_flow = self._create_flow_layout(keywords, "keyword", ui_font)
            layout.addWidget(keywords_flow)

        return card

    def _create_metadata_section(self, metadata, ui_font):
        """创建元数据区域"""
        card, layout = self._create_section_card("章节元素", "[M]", ui_font, section_id="metadata")

        # 使用书香风格
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.book_text_tertiary()  # 使用书香风格三级文字色
        highlight_color = theme_manager.book_accent_color()

        # 情感基调和时间标记（横向排列）
        meta_row = QHBoxLayout()
        meta_row.setSpacing(dp(16))

        tone = metadata.get('tone', '')
        if tone:
            tone_widget = QWidget()
            tone_widget.setStyleSheet("background-color: transparent;")
            tone_layout = QVBoxLayout(tone_widget)
            tone_layout.setContentsMargins(0, 0, 0, 0)
            tone_layout.setSpacing(dp(4))

            tone_label = QLabel("情感基调")
            tone_label.setObjectName("analysis_label_tone")
            tone_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {text_tertiary};
            """)
            tone_layout.addWidget(tone_label)

            tone_value = QLabel(tone)
            tone_value.setObjectName("analysis_text_tone")
            tone_value.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {theme_manager.text_warning()};
            """)
            tone_layout.addWidget(tone_value)

            meta_row.addWidget(tone_widget)

        timeline = metadata.get('timeline_marker', '')
        if timeline:
            timeline_widget = QWidget()
            timeline_widget.setStyleSheet("background-color: transparent;")
            timeline_layout = QVBoxLayout(timeline_widget)
            timeline_layout.setContentsMargins(0, 0, 0, 0)
            timeline_layout.setSpacing(dp(4))

            timeline_label = QLabel("时间标记")
            timeline_label.setObjectName("analysis_label_timeline")
            timeline_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {text_tertiary};
            """)
            timeline_layout.addWidget(timeline_label)

            timeline_value = QLabel(timeline)
            timeline_value.setObjectName("analysis_text_timeline")
            timeline_value.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {theme_manager.text_info()};
            """)
            timeline_layout.addWidget(timeline_value)

            meta_row.addWidget(timeline_widget)

        meta_row.addStretch()
        if tone or timeline:
            layout.addLayout(meta_row)

        # 出场角色
        characters = metadata.get('characters', [])
        if characters:
            char_label = QLabel("出场角色")
            char_label.setObjectName("analysis_label_characters")
            char_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
            """)
            layout.addWidget(char_label)

            char_flow = self._create_flow_layout(characters, "character", ui_font)
            layout.addWidget(char_flow)

        # 场景地点
        locations = metadata.get('locations', [])
        if locations:
            loc_label = QLabel("场景地点")
            loc_label.setObjectName("analysis_label_locations")
            loc_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
                margin-top: {dp(8)}px;
            """)
            layout.addWidget(loc_label)

            loc_flow = self._create_flow_layout(locations, "location", ui_font)
            layout.addWidget(loc_flow)

        # 重要物品
        items = metadata.get('items', [])
        if items:
            items_label = QLabel("重要物品")
            items_label.setObjectName("analysis_label_items")
            items_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
                margin-top: {dp(8)}px;
            """)
            layout.addWidget(items_label)

            items_flow = self._create_flow_layout(items, "item", ui_font)
            layout.addWidget(items_flow)

        # 章节标签
        tags = metadata.get('tags', [])
        if tags:
            tags_label = QLabel("章节类型")
            tags_label.setObjectName("analysis_label_tags")
            tags_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {text_secondary};
                margin-top: {dp(8)}px;
            """)
            layout.addWidget(tags_label)

            tags_flow = self._create_flow_layout(tags, "tag", ui_font)
            layout.addWidget(tags_flow)

        return card

    def _create_character_states_section(self, character_states, ui_font, serif_font):
        """创建角色状态区域"""
        card, layout = self._create_section_card("角色状态快照", "[C]", ui_font, section_id="character_states")

        # 使用书香风格
        card_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        highlight_color = theme_manager.book_accent_color()

        char_index = 0
        for char_name, state in character_states.items():
            if not isinstance(state, dict):
                continue

            # 角色卡片
            char_card = QFrame()
            char_card.setObjectName(f"char_state_card_{char_index}")
            char_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border: 1px solid {border_color};
                    border-radius: {dp(6)}px;
                    padding: {dp(10)}px;
                }}
            """)
            char_layout = QVBoxLayout(char_card)
            char_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
            char_layout.setSpacing(dp(6))

            # 角色名
            name_label = QLabel(char_name)
            name_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: 700;
                color: {highlight_color};
            """)
            char_layout.addWidget(name_label)

            # 位置和状态
            details = []
            if state.get('location'):
                details.append(f"位置: {state['location']}")
            if state.get('status'):
                details.append(f"状态: {state['status']}")

            if details:
                details_label = QLabel(" | ".join(details))
                details_label.setWordWrap(True)
                details_label.setStyleSheet(f"""
                    font-family: {serif_font};
                    font-size: {sp(12)}px;
                    color: {text_secondary};
                """)
                char_layout.addWidget(details_label)

            # 变化
            changes = state.get('changes', [])
            if changes:
                changes_label = QLabel("本章变化:")
                changes_label.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {theme_manager.book_text_tertiary()};
                    margin-top: {dp(4)}px;
                """)
                char_layout.addWidget(changes_label)

                for change in changes[:3]:
                    change_item = QLabel(f"  - {change}")
                    change_item.setWordWrap(True)
                    change_item.setStyleSheet(f"""
                        font-family: {serif_font};
                        font-size: {sp(12)}px;
                        color: {theme_manager.text_success()};
                    """)
                    char_layout.addWidget(change_item)

            layout.addWidget(char_card)
            char_index += 1

        return card

    def _create_key_events_section(self, key_events, ui_font, serif_font):
        """创建关键事件区域"""
        card, layout = self._create_section_card("关键事件", "[E]", ui_font, section_id="key_events")

        # 使用书香风格
        card_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_tertiary = theme_manager.book_text_tertiary()
        highlight_color = theme_manager.book_accent_color()

        # 事件类型映射
        event_type_names = {
            'battle': '战斗',
            'revelation': '揭示',
            'relationship': '关系',
            'discovery': '发现',
            'decision': '决策',
            'death': '死亡',
            'arrival': '到来',
            'departure': '离开',
        }

        # 边框颜色映射（保持鲜艳）
        importance_border_colors = {
            'high': theme_manager.ERROR,
            'medium': theme_manager.WARNING,
            'low': theme_manager.BORDER_DEFAULT,
        }

        # 文字颜色映射（确保对比度）
        importance_text_colors = {
            'high': theme_manager.text_error(),
            'medium': theme_manager.text_warning(),
            'low': text_tertiary,
        }

        event_index = 0
        for event in key_events[:5]:  # 限制显示数量
            if not isinstance(event, dict):
                continue

            importance = event.get('importance', 'medium')
            event_card = QFrame()
            event_card.setObjectName(f"event_card_{event_index}")
            event_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border-left: 3px solid {importance_border_colors.get(importance, theme_manager.WARNING)};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)
            event_layout = QVBoxLayout(event_card)
            event_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            event_layout.setSpacing(dp(4))

            # 事件类型和重要性
            header_row = QHBoxLayout()
            header_row.setSpacing(dp(8))

            event_type = event.get('type', '')
            type_text = event_type_names.get(event_type, event_type)
            type_label = QLabel(f"[{type_text}]")
            type_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(11)}px;
                font-weight: 600;
                color: {highlight_color};
            """)
            header_row.addWidget(type_label)

            imp_text = {'high': '重要', 'medium': '一般', 'low': '次要'}.get(importance, importance)
            imp_label = QLabel(imp_text)
            imp_text_color = importance_text_colors.get(importance, text_tertiary)
            imp_border_color = importance_border_colors.get(importance, theme_manager.BORDER_DEFAULT)
            imp_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(10)}px;
                color: {imp_text_color};
                background-color: {imp_border_color}15;
                border-radius: {dp(2)}px;
                padding: {dp(2)}px {dp(6)}px;
            """)
            header_row.addWidget(imp_label)
            header_row.addStretch()

            event_layout.addLayout(header_row)

            # 事件描述
            description = event.get('description', '')
            if description:
                desc_label = QLabel(description)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(f"""
                    font-family: {serif_font};
                    font-size: {sp(13)}px;
                    color: {text_primary};
                """)
                event_layout.addWidget(desc_label)

            # 涉及角色
            involved = event.get('involved_characters', [])
            if involved:
                involved_text = "涉及: " + ", ".join(involved[:4])
                if len(involved) > 4:
                    involved_text += f" 等{len(involved)}人"
                involved_label = QLabel(involved_text)
                involved_label.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {text_tertiary};
                """)
                event_layout.addWidget(involved_label)

            layout.addWidget(event_card)
            event_index += 1

        return card

    def _create_foreshadowing_section(self, foreshadowing, ui_font, serif_font):
        """创建伏笔追踪区域"""
        card, layout = self._create_section_card("伏笔追踪", "[F]", ui_font, section_id="foreshadowing")

        # 使用书香风格
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()

        # 埋下的伏笔
        planted = foreshadowing.get('planted', [])
        if planted:
            planted_label = QLabel("本章埋下的伏笔")
            planted_label.setObjectName("analysis_label_planted")
            planted_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {theme_manager.text_warning()};
            """)
            layout.addWidget(planted_label)

            fs_index = 0
            for item in planted[:5]:
                if not isinstance(item, dict):
                    continue

                foreshadow_card = QFrame()
                foreshadow_card.setObjectName(f"foreshadow_card_{fs_index}")
                priority = item.get('priority', 'medium')
                # 边框颜色映射 - 浅色主题使用更深的颜色提高对比度
                priority_border_colors = {
                    'high': theme_manager.ERROR_DARK if theme_manager.is_light_mode() else theme_manager.ERROR,
                    'medium': theme_manager.WARNING_DARK if theme_manager.is_light_mode() else theme_manager.WARNING,
                    'low': theme_manager.BORDER_DARK if theme_manager.is_light_mode() else theme_manager.BORDER_DEFAULT,
                }
                # 使用WARNING_BG作为背景色，在浅色主题下更加醒目
                foreshadow_bg = theme_manager.WARNING_BG if theme_manager.is_light_mode() else f"{theme_manager.WARNING}15"
                foreshadow_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {foreshadow_bg};
                        border-left: 3px solid {priority_border_colors.get(priority, theme_manager.WARNING_DARK)};
                        border-radius: {dp(4)}px;
                        padding: {dp(8)}px;
                    }}
                """)
                fs_layout = QVBoxLayout(foreshadow_card)
                fs_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
                fs_layout.setSpacing(dp(4))

                # 描述
                desc = item.get('description', '')
                if desc:
                    desc_label = QLabel(desc)
                    desc_label.setWordWrap(True)
                    desc_label.setStyleSheet(f"""
                        font-family: {serif_font};
                        font-size: {sp(13)}px;
                        color: {text_primary};
                    """)
                    fs_layout.addWidget(desc_label)

                # 原文引用
                original = item.get('original_text', '')
                if original:
                    orig_label = QLabel(f'"{original}"')
                    orig_label.setWordWrap(True)
                    orig_label.setStyleSheet(f"""
                        font-family: {serif_font};
                        font-size: {sp(12)}px;
                        font-style: italic;
                        color: {text_secondary};
                    """)
                    fs_layout.addWidget(orig_label)

                layout.addWidget(foreshadow_card)
                fs_index += 1

        # 回收的伏笔
        resolved = foreshadowing.get('resolved', [])
        if resolved:
            resolved_label = QLabel("本章回收的伏笔")
            resolved_label.setObjectName("analysis_label_resolved")
            resolved_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {theme_manager.text_success()};
                margin-top: {dp(12)}px;
            """)
            layout.addWidget(resolved_label)

            for item in resolved[:3]:
                if isinstance(item, dict):
                    resolution = item.get('resolution', str(item))
                else:
                    resolution = str(item)

                res_label = QLabel(f"  - {resolution}")
                res_label.setWordWrap(True)
                res_label.setStyleSheet(f"""
                    font-family: {serif_font};
                    font-size: {sp(12)}px;
                    color: {theme_manager.text_success()};
                """)
                layout.addWidget(res_label)

        # 未解决的悬念
        tensions = foreshadowing.get('tensions', [])
        if tensions:
            tensions_label = QLabel("未解决的悬念")
            tensions_label.setObjectName("analysis_label_tensions")
            tensions_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {theme_manager.text_error()};
                margin-top: {dp(12)}px;
            """)
            layout.addWidget(tensions_label)

            for tension in tensions[:3]:
                tension_label = QLabel(f"  ? {tension}")
                tension_label.setWordWrap(True)
                tension_label.setStyleSheet(f"""
                    font-family: {serif_font};
                    font-size: {sp(12)}px;
                    color: {theme_manager.text_error()};
                """)
                layout.addWidget(tension_label)

        return card
