"""
CodingDesk Workspace组件

提供内容编辑和助手面板功能。
支持实现Prompt和审查Prompt两种模式的Tab切换。
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QTextEdit, QStackedWidget, QSplitter, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

# 导入助手面板
from .assistant_panel import CodingAssistantPanel

logger = logging.getLogger(__name__)


class TabButton(QPushButton):
    """Tab切换按钮"""

    def __init__(self, text: str, is_active: bool = False, parent=None):
        super().__init__(text, parent)
        self._is_active = is_active
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_theme()
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def setActive(self, active: bool):
        """设置激活状态"""
        self._is_active = active
        self._apply_theme()

    def isActive(self) -> bool:
        """是否激活"""
        return self._is_active

    def _apply_theme(self):
        """应用主题样式"""
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                    font-weight: 500;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY}15;
                    color: {theme_manager.PRIMARY};
                    border-color: {theme_manager.PRIMARY};
                }}
            """)


class ContentEditor(ThemeAwareFrame):
    """内容编辑器（支持Tab切换，主题感知）"""

    # 实现Prompt信号
    contentChanged = pyqtSignal(str)
    saveRequested = pyqtSignal()
    # 审查Prompt信号
    reviewContentChanged = pyqtSignal(str)
    saveReviewRequested = pyqtSignal()
    generateReviewRequested = pyqtSignal()
    # Tab切换信号
    tabChanged = pyqtSignal(str)  # "implementation" or "review"

    def __init__(self, parent=None):
        self._current_tab = "implementation"  # 当前Tab
        self._implementation_content = ""  # 实现Prompt内容
        self._review_content = ""  # 审查Prompt内容
        self.impl_tab = None
        self.review_tab = None
        self.title_label = None
        self.word_count_label = None
        self.generate_review_btn = None
        self.save_btn = None
        self.editor = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("content_editor")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = QWidget()
        toolbar.setObjectName("editor_toolbar")
        toolbar.setFixedHeight(dp(48))
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(dp(12), dp(6), dp(12), dp(6))
        toolbar_layout.setSpacing(dp(8))

        # Tab切换按钮组
        tab_container = QWidget()
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(dp(4))

        self.impl_tab = TabButton("实现Prompt", is_active=True)
        self.impl_tab.clicked.connect(lambda: self._switch_tab("implementation"))
        tab_layout.addWidget(self.impl_tab)

        self.review_tab = TabButton("审查Prompt", is_active=False)
        self.review_tab.clicked.connect(lambda: self._switch_tab("review"))
        tab_layout.addWidget(self.review_tab)

        toolbar_layout.addWidget(tab_container)

        # 标题
        self.title_label = QLabel("")
        self.title_label.setObjectName("editor_title")
        toolbar_layout.addWidget(self.title_label)

        toolbar_layout.addStretch()

        # 字数统计
        self.word_count_label = QLabel("0 字")
        self.word_count_label.setObjectName("word_count")
        toolbar_layout.addWidget(self.word_count_label)

        # 生成审查Prompt按钮（仅在审查Tab时显示）
        self.generate_review_btn = QPushButton("生成")
        self.generate_review_btn.setObjectName("generate_review_btn")
        self.generate_review_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_review_btn.clicked.connect(self.generateReviewRequested.emit)
        self.generate_review_btn.setVisible(False)
        toolbar_layout.addWidget(self.generate_review_btn)

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save_clicked)
        toolbar_layout.addWidget(self.save_btn)

        layout.addWidget(toolbar)

        # 编辑器
        self.editor = QTextEdit()
        self.editor.setObjectName("text_editor")
        self.editor.setPlaceholderText("在此编辑内容...")
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor, 1)

    def _switch_tab(self, tab: str):
        """切换Tab"""
        if tab == self._current_tab:
            return

        # 保存当前内容
        current_text = self.editor.toPlainText()
        if self._current_tab == "implementation":
            self._implementation_content = current_text
        else:
            self._review_content = current_text

        # 切换Tab
        self._current_tab = tab

        # 更新Tab按钮状态
        self.impl_tab.setActive(tab == "implementation")
        self.review_tab.setActive(tab == "review")

        # 更新生成按钮可见性
        self.generate_review_btn.setVisible(tab == "review")

        # 加载对应内容
        if tab == "implementation":
            self.editor.blockSignals(True)
            self.editor.setPlainText(self._implementation_content)
            self.editor.blockSignals(False)
            self.word_count_label.setText(f"{len(self._implementation_content)} 字")
            self.editor.setPlaceholderText("在此编辑实现Prompt...")
        else:
            self.editor.blockSignals(True)
            self.editor.setPlainText(self._review_content)
            self.editor.blockSignals(False)
            self.word_count_label.setText(f"{len(self._review_content)} 字")
            self.editor.setPlaceholderText("在此编辑审查Prompt...")

        # 发送Tab切换信号
        self.tabChanged.emit(tab)

    def _on_text_changed(self):
        """文本变化"""
        text = self.editor.toPlainText()
        self.word_count_label.setText(f"{len(text)} 字")

        if self._current_tab == "implementation":
            self._implementation_content = text
            self.contentChanged.emit(text)
        else:
            self._review_content = text
            self.reviewContentChanged.emit(text)

    def _on_save_clicked(self):
        """保存按钮点击"""
        if self._current_tab == "implementation":
            self.saveRequested.emit()
        else:
            self.saveReviewRequested.emit()

    def setTitle(self, title: str):
        """设置标题"""
        self.title_label.setText(title)

    def setContent(self, content: str):
        """设置实现Prompt内容"""
        self._implementation_content = content
        if self._current_tab == "implementation":
            self.editor.blockSignals(True)
            self.editor.setPlainText(content)
            self.editor.blockSignals(False)
            self.word_count_label.setText(f"{len(content)} 字")

    def setReviewContent(self, content: str):
        """设置审查Prompt内容"""
        self._review_content = content
        if self._current_tab == "review":
            self.editor.blockSignals(True)
            self.editor.setPlainText(content)
            self.editor.blockSignals(False)
            self.word_count_label.setText(f"{len(content)} 字")

    def getContent(self) -> str:
        """获取实现Prompt内容"""
        if self._current_tab == "implementation":
            return self.editor.toPlainText()
        return self._implementation_content

    def getReviewContent(self) -> str:
        """获取审查Prompt内容"""
        if self._current_tab == "review":
            return self.editor.toPlainText()
        return self._review_content

    def updateWordCount(self, count: int):
        """更新字数显示"""
        self.word_count_label.setText(f"{count} 字")

    def getCurrentTab(self) -> str:
        """获取当前Tab"""
        return self._current_tab

    def switchToReview(self):
        """切换到审查Tab"""
        self._switch_tab("review")

    def switchToImplementation(self):
        """切换到实现Tab"""
        self._switch_tab("implementation")

    def clearAll(self):
        """清空所有内容"""
        self._implementation_content = ""
        self._review_content = ""
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.word_count_label.setText("0 字")

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#content_editor {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QWidget#editor_toolbar {{
                background-color: transparent;
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
            QLabel#editor_title {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
                margin-left: {dp(8)}px;
            }}
            QLabel#word_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
            }}
            QPushButton#save_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#save_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#generate_review_btn {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#generate_review_btn:hover {{
                background-color: {theme_manager.SUCCESS_DARK if hasattr(theme_manager, 'SUCCESS_DARK') else '#059669'};
            }}
            QTextEdit#text_editor {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
                border: none;
                padding: {dp(12)}px;
                font-size: {dp(14)}px;
                line-height: 1.6;
            }}
        """)


class EmptyState(ThemeAwareFrame):
    """空状态（主题感知）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("empty_state")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(40), dp(60), dp(40), dp(60))
        layout.setSpacing(dp(16))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("[ ]")
        icon_label.setObjectName("empty_icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_label = QLabel("请从左侧选择一个功能")
        text_label.setObjectName("empty_text")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#empty_state {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 2px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
            }}
            QLabel#empty_icon {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(48)}px;
            }}
            QLabel#empty_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(16)}px;
            }}
        """)


class GeneratingState(ThemeAwareFrame):
    """生成中状态（主题感知）"""

    def __init__(self, parent=None):
        self.title_label = None
        self.content_display = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("generating_state")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(40), dp(60), dp(40), dp(60))
        layout.setSpacing(dp(16))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel("正在生成...")
        self.title_label.setObjectName("gen_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 流式内容显示
        self.content_display = QTextEdit()
        self.content_display.setObjectName("gen_content")
        self.content_display.setReadOnly(True)
        self.content_display.setMinimumHeight(dp(200))
        layout.addWidget(self.content_display, 1)

    def setTitle(self, title: str):
        """设置标题"""
        self.title_label.setText(f"正在生成: {title}")

    def appendContent(self, text: str):
        """追加内容"""
        self.content_display.insertPlainText(text)

    def clearContent(self):
        """清空内容"""
        self.content_display.clear()

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#generating_state {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(12)}px;
            }}
            QLabel#gen_title {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QTextEdit#gen_content {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
                font-size: {dp(14)}px;
            }}
        """)


