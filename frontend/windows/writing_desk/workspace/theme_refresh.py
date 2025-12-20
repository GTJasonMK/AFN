"""
写作台主工作区 - 主题刷新 Mixin

包含所有主题样式刷新相关的方法。
"""

from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QTextEdit, QScrollArea, QTabWidget
)

from utils.dpi_utils import dp, sp
from utils.constants import VersionConstants


class ThemeRefreshMixin:
    """主题刷新相关方法的 Mixin"""

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
