"""
正文优化内容组件

整合思考流、建议卡片、段落选择器等组件，提供完整的优化功能界面。

三层权限控制模式（参考Claude Code设计）：
- 审核模式（默认）：每个建议暂停等待用户确认
- 自动模式：自动应用建议并高亮标记
- 计划模式：先分析全文生成报告，用户确认后再应用
"""

import json
import logging
from enum import Enum
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSplitter,
    QStackedWidget, QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from api.client import AFNAPIClient
from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.sse_worker import SSEWorker

from .components.thinking_stream import ThinkingStreamView
from .components.suggestion_card import SuggestionCard
from .components.paragraph_selector import ParagraphSelector

logger = logging.getLogger(__name__)


class OptimizationMode(Enum):
    """优化模式枚举 - 参考Claude Code的三层权限设计"""
    REVIEW = "review"      # 审核模式：每个建议暂停等待确认
    AUTO = "auto"          # 自动模式：自动应用建议
    PLAN = "plan"          # 计划模式：先生成报告，确认后应用


class OptimizationContent(ThemeAwareWidget):
    """正文优化内容组件 - Claude Code风格交互

    三层权限控制：
    - 审核模式：每个建议单独确认，提供最高控制度
    - 自动模式：自动应用所有建议，适合快速优化
    - 计划模式：先完成全部分析，用户选择性应用
    """

    # 信号
    suggestion_applied = pyqtSignal(dict)  # 应用建议信号
    optimization_complete = pyqtSignal(int)  # 优化完成信号（建议数）

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.chapter_number: Optional[int] = None
        self.chapter_content: str = ""
        self.suggestions: List[dict] = []
        self.sse_worker: Optional[SSEWorker] = None
        self.is_optimizing = False

        # 三层权限模式 - 默认审核模式
        self.optimization_mode = OptimizationMode.REVIEW
        self.session_id: Optional[str] = None  # 后端会话ID，用于暂停/继续控制
        self.current_suggestion_card: Optional['SuggestionCard'] = None  # 当前待处理的建议卡片

        # 计划模式相关
        self.plan_mode_suggestions: List[dict] = []  # 计划模式收集的所有建议

        # UI组件
        self.header_label = None
        self.start_btn = None
        self.stop_btn = None
        self.status_label = None
        self.content_stack = None
        self.setup_page = None
        self.progress_page = None
        self.paragraph_selector = None
        self.thinking_stream = None
        self.suggestions_scroll = None
        self.suggestions_container = None
        self.suggestions_layout = None
        self.apply_all_btn = None
        self.apply_high_btn = None
        self.mode_group = None  # 模式选择按钮组
        self.review_radio = None
        self.auto_radio = None
        self.plan_radio = None
        self.continue_btn = None  # 继续分析按钮
        self.apply_plan_btn = None  # 计划模式应用按钮

        # 空状态UI组件
        self.empty_hint = None
        self.empty_icon_label = None
        self.empty_text_label = None
        self.empty_hint2_label = None
        self.content_area = None

        super().__init__(parent)
        self.setupUI()  # 显式调用setupUI来创建UI结构

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 头部
        header = QHBoxLayout()
        self.header_label = QLabel("正文优化")
        header.addWidget(self.header_label)
        header.addStretch()

        self.status_label = QLabel("")
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # 内容区域（使用堆叠页面）
        self.content_stack = QStackedWidget()

        # 页面1：设置页（段落选择 + 开始按钮）
        self.setup_page = self._create_setup_page()
        self.content_stack.addWidget(self.setup_page)

        # 页面2：进度页（思考流 + 建议列表）
        self.progress_page = self._create_progress_page()
        self.content_stack.addWidget(self.progress_page)

        layout.addWidget(self.content_stack, stretch=1)

    def _create_setup_page(self) -> QWidget:
        """创建设置页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 空状态提示（初始显示）
        self.empty_hint = QWidget()
        empty_layout = QVBoxLayout(self.empty_hint)
        empty_layout.setContentsMargins(0, dp(40), 0, 0)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.empty_icon_label = QLabel("...")
        self.empty_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_icon_label)

        self.empty_text_label = QLabel("请先在左侧选择一个章节")
        self.empty_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_text_label.setWordWrap(True)
        empty_layout.addWidget(self.empty_text_label)

        self.empty_hint2_label = QLabel("选择章节版本后，可以在此进行正文优化分析")
        self.empty_hint2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint2_label.setWordWrap(True)
        empty_layout.addWidget(self.empty_hint2_label)

        empty_layout.addStretch()
        layout.addWidget(self.empty_hint, stretch=1)

        # 内容区域（有章节时显示）
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(dp(12))

        # 提示
        hint_label = QLabel("选择要分析的段落，或直接分析全部内容")
        content_layout.addWidget(hint_label)

        # 段落选择器
        self.paragraph_selector = ParagraphSelector(parent=self.content_area)
        content_layout.addWidget(self.paragraph_selector, stretch=1)

        # 三层模式选择 - 参考Claude Code设计
        mode_frame = QFrame()
        mode_frame.setObjectName("mode_frame")
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        mode_layout.setSpacing(dp(8))

        mode_title = QLabel("优化模式")
        mode_title.setObjectName("mode_title")
        mode_layout.addWidget(mode_title)

        self.mode_group = QButtonGroup(mode_frame)

        # 审核模式（默认）
        self.review_radio = QRadioButton("审核模式（推荐）")
        self.review_radio.setObjectName("mode_radio")
        self.review_radio.setChecked(True)
        self.review_radio.setToolTip("每个建议都会暂停等待确认，适合重要章节")
        self.mode_group.addButton(self.review_radio, 0)
        mode_layout.addWidget(self.review_radio)

        review_desc = QLabel("每个建议单独确认，提供最高控制度")
        review_desc.setObjectName("mode_desc")
        review_desc.setContentsMargins(dp(24), 0, 0, 0)
        mode_layout.addWidget(review_desc)

        # 自动模式
        self.auto_radio = QRadioButton("自动模式")
        self.auto_radio.setObjectName("mode_radio")
        self.auto_radio.setToolTip("自动应用所有建议并高亮标记，适合快速优化")
        self.mode_group.addButton(self.auto_radio, 1)
        mode_layout.addWidget(self.auto_radio)

        auto_desc = QLabel("自动应用建议并高亮标记，适合快速优化")
        auto_desc.setObjectName("mode_desc")
        auto_desc.setContentsMargins(dp(24), 0, 0, 0)
        mode_layout.addWidget(auto_desc)

        # 计划模式
        self.plan_radio = QRadioButton("计划模式")
        self.plan_radio.setObjectName("mode_radio")
        self.plan_radio.setToolTip("先完成全部分析，然后选择性应用建议")
        self.mode_group.addButton(self.plan_radio, 2)
        mode_layout.addWidget(self.plan_radio)

        plan_desc = QLabel("先完成分析生成报告，用户选择性应用")
        plan_desc.setObjectName("mode_desc")
        plan_desc.setContentsMargins(dp(24), 0, 0, 0)
        mode_layout.addWidget(plan_desc)

        content_layout.addWidget(mode_frame)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.start_btn = QPushButton("开始优化分析")
        self.start_btn.setFixedWidth(dp(140))
        self.start_btn.clicked.connect(self._start_optimization)
        btn_layout.addWidget(self.start_btn)

        content_layout.addLayout(btn_layout)

        self.content_area.setVisible(False)  # 初始隐藏
        layout.addWidget(self.content_area, stretch=1)

        return page

    def _create_progress_page(self) -> QWidget:
        """创建进度页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 思考流
        self.thinking_stream = ThinkingStreamView(parent=page)
        splitter.addWidget(self.thinking_stream)

        # 建议列表区域
        suggestions_widget = QWidget()
        suggestions_layout = QVBoxLayout(suggestions_widget)
        suggestions_layout.setContentsMargins(0, 0, 0, 0)
        suggestions_layout.setSpacing(dp(8))

        # 建议列表头部
        suggestions_header = QHBoxLayout()
        suggestions_title = QLabel("修改建议")
        suggestions_header.addWidget(suggestions_title)
        suggestions_header.addStretch()

        self.apply_high_btn = QPushButton("应用高优先级")
        self.apply_high_btn.setFixedWidth(dp(100))
        self.apply_high_btn.clicked.connect(self._apply_high_priority)
        self.apply_high_btn.setEnabled(False)
        suggestions_header.addWidget(self.apply_high_btn)

        self.apply_all_btn = QPushButton("应用全部")
        self.apply_all_btn.setFixedWidth(dp(80))
        self.apply_all_btn.clicked.connect(self._apply_all)
        self.apply_all_btn.setEnabled(False)
        suggestions_header.addWidget(self.apply_all_btn)

        suggestions_layout.addLayout(suggestions_header)

        # 建议滚动区域
        self.suggestions_scroll = QScrollArea()
        self.suggestions_scroll.setWidgetResizable(True)
        self.suggestions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.suggestions_container = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions_container)
        self.suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self.suggestions_layout.setSpacing(dp(8))
        self.suggestions_layout.addStretch()

        self.suggestions_scroll.setWidget(self.suggestions_container)
        suggestions_layout.addWidget(self.suggestions_scroll, stretch=1)

        splitter.addWidget(suggestions_widget)

        # 设置分割比例
        splitter.setSizes([200, 300])

        layout.addWidget(splitter, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedWidth(dp(80))
        self.stop_btn.clicked.connect(self._stop_optimization)
        btn_layout.addWidget(self.stop_btn)

        # 继续分析按钮（审核模式下使用）
        self.continue_btn = QPushButton("继续分析")
        self.continue_btn.setFixedWidth(dp(100))
        self.continue_btn.clicked.connect(self._continue_analysis)
        self.continue_btn.setVisible(False)  # 初始隐藏
        btn_layout.addWidget(self.continue_btn)

        # 计划模式应用按钮
        self.apply_plan_btn = QPushButton("确认应用选中建议")
        self.apply_plan_btn.setFixedWidth(dp(140))
        self.apply_plan_btn.clicked.connect(self._apply_plan_suggestions)
        self.apply_plan_btn.setVisible(False)  # 初始隐藏
        btn_layout.addWidget(self.apply_plan_btn)

        btn_layout.addStretch()

        back_btn = QPushButton("返回设置")
        back_btn.setFixedWidth(dp(80))
        back_btn.clicked.connect(self._back_to_setup)
        btn_layout.addWidget(back_btn)

        layout.addLayout(btn_layout)

        return page

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()

        if self.header_label:
            self.header_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(16)}px;
                font-weight: bold;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if self.status_label:
            self.status_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        # 空状态样式
        if self.empty_icon_label:
            self.empty_icon_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(32)}px;
                color: {theme_manager.TEXT_TERTIARY};
            """)

        if self.empty_text_label:
            self.empty_text_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: bold;
                color: {theme_manager.TEXT_SECONDARY};
                margin-top: {dp(16)}px;
            """)

        if self.empty_hint2_label:
            self.empty_hint2_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_TERTIARY};
                margin-top: {dp(8)}px;
            """)

        if self.start_btn:
            self.start_btn.setStyleSheet(ButtonStyles.primary())

        if self.stop_btn:
            self.stop_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {theme_manager.ERROR};
                    background-color: transparent;
                    border: 1px solid {theme_manager.ERROR};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.ERROR}20;
                }}
            """)

        btn_style = f"""
            QPushButton {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_DISABLED};
            }}
        """
        if self.apply_high_btn:
            self.apply_high_btn.setStyleSheet(btn_style)
        if self.apply_all_btn:
            self.apply_all_btn.setStyleSheet(btn_style)

        # 三层模式选择框样式
        if self.content_area:
            mode_frame = self.content_area.findChild(QFrame, "mode_frame")
            if mode_frame:
                mode_frame.setStyleSheet(f"""
                    QFrame#mode_frame {{
                        background-color: {theme_manager.BG_SECONDARY};
                        border: 1px solid {theme_manager.BORDER_DEFAULT};
                        border-radius: {dp(8)}px;
                    }}
                """)

            mode_title = self.content_area.findChild(QLabel, "mode_title")
            if mode_title:
                mode_title.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    font-weight: bold;
                    color: {theme_manager.TEXT_PRIMARY};
                """)

            # 单选按钮样式
            radio_style = f"""
                QRadioButton {{
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {theme_manager.TEXT_PRIMARY};
                    spacing: {dp(8)}px;
                }}
                QRadioButton::indicator {{
                    width: {dp(16)}px;
                    height: {dp(16)}px;
                    border: 2px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(8)}px;
                    background-color: {theme_manager.BG_PRIMARY};
                }}
                QRadioButton::indicator:checked {{
                    border-color: {theme_manager.PRIMARY};
                    background-color: {theme_manager.PRIMARY};
                }}
            """
            for radio in [self.review_radio, self.auto_radio, self.plan_radio]:
                if radio:
                    radio.setStyleSheet(radio_style)

            # 模式描述样式
            for desc in self.content_area.findChildren(QLabel, "mode_desc"):
                desc.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                """)

        # 继续分析按钮
        if self.continue_btn:
            self.continue_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {theme_manager.BUTTON_TEXT};
                    background-color: {theme_manager.SUCCESS};
                    border: 1px solid {theme_manager.SUCCESS};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.SUCCESS}dd;
                }}
            """)

        # 计划模式应用按钮
        if self.apply_plan_btn:
            self.apply_plan_btn.setStyleSheet(ButtonStyles.primary())

        if self.suggestions_scroll:
            self.suggestions_scroll.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {theme_manager.scrollbar()}
            """)

    def set_chapter(self, chapter_number: int, content: str):
        """
        设置要优化的章节

        Args:
            chapter_number: 章节号
            content: 章节内容
        """
        logger.info("OptimizationContent.set_chapter: chapter=%s, content_len=%d",
                    chapter_number, len(content) if content else 0)

        self.chapter_number = chapter_number
        self.chapter_content = content

        # 更新段落选择器
        if self.paragraph_selector:
            self.paragraph_selector.set_content(content)
        else:
            logger.warning("paragraph_selector 未初始化!")

        # 显示/隐藏空状态和内容区域
        has_content = bool(content and content.strip())
        logger.info("has_content=%s, empty_hint=%s, content_area=%s",
                    has_content, self.empty_hint is not None, self.content_area is not None)

        if self.empty_hint:
            self.empty_hint.setVisible(not has_content)
            # 根据情况更新空状态提示
            if not has_content and chapter_number is not None:
                # 章节已选择但没有内容
                if self.empty_text_label:
                    self.empty_text_label.setText(f"第{chapter_number}章暂无内容")
                if self.empty_hint2_label:
                    self.empty_hint2_label.setText("请先生成章节内容，或选择一个已生成的版本")
            elif not has_content:
                # 没有选择章节
                if self.empty_text_label:
                    self.empty_text_label.setText("请先在左侧选择一个章节")
                if self.empty_hint2_label:
                    self.empty_hint2_label.setText("选择章节版本后，可以在此进行正文优化分析")
        if self.content_area:
            self.content_area.setVisible(has_content)
            logger.info("content_area.setVisible(%s)", has_content)

        # 更新头部标签
        if self.header_label and chapter_number is not None:
            self.header_label.setText(f"正文优化 - 第{chapter_number}章")

        # 重置状态
        self._reset_state()

        # 切换到设置页
        if self.content_stack:
            self.content_stack.setCurrentIndex(0)

    def _reset_state(self):
        """重置状态"""
        self.suggestions.clear()
        self.plan_mode_suggestions.clear()
        self.is_optimizing = False
        self.session_id = None
        self.current_suggestion_card = None

        # 清空建议列表
        if self.suggestions_layout:
            while self.suggestions_layout.count() > 1:  # 保留stretch
                item = self.suggestions_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # 清空思考流
        if self.thinking_stream:
            self.thinking_stream.clear()

        # 更新按钮状态
        if self.apply_all_btn:
            self.apply_all_btn.setEnabled(False)
        if self.apply_high_btn:
            self.apply_high_btn.setEnabled(False)
        if self.continue_btn:
            self.continue_btn.setVisible(False)
        if self.apply_plan_btn:
            self.apply_plan_btn.setVisible(False)

        self._update_status("")

    def _get_selected_mode(self) -> OptimizationMode:
        """获取当前选择的优化模式"""
        if self.mode_group:
            checked_id = self.mode_group.checkedId()
            if checked_id == 0:
                return OptimizationMode.REVIEW
            elif checked_id == 1:
                return OptimizationMode.AUTO
            elif checked_id == 2:
                return OptimizationMode.PLAN
        return OptimizationMode.REVIEW

    def _start_optimization(self):
        """开始优化分析"""
        if not self.chapter_content or self.chapter_number is None:
            self._update_status("请先选择章节")
            return

        if self.is_optimizing:
            return

        # 获取选择的模式
        self.optimization_mode = self._get_selected_mode()
        logger.info("开始优化分析，模式: %s", self.optimization_mode.value)

        self.is_optimizing = True
        self._reset_state()

        # 切换到进度页
        if self.content_stack:
            self.content_stack.setCurrentIndex(1)

        # 根据模式更新UI
        mode_names = {
            OptimizationMode.REVIEW: "审核模式",
            OptimizationMode.AUTO: "自动模式",
            OptimizationMode.PLAN: "计划模式",
        }
        self._update_status(f"正在分析（{mode_names[self.optimization_mode]}）...")

        # 获取选中的段落
        selected_indices = []
        scope = "full"
        if self.paragraph_selector and self.paragraph_selector.has_selection():
            selected_indices = self.paragraph_selector.get_selected_indices()
            scope = "selected"

        # 构建请求
        payload = {
            "content": self.chapter_content,
            "scope": scope,
            "selected_paragraphs": selected_indices if selected_indices else None,
            "dimensions": None,  # 使用默认维度（全部）
            "mode": self.optimization_mode.value,  # 传递优化模式给后端
        }

        # 启动SSE Worker
        client = AFNAPIClient()
        url = client.get_optimize_chapter_url(self.project_id, self.chapter_number)

        self.sse_worker = SSEWorker(url, payload)
        self.sse_worker.event_received.connect(self._on_sse_event)
        self.sse_worker.error.connect(self._on_sse_error)
        self.sse_worker.complete.connect(self._on_sse_complete)
        self.sse_worker.start()

    def _stop_optimization(self):
        """停止优化"""
        # 取消后端会话
        if self.session_id:
            try:
                client = AFNAPIClient()
                client.cancel_optimization_session(self.session_id)
                logger.info("已取消后端会话: %s", self.session_id)
            except Exception as e:
                logger.warning("取消后端会话失败: %s", e)

        # 停止SSE连接
        if self.sse_worker:
            try:
                self.sse_worker.stop()
            except RuntimeError:
                # C++对象已被删除
                pass
            self.sse_worker = None

        self.is_optimizing = False
        self.session_id = None
        if self.continue_btn:
            self.continue_btn.setVisible(False)
        self._update_status("已停止")

    def _back_to_setup(self):
        """返回设置页"""
        self._stop_optimization()
        if self.content_stack:
            self.content_stack.setCurrentIndex(0)

    def _on_sse_event(self, event_type: str, data: dict):
        """处理SSE事件"""
        # 后端现在负责暂停控制，直接处理所有事件
        self._process_sse_event(event_type, data)

    def _process_sse_event(self, event_type: str, data: dict):
        """实际处理SSE事件"""
        if event_type == "workflow_start":
            # 保存会话ID用于暂停/继续控制
            self.session_id = data.get("session_id", "")
            total = data.get("total_paragraphs", 0)
            dimensions = data.get("dimensions", [])
            if self.thinking_stream:
                self.thinking_stream.on_workflow_start(total, dimensions)

        elif event_type == "workflow_paused":
            # 后端已暂停，等待用户操作
            self._update_status("等待处理建议...")
            if self.thinking_stream:
                self.thinking_stream.on_workflow_paused()
            # 显示继续分析按钮
            if self.continue_btn:
                self.continue_btn.setVisible(True)

        elif event_type == "workflow_resumed":
            # 后端已恢复
            self._update_status("正在分析...")
            if self.thinking_stream:
                self.thinking_stream.on_workflow_resumed()
            # 隐藏继续分析按钮
            if self.continue_btn:
                self.continue_btn.setVisible(False)

        elif event_type == "paragraph_start":
            index = data.get("index", 0)
            preview = data.get("text_preview", "")
            if self.thinking_stream:
                self.thinking_stream.set_current_paragraph(index, preview)

        elif event_type == "thinking":
            content = data.get("content", "")
            step = data.get("step", "")
            if self.thinking_stream:
                self.thinking_stream.add_thinking(content, step)

        elif event_type == "action":
            action = data.get("action", "")
            description = data.get("description", "")
            if self.thinking_stream:
                self.thinking_stream.add_action(action, description)

        elif event_type == "observation":
            result = data.get("result", "")
            relevance = data.get("relevance")
            if self.thinking_stream:
                self.thinking_stream.add_observation(result, relevance)

        elif event_type == "suggestion":
            self._handle_suggestion(data)

        elif event_type == "paragraph_complete":
            pass  # 可以在这里更新进度

        elif event_type == "workflow_complete":
            total = data.get("total_suggestions", 0)
            summary = data.get("summary", "")
            if self.thinking_stream:
                self.thinking_stream.on_workflow_complete(total, summary)
            self._on_workflow_complete(total, summary)

        elif event_type == "error":
            message = data.get("message", "未知错误")
            self._update_status(f"错误: {message}")
            if self.thinking_stream:
                self.thinking_stream.add_error(message)
            logger.error("优化错误: %s", message)

    def _handle_suggestion(self, suggestion: dict):
        """处理建议事件 - 根据模式采取不同行为"""
        self.suggestions.append(suggestion)

        # 创建建议卡片
        card = SuggestionCard(suggestion, parent=self.suggestions_container)
        card.applied.connect(self._on_suggestion_applied)
        card.ignored.connect(self._on_suggestion_ignored)

        # 插入到stretch之前
        if self.suggestions_layout:
            self.suggestions_layout.insertWidget(
                self.suggestions_layout.count() - 1,
                card
            )

        # 在思考流中添加建议提示
        reason = suggestion.get("reason", "发现问题")
        if self.thinking_stream:
            self.thinking_stream.add_suggestion_hint(reason)

        # 根据模式处理
        if self.optimization_mode == OptimizationMode.AUTO:
            # 自动模式：自动应用建议
            card._on_apply()

        elif self.optimization_mode == OptimizationMode.REVIEW:
            # 审核模式：记录当前建议卡片
            # 后端会发送 workflow_paused 事件来更新UI状态
            self.current_suggestion_card = card

        elif self.optimization_mode == OptimizationMode.PLAN:
            # 计划模式：收集建议，分析完成后让用户选择
            self.plan_mode_suggestions.append({
                "suggestion": suggestion,
                "card": card
            })

    def _on_sse_error(self, error_msg: str):
        """处理SSE错误"""
        self.is_optimizing = False
        self._update_status(f"连接错误: {error_msg}")
        if self.thinking_stream:
            self.thinking_stream.add_error(error_msg)
        logger.error("SSE错误: %s", error_msg)

    def _on_sse_complete(self):
        """SSE完成"""
        self.is_optimizing = False
        self.sse_worker = None

        # 启用应用按钮
        if self.suggestions:
            if self.apply_all_btn:
                self.apply_all_btn.setEnabled(True)
            high_count = sum(1 for s in self.suggestions if s.get("priority") == "high")
            if high_count > 0 and self.apply_high_btn:
                self.apply_high_btn.setEnabled(True)

        # 隐藏继续按钮
        if self.continue_btn:
            self.continue_btn.setVisible(False)

    def _on_workflow_complete(self, total_suggestions: int, summary: str):
        """工作流完成回调"""
        self._update_status(summary)
        self.optimization_complete.emit(total_suggestions)

        # 隐藏继续按钮
        if self.continue_btn:
            self.continue_btn.setVisible(False)

        # 计划模式：显示应用按钮
        if self.optimization_mode == OptimizationMode.PLAN:
            if self.apply_plan_btn and self.plan_mode_suggestions:
                self.apply_plan_btn.setVisible(True)
                self._update_status(f"分析完成，共 {total_suggestions} 条建议，请选择要应用的建议")

    def _apply_plan_suggestions(self):
        """计划模式：应用选中的建议"""
        applied_count = 0
        for item in self.plan_mode_suggestions:
            card = item.get("card")
            if card and not card.is_applied and not card.is_ignored:
                card._on_apply()
                applied_count += 1

        self._update_status(f"已应用 {applied_count} 条建议")

        # 隐藏应用按钮
        if self.apply_plan_btn:
            self.apply_plan_btn.setVisible(False)

    def _on_suggestion_applied(self, suggestion: dict):
        """建议被应用"""
        self.suggestion_applied.emit(suggestion)
        logger.info("应用建议: 段落%d", suggestion.get("paragraph_index", -1))

        # 审核模式下，调用后端继续分析
        if self.optimization_mode == OptimizationMode.REVIEW:
            self._resume_backend_analysis()

    def _on_suggestion_ignored(self, suggestion: dict):
        """建议被忽略"""
        logger.info("忽略建议: 段落%d", suggestion.get("paragraph_index", -1))

        # 审核模式下，调用后端继续分析
        if self.optimization_mode == OptimizationMode.REVIEW:
            self._resume_backend_analysis()

    def _resume_backend_analysis(self):
        """通知后端继续分析"""
        if not self.session_id:
            logger.warning("无法继续分析：session_id 为空")
            return

        self.current_suggestion_card = None

        # 调用后端 continue API
        try:
            client = AFNAPIClient()
            result = client.continue_optimization_session(self.session_id)
            logger.info("继续分析: %s", result)
        except Exception as e:
            logger.error("调用 continue API 失败: %s", e)
            self._update_status(f"继续分析失败: {e}")

    def _continue_analysis(self):
        """继续分析（用户点击继续按钮）"""
        # 如果有当前建议卡片且未处理，自动忽略
        if self.current_suggestion_card and not self.current_suggestion_card.is_applied:
            if not self.current_suggestion_card.is_ignored:
                self.current_suggestion_card._on_ignore()
                return  # _on_ignore 会触发 _on_suggestion_ignored，进而调用 _resume_backend_analysis

        # 直接调用后端继续
        self._resume_backend_analysis()

    def _apply_all(self):
        """应用全部建议"""
        for i in range(self.suggestions_layout.count() - 1):  # -1 排除stretch
            item = self.suggestions_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, SuggestionCard) and not card.is_applied and not card.is_ignored:
                    card._on_apply()

    def _apply_high_priority(self):
        """应用高优先级建议"""
        for i in range(self.suggestions_layout.count() - 1):
            item = self.suggestions_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, SuggestionCard) and card.is_high_priority():
                    if not card.is_applied and not card.is_ignored:
                        card._on_apply()

    def _update_status(self, text: str):
        """更新状态文本"""
        if self.status_label:
            self.status_label.setText(text)