class CDWorkspace(ThemeAwareFrame):
    """CodingDesk工作区（主题感知）"""

    # 实现Prompt信号
    generateRequested = pyqtSignal(int)
    saveContentRequested = pyqtSignal(int, str)
    # 审查Prompt信号
    generateReviewRequested = pyqtSignal(int)
    saveReviewRequested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        self._project_id = None
        self._current_feature_index = None
        self._current_feature_title = None
        self.content_stack = None
        self.empty_state = None
        self.generating_state = None
        self.editor = None
        self.assistant_panel = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("cd_workspace")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 主内容区（使用堆叠布局）
        self.content_stack = QStackedWidget()

        # 空状态
        self.empty_state = EmptyState()
        self.content_stack.addWidget(self.empty_state)

        # 生成中状态
        self.generating_state = GeneratingState()
        self.content_stack.addWidget(self.generating_state)

        # 编辑器
        self.editor = ContentEditor()
        self.editor.saveRequested.connect(self._on_save)
        self.editor.saveReviewRequested.connect(self._on_save_review)
        self.editor.generateReviewRequested.connect(self._on_generate_review)
        self.content_stack.addWidget(self.editor)

        layout.addWidget(self.content_stack, 1)

        # 助手面板（替换原来的版本面板）
        self.assistant_panel = CodingAssistantPanel()
        layout.addWidget(self.assistant_panel)

        # 默认显示空状态
        self.content_stack.setCurrentWidget(self.empty_state)

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        logger.info("CDWorkspace.setProjectId 被调用: project_id=%s", project_id)
        self._project_id = project_id
        # 同步设置到助手面板
        self.assistant_panel.setProjectId(project_id)

    def loadFeature(self, feature_index: int):
        """加载功能（显示空编辑器）"""
        self._current_feature_index = feature_index
        self._current_feature_title = f"功能 {feature_index + 1}"

        # 清空编辑器内容
        self.editor.clearAll()
        self.editor.setTitle(self._current_feature_title)
        self.editor.switchToImplementation()
        self.content_stack.setCurrentWidget(self.editor)

    def setFeatureContent(self, feature_index: int, data: dict):
        """设置功能内容（从API加载的数据）"""
        self._current_feature_index = feature_index
        self._current_feature_title = data.get('title', f'功能 {feature_index + 1}')

        content = data.get('content', '')
        review_prompt = data.get('review_prompt', '')
        word_count = data.get('word_count', len(content))

        self.editor.setTitle(self._current_feature_title)
        self.editor.setContent(content)
        self.editor.setReviewContent(review_prompt)
        self.editor.updateWordCount(word_count)
        self.editor.switchToImplementation()
        self.content_stack.setCurrentWidget(self.editor)

    def showGenerating(self, feature_index: int, feature_title: str = None):
        """显示生成中状态"""
        self._current_feature_index = feature_index
        self._current_feature_title = feature_title or f"功能 {feature_index + 1}"

        self.generating_state.setTitle(self._current_feature_title)
        self.generating_state.clearContent()
        self.content_stack.setCurrentWidget(self.generating_state)

    def showGeneratingReview(self, feature_index: int, feature_title: str = None):
        """显示审查Prompt生成中状态"""
        self._current_feature_index = feature_index
        self._current_feature_title = feature_title or f"功能 {feature_index + 1}"

        self.generating_state.setTitle(f"{self._current_feature_title} - 审查Prompt")
        self.generating_state.clearContent()
        self.content_stack.setCurrentWidget(self.generating_state)

    def appendGeneratedContent(self, text: str):
        """追加生成的内容"""
        self.generating_state.appendContent(text)

    def finishGenerating(self, content: str, version_count: int = 1):
        """完成生成（实现Prompt）"""
        self.editor.setTitle(self._current_feature_title or f"功能 {self._current_feature_index + 1}")
        self.editor.setContent(content)
        self.editor.switchToImplementation()
        self.content_stack.setCurrentWidget(self.editor)

    def finishGeneratingReview(self, review_prompt: str):
        """完成审查Prompt生成"""
        self.editor.setTitle(self._current_feature_title or f"功能 {self._current_feature_index + 1}")
        self.editor.setReviewContent(review_prompt)
        self.editor.switchToReview()
        self.content_stack.setCurrentWidget(self.editor)

    def onGenerationError(self, error_msg: str):
        """生成错误"""
        # 切换回编辑器，显示空内容
        self.editor.setTitle(self._current_feature_title or f"功能 {self._current_feature_index + 1}")
        self.content_stack.setCurrentWidget(self.editor)

    def onSaveSuccess(self, word_count: int):
        """保存成功"""
        self.editor.updateWordCount(word_count)

    def _on_save(self):
        """保存实现Prompt内容"""
        if self._current_feature_index is not None:
            content = self.editor.getContent()
            self.saveContentRequested.emit(self._current_feature_index, content)

    def _on_save_review(self):
        """保存审查Prompt内容"""
        if self._current_feature_index is not None:
            review_content = self.editor.getReviewContent()
            self.saveReviewRequested.emit(self._current_feature_index, review_content)

    def _on_generate_review(self):
        """生成审查Prompt"""
        if self._current_feature_index is not None:
            self.generateReviewRequested.emit(self._current_feature_index)

    def getCurrentTab(self) -> str:
        """获取当前Tab"""
        return self.editor.getCurrentTab()

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#cd_workspace {{
                background-color: transparent;
            }}
        """)


__all__ = ["CDWorkspace"]
