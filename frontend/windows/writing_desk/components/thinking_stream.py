"""
Agent思考过程流式显示组件

显示Agent的思考过程、动作和观察结果，类似Claude Code的体验。

特性：
- 分层显示：思考 -> 动作 -> 观察 -> 建议
- 视觉区分：不同类型使用不同图标和颜色
- 层级缩进：子步骤自动缩进
- 状态指示：显示当前分析进度
- 动画效果：运行时状态指示器动画
- 折叠展开：思考块可折叠，折叠时显示前两行预览
"""

from datetime import datetime
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QCursor

from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ThinkingBlock(ThemeAwareFrame):
    """单个思考块 - Claude Code风格，支持折叠/展开"""

    # 类型定义
    TYPE_THINKING = "thinking"        # 思考过程
    TYPE_ACTION = "action"            # 执行动作
    TYPE_OBSERVATION = "observation"  # 观察结果
    TYPE_SUGGESTION = "suggestion_hint"  # 建议提示
    TYPE_PROGRESS = "progress"        # 进度信息
    TYPE_ERROR = "error"              # 错误信息
    TYPE_SUCCESS = "success"          # 成功信息

    # 预览行数
    PREVIEW_LINES = 2

    def __init__(
        self,
        block_type: str,
        content: str,
        step: Optional[str] = None,
        indent_level: int = 0,
        details: Optional[List[str]] = None,
        collapsible: bool = True,
        parent=None
    ):
        """
        初始化思考块

        Args:
            block_type: 块类型
            content: 主要内容
            step: 步骤标识
            indent_level: 缩进级别（0-2）
            details: 详细信息列表
            collapsible: 是否可折叠
            parent: 父组件
        """
        self.block_type = block_type
        self.content = content
        self.step = step
        self.indent_level = min(indent_level, 2)  # 最多2级缩进
        self.details = details or []
        self.timestamp = datetime.now()
        self.collapsible = collapsible
        self.is_collapsed = True  # 默认折叠

        # UI组件
        self.icon_label = None
        self.content_label = None
        self.preview_label = None
        self.time_label = None
        self.toggle_btn = None
        self.details_container = None
        self.full_content_widget = None

        super().__init__(parent)
        self.setupUI()

    def _get_preview_text(self) -> str:
        """获取预览文本（前两行）"""
        lines = self.content.split('\n')
        preview_lines = lines[:self.PREVIEW_LINES]
        preview = '\n'.join(preview_lines)

        # 如果内容超过预览行数，添加省略号
        if len(lines) > self.PREVIEW_LINES or len(self.content) > 80:
            if len(preview) > 80:
                preview = preview[:80]
            preview += "..."

        return preview

    def _should_be_collapsible(self) -> bool:
        """判断是否应该可折叠"""
        if not self.collapsible:
            return False
        # 内容较长或有详细信息时可折叠
        lines = self.content.split('\n')
        return len(lines) > self.PREVIEW_LINES or len(self.content) > 80 or len(self.details) > 0

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            dp(8 + self.indent_level * 16), dp(6), dp(8), dp(6)
        )
        main_layout.setSpacing(dp(4))

        # 主行布局（始终显示）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(dp(24))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)

        # 内容预览/完整内容
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 预览标签（折叠时显示）
        self.preview_label = QLabel(self._get_preview_text())
        self.preview_label.setWordWrap(True)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        content_layout.addWidget(self.preview_label)

        # 完整内容标签（展开时显示）
        self.content_label = QLabel(self.content)
        self.content_label.setWordWrap(True)
        self.content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.content_label.setVisible(False)  # 初始隐藏
        content_layout.addWidget(self.content_label)

        header_layout.addWidget(content_widget, stretch=1)

        # 折叠/展开按钮
        if self._should_be_collapsible():
            self.toggle_btn = QPushButton()
            self.toggle_btn.setFixedSize(dp(20), dp(20))
            self.toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.toggle_btn.clicked.connect(self._toggle_collapse)
            self._update_toggle_button()
            header_layout.addWidget(self.toggle_btn)

        # 时间戳
        self.time_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        self.time_label.setFixedWidth(dp(55))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.time_label)

        main_layout.addLayout(header_layout)

        # 详细信息容器（展开时显示）
        if self.details:
            self.details_container = QWidget()
            self.details_container.setVisible(False)  # 初始隐藏
            details_layout = QVBoxLayout(self.details_container)
            details_layout.setContentsMargins(dp(32), dp(4), 0, 0)
            details_layout.setSpacing(dp(2))

            for detail in self.details:
                detail_label = QLabel(f"- {detail}")
                detail_label.setWordWrap(True)
                detail_label.setObjectName("detail_label")
                details_layout.addWidget(detail_label)

            main_layout.addWidget(self.details_container)

    def _toggle_collapse(self):
        """切换折叠状态"""
        self.is_collapsed = not self.is_collapsed

        # 切换显示
        self.preview_label.setVisible(self.is_collapsed)
        self.content_label.setVisible(not self.is_collapsed)

        if self.details_container:
            self.details_container.setVisible(not self.is_collapsed)

        self._update_toggle_button()

    def _update_toggle_button(self):
        """更新折叠按钮图标"""
        if self.toggle_btn:
            # 使用文字符号作为展开/折叠指示
            icon = "+" if self.is_collapsed else "-"
            self.toggle_btn.setText(icon)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()

        # 图标映射 - 使用文字符号代替emoji
        icon_map = {
            self.TYPE_THINKING: "[*]",      # 思考
            self.TYPE_ACTION: "[>]",        # 动作
            self.TYPE_OBSERVATION: "[=]",   # 观察
            self.TYPE_SUGGESTION: "[!]",    # 建议
            self.TYPE_PROGRESS: "[~]",      # 进度
            self.TYPE_ERROR: "[X]",         # 错误
            self.TYPE_SUCCESS: "[+]",       # 成功
        }

        # 颜色映射
        color_map = {
            self.TYPE_THINKING: theme_manager.INFO,
            self.TYPE_ACTION: theme_manager.WARNING,
            self.TYPE_OBSERVATION: theme_manager.SUCCESS,
            self.TYPE_SUGGESTION: theme_manager.PRIMARY,
            self.TYPE_PROGRESS: theme_manager.TEXT_SECONDARY,
            self.TYPE_ERROR: theme_manager.ERROR,
            self.TYPE_SUCCESS: theme_manager.SUCCESS,
        }

        icon = icon_map.get(self.block_type, "[?]")
        color = color_map.get(self.block_type, theme_manager.TEXT_PRIMARY)

        # 图标样式
        if self.icon_label:
            self.icon_label.setText(icon)
            self.icon_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {color};
            """)

        # 内容样式
        content_style = f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_PRIMARY};
            line-height: 1.5;
        """

        # 预览样式（稍微暗淡）
        preview_style = f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
            line-height: 1.5;
        """

        if self.content_label:
            font_weight = "font-weight: 600;" if self.block_type in [self.TYPE_SUGGESTION, self.TYPE_ERROR] else ""
            self.content_label.setStyleSheet(content_style + font_weight)

        if self.preview_label:
            self.preview_label.setStyleSheet(preview_style)

        # 时间戳样式
        if self.time_label:
            self.time_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(10)}px;
                color: {theme_manager.TEXT_TERTIARY};
            """)

        # 折叠按钮样式
        if self.toggle_btn:
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    font-weight: bold;
                    color: {theme_manager.TEXT_SECONDARY};
                    background-color: transparent;
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {dp(4)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.BG_CARD_HOVER};
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)

        # 详细信息样式
        if self.details_container:
            for label in self.details_container.findChildren(QLabel, "detail_label"):
                label.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                    line-height: 1.4;
                """)

        # 整体容器样式 - 左边框指示类型
        border_color = color
        bg_alpha = "08" if self.block_type == self.TYPE_SUGGESTION else "00"
        self.setStyleSheet(f"""
            ThinkingBlock {{
                background-color: {color}{bg_alpha};
                border-left: 3px solid {border_color};
                border-radius: {dp(4)}px;
                margin: {dp(2)}px 0;
            }}
        """)


class ThinkingStreamView(ThemeAwareWidget):
    """Agent思考过程流式显示组件 - Claude Code风格

    特性：
    - 分层显示思考、动作、观察、建议
    - 进度条和状态指示
    - 自动滚动到最新内容
    - 支持折叠/展开
    - 运行状态动画效果
    """

    cleared = pyqtSignal()  # 清空信号
    workflow_paused = pyqtSignal()  # 工作流暂停信号
    workflow_resumed = pyqtSignal()  # 工作流恢复信号

    # 动画帧序列 - 模拟旋转效果
    ANIMATION_FRAMES = ["[|]", "[/]", "[-]", "[\\]"]
    ANIMATION_INTERVAL = 150  # 毫秒

    def __init__(self, parent=None):
        self.thinking_blocks = []
        self.scroll_area = None
        self.container = None
        self.container_layout = None
        self.header_label = None
        self.clear_btn = None
        self.collapse_btn = None
        self.status_indicator = None
        self.progress_bar = None
        self.current_paragraph_label = None
        self.is_collapsed = False

        # 进度跟踪
        self.total_paragraphs = 0
        self.current_paragraph = 0
        self.total_suggestions = 0

        # 动画状态
        self._animation_timer = None
        self._animation_frame_index = 0
        self._current_status = "running"
        self._status_color = None

        super().__init__(parent)
        self.setupUI()
        self._init_animation()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 头部
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        # 状态指示器（动画点）
        self.status_indicator = QLabel("[~]")
        self.status_indicator.setFixedWidth(dp(20))
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.status_indicator)

        self.header_label = QLabel("Agent 思考过程")
        header.addWidget(self.header_label)

        header.addStretch()

        # 折叠按钮
        self.collapse_btn = QPushButton("收起")
        self.collapse_btn.setFixedWidth(dp(50))
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header.addWidget(self.collapse_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(dp(50))
        self.clear_btn.clicked.connect(self.clear)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        # 进度条
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(dp(3))
        self.progress_bar.setObjectName("progress_bar")
        layout.addWidget(self.progress_bar)

        # 当前段落指示
        self.current_paragraph_label = QLabel("")
        self.current_paragraph_label.setObjectName("current_paragraph_label")
        self.current_paragraph_label.setVisible(False)
        layout.addWidget(self.current_paragraph_label)

        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        self.container_layout.setSpacing(dp(2))
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area, stretch=1)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()

        # 状态指示器
        if self.status_indicator:
            self.status_indicator.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {theme_manager.PRIMARY};
            """)

        if self.header_label:
            self.header_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        btn_style = f"""
            QPushButton {{
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(2)}px {dp(6)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
            }}
        """
        if self.clear_btn:
            self.clear_btn.setStyleSheet(btn_style)
        if self.collapse_btn:
            self.collapse_btn.setStyleSheet(btn_style)

        # 进度条
        if self.progress_bar:
            progress = self._calculate_progress()
            self.progress_bar.setStyleSheet(f"""
                QFrame#progress_bar {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme_manager.PRIMARY},
                        stop:{progress} {theme_manager.PRIMARY},
                        stop:{progress + 0.001} {theme_manager.BG_SECONDARY},
                        stop:1 {theme_manager.BG_SECONDARY}
                    );
                    border-radius: {dp(1)}px;
                }}
            """)

        if self.current_paragraph_label:
            self.current_paragraph_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding: {dp(6)}px {dp(10)}px;
                background-color: {theme_manager.BG_SECONDARY};
                border-radius: {dp(4)}px;
                border-left: 3px solid {theme_manager.PRIMARY};
            """)

        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {theme_manager.scrollbar()}
            """)

        if self.container:
            self.container.setStyleSheet(f"""
                background-color: transparent;
            """)

    def _calculate_progress(self) -> float:
        """计算进度百分比"""
        if self.total_paragraphs <= 0:
            return 0.0
        return min(1.0, self.current_paragraph / self.total_paragraphs)

    def _update_progress_bar(self):
        """更新进度条"""
        if self.progress_bar:
            progress = self._calculate_progress()
            self.progress_bar.setStyleSheet(f"""
                QFrame#progress_bar {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme_manager.PRIMARY},
                        stop:{progress} {theme_manager.PRIMARY},
                        stop:{progress + 0.001} {theme_manager.BG_SECONDARY},
                        stop:1 {theme_manager.BG_SECONDARY}
                    );
                    border-radius: 1px;
                }}
            """)

    def _toggle_collapse(self):
        """切换折叠状态"""
        self.is_collapsed = not self.is_collapsed
        if self.scroll_area:
            self.scroll_area.setVisible(not self.is_collapsed)
        if self.collapse_btn:
            self.collapse_btn.setText("展开" if self.is_collapsed else "收起")

    def _init_animation(self):
        """初始化动画定时器"""
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._on_animation_tick)

    def _start_animation(self):
        """启动状态指示器动画（线程安全）"""
        # 使用QTimer.singleShot确保在主线程执行
        if self._animation_timer:
            QTimer.singleShot(0, self._do_start_animation)

    def _do_start_animation(self):
        """实际启动动画（在主线程执行）"""
        if self._animation_timer and not self._animation_timer.isActive():
            self._animation_frame_index = 0
            self._animation_timer.start(self.ANIMATION_INTERVAL)

    def _stop_animation(self):
        """停止状态指示器动画（线程安全）"""
        # 使用QTimer.singleShot确保在主线程执行
        if self._animation_timer:
            QTimer.singleShot(0, self._do_stop_animation)

    def _do_stop_animation(self):
        """实际停止动画（在主线程执行）"""
        if self._animation_timer and self._animation_timer.isActive():
            self._animation_timer.stop()

    def _on_animation_tick(self):
        """动画帧更新回调"""
        if not self.status_indicator or self._current_status != "running":
            self._stop_animation()
            return

        # 更新到下一帧
        self._animation_frame_index = (self._animation_frame_index + 1) % len(self.ANIMATION_FRAMES)
        frame = self.ANIMATION_FRAMES[self._animation_frame_index]
        self.status_indicator.setText(frame)

    def set_status(self, status: str):
        """
        设置状态指示（线程安全）

        Args:
            status: 状态 (running/paused/complete/error)
        """
        self._current_status = status

        # 使用QTimer.singleShot确保UI更新在主线程执行
        QTimer.singleShot(0, lambda: self._do_set_status(status))

    def _do_set_status(self, status: str):
        """实际设置状态（在主线程执行）"""
        status_map = {
            "running": ("[|]", theme_manager.PRIMARY),
            "paused": ("[-]", theme_manager.WARNING),
            "complete": ("[+]", theme_manager.SUCCESS),
            "error": ("[X]", theme_manager.ERROR),
        }
        icon, color = status_map.get(status, ("[?]", theme_manager.TEXT_SECONDARY))
        self._status_color = color

        if self.status_indicator:
            self.status_indicator.setText(icon)
            self.status_indicator.setStyleSheet(f"""
                font-family: {theme_manager.ui_font()};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {color};
            """)

        # 根据状态控制动画
        if status == "running":
            self._do_start_animation()
        else:
            self._do_stop_animation()

    def set_current_paragraph(self, index: int, preview: str):
        """
        设置当前正在分析的段落（线程安全）

        Args:
            index: 段落索引
            preview: 段落预览
        """
        self.current_paragraph = index + 1
        # 使用QTimer.singleShot确保UI更新在主线程执行
        QTimer.singleShot(0, lambda: self._do_set_current_paragraph(index, preview))

    def _do_set_current_paragraph(self, index: int, preview: str):
        """实际设置当前段落（在主线程执行）"""
        self._update_progress_bar()

        if self.current_paragraph_label:
            progress_text = f"[{self.current_paragraph}/{self.total_paragraphs}]" if self.total_paragraphs > 0 else ""
            text = f"{progress_text} 正在分析第 {index + 1} 段: {preview[:50]}..."
            self.current_paragraph_label.setText(text)
            self.current_paragraph_label.setVisible(True)

        self._do_set_status("running")

    def add_thinking(self, content: str, step: str, indent: int = 0, details: list = None):
        """
        添加思考内容

        Args:
            content: 思考内容
            step: 步骤标识
            indent: 缩进级别
            details: 详细信息列表
        """
        self._add_block(ThinkingBlock.TYPE_THINKING, content, step, indent, details)

    def add_action(self, action: str, description: str, indent: int = 1, details: list = None):
        """
        添加动作

        Args:
            action: 动作类型
            description: 动作描述
            indent: 缩进级别
            details: 详细信息列表
        """
        self._add_block(ThinkingBlock.TYPE_ACTION, description, action, indent, details)

    def add_observation(self, result: str, relevance: Optional[float] = None, indent: int = 1, details: list = None):
        """
        添加观察结果

        Args:
            result: 观察结果
            relevance: 相关度（可选）
            indent: 缩进级别
            details: 详细信息列表
        """
        content = result
        if relevance is not None:
            content += f" (相关度: {relevance:.0%})"
        self._add_block(ThinkingBlock.TYPE_OBSERVATION, content, None, indent, details)

    def add_suggestion_hint(self, reason: str, indent: int = 0):
        """
        添加建议提示

        Args:
            reason: 建议原因
            indent: 缩进级别
        """
        self._add_block(ThinkingBlock.TYPE_SUGGESTION, reason, None, indent)
        self.total_suggestions += 1

    def add_error(self, message: str):
        """添加错误信息"""
        self._add_block(ThinkingBlock.TYPE_ERROR, message)
        self.set_status("error")

    def add_success(self, message: str):
        """添加成功信息"""
        self._add_block(ThinkingBlock.TYPE_SUCCESS, message)

    def add_progress(self, message: str):
        """添加进度信息"""
        self._add_block(ThinkingBlock.TYPE_PROGRESS, message)

    def _add_block(
        self,
        block_type: str,
        content: str,
        step: Optional[str] = None,
        indent: int = 0,
        details: list = None
    ):
        """
        添加思考块（线程安全）

        Args:
            block_type: 块类型
            content: 内容
            step: 步骤标识
            indent: 缩进级别
            details: 详细信息列表
        """
        # 使用QTimer.singleShot确保UI操作在主线程执行
        QTimer.singleShot(0, lambda: self._do_add_block(
            block_type, content, step, indent, details
        ))

    def _do_add_block(
        self,
        block_type: str,
        content: str,
        step: Optional[str] = None,
        indent: int = 0,
        details: list = None
    ):
        """实际添加思考块（在主线程执行）"""
        # 检查容器是否仍然有效
        if not self.container or not self.container_layout:
            return

        block = ThinkingBlock(
            block_type, content, step,
            indent_level=indent,
            details=details,
            parent=self.container
        )
        self.thinking_blocks.append(block)

        # 插入到stretch之前
        self.container_layout.insertWidget(
            self.container_layout.count() - 1,
            block
        )

        # 使用定时器延迟滚动，确保布局更新完成
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """滚动到底部"""
        if self.scroll_area:
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """清空所有思考块（线程安全）"""
        # 重置状态变量（这些是线程安全的基本类型操作）
        self.total_paragraphs = 0
        self.current_paragraph = 0
        self.total_suggestions = 0

        # UI操作在主线程执行
        QTimer.singleShot(0, self._do_clear)

    def _do_clear(self):
        """实际清空操作（在主线程执行）"""
        for block in self.thinking_blocks:
            block.deleteLater()
        self.thinking_blocks.clear()

        if self.current_paragraph_label:
            self.current_paragraph_label.setVisible(False)

        self._update_progress_bar()
        self._do_set_status("running")
        self.cleared.emit()

    def on_workflow_start(self, total_paragraphs: int, dimensions: list):
        """
        工作流开始回调（线程安全）

        Args:
            total_paragraphs: 总段落数
            dimensions: 检查维度
        """
        self.total_paragraphs = total_paragraphs
        # 使用QTimer.singleShot确保UI操作在主线程执行
        QTimer.singleShot(0, lambda: self._do_workflow_start(total_paragraphs, dimensions))

    def _do_workflow_start(self, total_paragraphs: int, dimensions: list):
        """实际工作流开始处理（在主线程执行）"""
        self._do_clear()
        self.total_paragraphs = total_paragraphs
        self._do_set_status("running")

        # 维度名称映射
        dim_names = {
            "coherence": "逻辑连贯",
            "character": "角色一致",
            "foreshadow": "伏笔呼应",
            "timeline": "时间线",
            "style": "风格一致",
            "scene": "场景描写",
        }
        dim_display = [dim_names.get(d, d) for d in dimensions]

        self._do_add_block(
            ThinkingBlock.TYPE_THINKING,
            f"开始分析 {total_paragraphs} 个段落",
            "start",
            0,
            [f"检查维度: {', '.join(dim_display)}"]
        )

    def on_workflow_complete(self, total_suggestions: int, summary: str):
        """
        工作流完成回调（线程安全）

        Args:
            total_suggestions: 总建议数
            summary: 汇总信息
        """
        self.current_paragraph = self.total_paragraphs
        # 使用QTimer.singleShot确保UI操作在主线程执行
        QTimer.singleShot(0, lambda: self._do_workflow_complete(total_suggestions, summary))

    def _do_workflow_complete(self, total_suggestions: int, summary: str):
        """实际工作流完成处理（在主线程执行）"""
        self._update_progress_bar()
        self._do_set_status("complete")

        if self.current_paragraph_label:
            self.current_paragraph_label.setVisible(False)

        self._do_add_block(ThinkingBlock.TYPE_SUCCESS, f"分析完成，共发现 {total_suggestions} 条建议")

    def on_workflow_paused(self):
        """工作流暂停（线程安全）"""
        QTimer.singleShot(0, self._do_workflow_paused)

    def _do_workflow_paused(self):
        """实际工作流暂停处理（在主线程执行）"""
        self._do_set_status("paused")
        self._do_add_block(ThinkingBlock.TYPE_PROGRESS, "等待用户处理建议...")
        self.workflow_paused.emit()

    def on_workflow_resumed(self):
        """工作流恢复（线程安全）"""
        QTimer.singleShot(0, self._do_workflow_resumed)

    def _do_workflow_resumed(self):
        """实际工作流恢复处理（在主线程执行）"""
        self._do_set_status("running")
        self._do_add_block(ThinkingBlock.TYPE_PROGRESS, "继续分析...")
        self.workflow_resumed.emit()

    def cleanup(self):
        """清理资源，停止动画定时器"""
        self._stop_animation()
        if self._animation_timer:
            self._animation_timer.deleteLater()
            self._animation_timer = None
