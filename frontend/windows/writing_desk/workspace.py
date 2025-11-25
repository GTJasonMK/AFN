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

        # 如果有显示中的章节内容，重新应用样式
        if self.current_chapter_data and self.content_widget:
            self._refresh_content_styles()

    def setProjectId(self, project_id):
        """设置项目ID"""
        self.project_id = project_id

    def _refresh_content_styles(self):
        """刷新内容区域的主题样式（主题切换时调用）"""
        if not self.content_widget:
            return

        # 获取当前主题的颜色值
        border_color = theme_manager.BORDER_LIGHT
        is_dark = theme_manager.is_dark_mode()

        # 更新章节标题卡片
        if chapter_header := self.content_widget.findChild(QFrame, "chapter_header"):
            gradient = ModernEffects.linear_gradient(
                theme_manager.PRIMARY_GRADIENT,
                135
            )
            # 根据主题调整阴影强度
            shadow_color = "rgba(0, 0, 0, 30)" if not theme_manager.is_dark_mode() else "rgba(0, 0, 0, 60)"
            chapter_header.setStyleSheet(f"""
                QFrame#chapter_header {{
                    background: {gradient};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: {dp(12)}px;
                }}
            """)

        # 更新章节标题文字
        if self.chapter_title:
            self.chapter_title.setStyleSheet(f"""
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 更新章节元信息标签
        if meta_label := self.content_widget.findChild(QLabel, "chapter_meta_label"):
            meta_label.setStyleSheet(f"""
                font-size: {sp(12)}px;
                color: {theme_manager.BUTTON_TEXT};
                opacity: 0.85;
            """)

        # 更新生成按钮 - 使用主题变量而非硬编码
        if self.generate_btn:
            # 根据主题选择按钮颜色（深色主题用更亮的颜色）
            btn_bg = "rgba(255, 255, 255, 0.2)" if not theme_manager.is_dark_mode() else "rgba(255, 255, 255, 0.15)"
            btn_border = "rgba(255, 255, 255, 0.3)" if not theme_manager.is_dark_mode() else "rgba(255, 255, 255, 0.25)"
            btn_hover_bg = "rgba(255, 255, 255, 0.3)" if not theme_manager.is_dark_mode() else "rgba(255, 255, 255, 0.25)"
            btn_hover_border = "rgba(255, 255, 255, 0.5)" if not theme_manager.is_dark_mode() else "rgba(255, 255, 255, 0.4)"

            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid {btn_border};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover_bg};
                    border-color: {btn_hover_border};
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
            """)

        # 更新TabWidget
        if self.tab_widget:
            self.tab_widget.setStyleSheet(theme_manager.tabs())

        # 更新文本编辑器（增强版本，包含选中颜色和滚动条）
        if self.content_text:
            # 简单的StyleSheet设置（学习其他组件的做法）
            self.content_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {theme_manager.BG_CARD};
                    border: none;
                    padding: {dp(16)}px;
                    font-size: {sp(15)}px;
                    color: {theme_manager.TEXT_PRIMARY};
                    line-height: 1.8;
                }}
                {theme_manager.scrollbar()}
            """)

        # 更新编辑器容器的玻璃拟态效果
        if editor_container := self.content_widget.findChild(QFrame, "editor_container"):
            # 完全手动设置样式
            if is_dark:
                bg_color = "rgba(26, 31, 53, 0.65)"
            else:
                bg_color = "rgba(255, 255, 255, 0.72)"

            editor_container.setStyleSheet(f"""
                QFrame#editor_container {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: {dp(2)}px;
                }}
            """)

        # 更新工具栏样式
        if toolbar := self.content_widget.findChild(QFrame, "content_toolbar"):
            toolbar.setStyleSheet(f"""
                QFrame#content_toolbar {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: {dp(6)}px {dp(10)}px;
                }}
            """)

        # 更新字数统计标签
        if word_count_label := self.content_widget.findChild(QLabel, "word_count_label"):
            word_count_label.setStyleSheet(f"""
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                font-weight: 500;
            """)

        # 更新状态标签（如果存在）
        if status_label := self.content_widget.findChild(QLabel, "status_label"):
            status_label.setStyleSheet(f"""
                font-size: {sp(13)}px;
                color: {theme_manager.WARNING};
            """)

        # 更新保存按钮
        if save_btn := self.content_widget.findChild(QPushButton, "save_btn"):
            save_btn.setStyleSheet(ButtonStyles.primary('SM'))

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

    def _refresh_version_cards_styles(self):
        """刷新版本卡片的主题样式"""
        if not self.content_widget:
            return

        # 获取当前主题的边框颜色
        border_color = theme_manager.BORDER_LIGHT
        is_dark = theme_manager.is_dark_mode()

        # 关键修复：更新嵌套的 version_tabs TabWidget 背景色
        # 查找所有 QTabWidget，排除主TabWidget
        for tab_widget in self.content_widget.findChildren(QTabWidget):
            if tab_widget != self.tab_widget:  # 不是主TabWidget
                tab_widget.setStyleSheet(theme_manager.tabs())

        # 查找所有版本卡片并更新样式
        for i in range(10):  # 最多支持10个版本
            card_name = f"version_card_{i}"
            if version_card := self.content_widget.findChild(QFrame, card_name):
                # 完全手动设置样式
                if is_dark:
                    bg_color = "rgba(26, 31, 53, 0.65)"
                else:
                    bg_color = "rgba(255, 255, 255, 0.72)"

                version_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {bg_color};
                        border: 1px solid {border_color};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: {dp(2)}px;
                    }}
                """)

                # 更新版本卡片内的文本编辑器
                for text_edit in version_card.findChildren(QTextEdit):
                    # 简单的StyleSheet设置（学习其他组件的做法）
                    text_edit.setStyleSheet(f"""
                        QTextEdit {{
                            background-color: {theme_manager.BG_CARD};
                            border: none;
                            padding: {dp(16)}px;
                            font-size: {sp(15)}px;
                            color: {theme_manager.TEXT_PRIMARY};
                            line-height: 1.8;
                        }}
                        {theme_manager.scrollbar()}
                    """)

            # 更新版本信息栏
            info_bar_name = f"version_info_bar_{i}"
            if info_bar := self.content_widget.findChild(QFrame, info_bar_name):
                info_bar.setStyleSheet(f"""
                    QFrame {{
                        background-color: {theme_manager.BG_CARD};
                        border: 1px solid {border_color};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: {dp(8)}px {dp(12)}px;
                    }}
                """)

                # 更新信息栏内的标签
                for label in info_bar.findChildren(QLabel):
                    if "info_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-size: {sp(12)}px;
                            color: {theme_manager.TEXT_SECONDARY};
                        """)

                # 更新按钮样式
                for btn in info_bar.findChildren(QPushButton):
                    if "select_btn" in btn.objectName():
                        if btn.isEnabled():
                            btn.setStyleSheet(ButtonStyles.primary('SM'))
                        else:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    background: {theme_manager.SUCCESS};
                                    color: {theme_manager.BUTTON_TEXT};
                                    border: none;
                                    border-radius: {dp(4)}px;
                                    padding: {dp(6)}px {dp(12)}px;
                                    font-size: {sp(12)}px;
                                }}
                            """)
                    elif "retry_btn" in btn.objectName():
                        btn.setStyleSheet(ButtonStyles.secondary('SM'))

    def _refresh_review_styles(self):
        """刷新评审区域的主题样式"""
        if not self.content_widget:
            return

        # 更新推荐卡片
        if recommendation_card := self.content_widget.findChild(QFrame, "recommendation_card"):
            gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)
            recommendation_card.setStyleSheet(f"""
                QFrame#recommendation_card {{
                    background: {gradient};
                    border-radius: {theme_manager.RADIUS_MD};
                    border: none;
                    padding: {dp(14)}px;
                }}
            """)

            # 更新推荐卡片内的标题
            for label in recommendation_card.findChildren(QLabel):
                if "rec_title" in label.objectName():
                    label.setStyleSheet(f"""
                        font-size: {sp(15)}px;
                        font-weight: 700;
                        color: {theme_manager.BUTTON_TEXT};
                    """)
                elif "rec_reason" in label.objectName():
                    label.setStyleSheet(f"""
                        font-size: {sp(12)}px;
                        color: {theme_manager.BUTTON_TEXT};
                        opacity: 0.9;
                    """)

        # 更新评审卡片样式
        for i in range(1, 10):  # 最多支持10个版本的评审卡片
            card_name = f"eval_card_{i}"
            if eval_card := self.content_widget.findChild(QFrame, card_name):
                # 检查是否为推荐版本（通过边框判断）
                current_style = eval_card.styleSheet()
                is_recommended = "2px solid" in current_style
                border_style = f"2px solid {theme_manager.PRIMARY}" if is_recommended else f"1px solid {theme_manager.BORDER_DEFAULT}"

                eval_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {theme_manager.BG_CARD};
                        border: {border_style};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新评审卡片内的标题
                for label in eval_card.findChildren(QLabel):
                    if "eval_title" in label.objectName():
                        label.setStyleSheet(f"""
                            font-size: {sp(14)}px;
                            font-weight: 700;
                            color: {theme_manager.TEXT_PRIMARY};
                        """)
                    elif "eval_badge" in label.objectName():
                        label.setStyleSheet(f"""
                            background: {theme_manager.PRIMARY};
                            color: {theme_manager.BUTTON_TEXT};
                            padding: {dp(2)}px {dp(8)}px;
                            border-radius: {dp(4)}px;
                            font-size: {sp(11)}px;
                        """)
                    elif "pros_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-size: {sp(12)}px;
                            color: {theme_manager.SUCCESS};
                            padding: {dp(4)}px {dp(8)}px;
                            background-color: {theme_manager.SUCCESS_BG};
                            border-radius: {dp(4)}px;
                        """)
                    elif "cons_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-size: {sp(12)}px;
                            color: {theme_manager.WARNING};
                            padding: {dp(4)}px {dp(8)}px;
                            background-color: {theme_manager.WARNING_BG};
                            border-radius: {dp(4)}px;
                        """)

        # 更新重新评审按钮
        if reeval_btn := self.content_widget.findChild(QPushButton, "reeval_btn"):
            reeval_btn.setStyleSheet(ButtonStyles.secondary())

        # 更新开始评审按钮（空状态时显示）
        if evaluate_btn := self.content_widget.findChild(QPushButton, "evaluate_btn"):
            evaluate_btn.setStyleSheet(ButtonStyles.primary())

        # 更新评审区域的滚动条
        for scroll_area in self.content_widget.findChildren(QScrollArea):
            if "details_scroll" in scroll_area.objectName():
                scroll_area.setStyleSheet(f"""
                    QScrollArea {{
                        border: none;
                        background-color: transparent;
                    }}
                    {theme_manager.scrollbar()}
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

        # TabWidget：正文、版本、评审
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

        layout.addWidget(self.tab_widget, stretch=1)

        return widget

    def createContentTab(self, chapter_data):
        """创建正文标签页 - 现代化设计（内容优先）"""
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
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
            font-weight: 500;
        """)
        toolbar_layout.addWidget(word_count_label)

        # 状态提示
        if not content:
            status_label = QLabel("• 尚未生成")
            status_label.setObjectName("status_label")  # 添加objectName
            status_label.setStyleSheet(f"""
                font-size: {sp(13)}px;
                color: {theme_manager.WARNING};
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

        # 应用玻璃拟态效果 - 手动设置样式
        if theme_manager.is_dark_mode():
            bg_color = "rgba(26, 31, 53, 0.65)"
        else:
            bg_color = "rgba(255, 255, 255, 0.72)"

        editor_container.setStyleSheet(f"""
            QFrame#editor_container {{
                background-color: {bg_color};
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
            MessageService.show_success(self, "章节内容已保存")

    def createVersionsTab(self, chapter_data):
        """创建版本对比标签页 - 现代化设计"""
        versions = chapter_data.get('versions', [])
        selected_idx = chapter_data.get('selected_version')

        # 如果没有版本数据，使用专业空状态组件
        if not versions:
            return EmptyStateWithIllustration(
                illustration_char='📑',
                title='暂无版本',
                description='生成章节后，AI会创建3个候选版本供你选择',
                action_text='生成章节',
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

        # 手动设置样式
        if theme_manager.is_dark_mode():
            bg_color = "rgba(26, 31, 53, 0.65)"
        else:
            bg_color = "rgba(255, 255, 255, 0.72)"

        content_card.setStyleSheet(f"""
            QFrame#version_card_{version_index} {{
                background-color: {bg_color};
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
            font-size: {sp(15)}px;
            font-weight: 700;
            color: {theme_manager.BUTTON_TEXT};
        """)
        rec_info_layout.addWidget(rec_title)

        rec_reason = QLabel(reason)
        rec_reason.setObjectName("rec_reason")  # 添加objectName
        rec_reason.setWordWrap(True)
        rec_reason.setStyleSheet(f"""
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
            font-size: {sp(14)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)

        if is_recommended:
            badge = QLabel("AI推荐")
            badge.setObjectName(f"eval_badge_{version_num}")  # 添加objectName
            badge.setStyleSheet(f"""
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
                font-size: {sp(12)}px;
                color: {theme_manager.SUCCESS};
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
                font-size: {sp(12)}px;
                color: {theme_manager.WARNING};
                padding: {dp(4)}px {dp(8)}px;
                background-color: {theme_manager.WARNING_BG};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(cons_label)

        return card
