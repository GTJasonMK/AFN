"""
写作台助手面板

支持两种模式：
1. RAG查询 - 测试向量检索效果
2. 正文优化 - Agent分析正文并提供修改建议
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QLabel, QHBoxLayout, QSpinBox, QSizePolicy,
    QPushButton, QStackedWidget, QButtonGroup,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from utils.constants import WorkerTimeouts
from api.manager import APIClientManager

# 复用灵感模式的输入组件
from windows.inspiration_mode.components import ConversationInput

# 优化模式组件
from .optimization_content import OptimizationContent


logger = logging.getLogger(__name__)


class RAGResultCard(TransparencyAwareMixin, ThemeAwareFrame):
    """RAG检索结果卡片

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符
    _transparency_component_id = "card"

    def __init__(self, result_type: str, data: dict, parent=None):
        """
        Args:
            result_type: 结果类型 "chunk" 或 "summary"
            data: 结果数据
        """
        self.result_type = result_type
        self.data = data
        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 修正：10不符合8pt网格
        layout.setSpacing(dp(6))

        # 头部：章节信息 + 相似度分数
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        # 章节标签
        chapter_num = self.data.get('chapter_number', 0)
        chapter_title = self.data.get('chapter_title') or self.data.get('title', '')
        chapter_text = f"第{chapter_num}章"
        if chapter_title:
            # 限制标题长度，避免溢出
            display_title = chapter_title[:20] + "..." if len(chapter_title) > 20 else chapter_title
            chapter_text += f" {display_title}"

        self.chapter_label = QLabel(chapter_text)
        self.chapter_label.setObjectName("chapter_label")
        # 允许标签收缩
        self.chapter_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        header_layout.addWidget(self.chapter_label)

        header_layout.addStretch()

        # 相似度分数（距离越小越相似）
        score = self.data.get('score', 0)
        similarity = max(0, 1 - score)  # 转换为相似度百分比
        self.score_label = QLabel(f"相似度: {similarity:.1%}")
        self.score_label.setObjectName("score_label")
        header_layout.addWidget(self.score_label)

        layout.addLayout(header_layout)

        # 内容区域
        if self.result_type == "chunk":
            content = self.data.get('content', '')
        else:  # summary
            content = self.data.get('summary', '')

        # 限制显示长度
        display_content = content
        if len(content) > 500:
            display_content = content[:500] + "..."

        self.content_label = QLabel(display_content)
        self.content_label.setObjectName("content_label")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.content_label)

        # 元数据（仅chunk有）
        if self.result_type == "chunk":
            metadata = self.data.get('metadata', {})
            if metadata:
                meta_text = " | ".join(f"{k}: {v}" for k, v in metadata.items() if v)
                if meta_text:
                    self.meta_label = QLabel(meta_text)
                    self.meta_label.setObjectName("meta_label")
                    self.meta_label.setWordWrap(True)  # 允许换行
                    layout.addWidget(self.meta_label)

    def _apply_theme(self):
        """应用主题 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        ui_font = theme_manager.ui_font()

        # 卡片背景 - 支持透明效果
        if self._transparency_enabled:
            bg_rgba = self._hex_to_rgba(theme_manager.BG_PRIMARY, self._current_opacity)
            border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_MEDIUM)

            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                background-color: {bg_rgba};
                border: 1px solid {border_rgba};
                border-radius: {dp(6)}px;
            """)
            self._make_widget_transparent(self)
        else:
            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
            """)

        # 章节标签
        if hasattr(self, 'chapter_label'):
            self.chapter_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.ACCENT_PRIMARY};
            """)

        # 分数标签
        if hasattr(self, 'score_label'):
            self.score_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                color: {theme_manager.TEXT_SECONDARY};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(3)}px;
            """)

        # 内容标签
        if hasattr(self, 'content_label'):
            self.content_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.5;
            """)

        # 元数据标签
        if hasattr(self, 'meta_label'):
            self.meta_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                color: {theme_manager.TEXT_TERTIARY};
            """)


class RAGResultSection(ThemeAwareWidget):
    """RAG结果分组（剧情片段或章节摘要）"""

    def __init__(self, title: str, result_type: str, results: list, parent=None):
        self.title = title
        self.result_type = result_type
        self.results = results
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 标题
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("section_title")
        title_layout.addWidget(self.title_label)

        self.count_label = QLabel(f"({len(self.results)}条)")
        self.count_label.setObjectName("count_label")
        title_layout.addWidget(self.count_label)

        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 结果卡片
        for data in self.results:
            card = RAGResultCard(self.result_type, data, self)
            layout.addWidget(card)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()

        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if hasattr(self, 'count_label'):
            self.count_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_SECONDARY};
            """)


class AssistantPanel(TransparencyAwareMixin, ThemeAwareFrame):
    """写作台右侧助手面板 - 支持RAG查询和正文优化两种模式

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符 - 作为侧边面板
    _transparency_component_id = "sidebar"

    # 信号
    suggestion_applied = pyqtSignal(dict)  # 建议被应用

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = APIClientManager.get_client()

        # 当前模式
        self.current_mode = "rag"  # "rag" 或 "optimize"

        # 状态
        self.is_loading = False
        self._worker = None  # 异步Worker引用
        self._result_widgets = []  # 结果组件引用

        # 模式切换组件
        self.mode_switch_container = None
        self.rag_btn = None
        self.optimize_btn = None
        self.content_stack = None

        # RAG模式组件
        self.rag_content = None
        self.header_bar = None
        self.topk_spinner = None
        self.divider = None
        self.scroll_area = None
        self.result_content = None
        self.result_layout = None
        self.input_container = None
        self.input_box = None

        # 优化模式组件
        self.optimization_content = None

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态

        # 注意：宽度由父组件 main.py 通过 setFixedWidth() 控制
        # 此处不再设置 SizePolicy，避免冲突

        self.setupUI()

        # 初始提示
        QTimer.singleShot(500, self._show_welcome_message)

    def _create_ui_structure(self):
        """创建 UI 结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 模式切换按钮
        self.mode_switch_container = QWidget()
        self.mode_switch_container.setFixedHeight(dp(48))
        switch_layout = QHBoxLayout(self.mode_switch_container)
        switch_layout.setContentsMargins(dp(16), dp(8), dp(16), dp(8))
        switch_layout.setSpacing(dp(8))

        self.rag_btn = QPushButton("RAG查询")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.clicked.connect(lambda: self._switch_mode("rag"))
        switch_layout.addWidget(self.rag_btn)

        self.optimize_btn = QPushButton("正文优化")
        self.optimize_btn.setCheckable(True)
        self.optimize_btn.clicked.connect(lambda: self._switch_mode("optimize"))
        switch_layout.addWidget(self.optimize_btn)

        switch_layout.addStretch()
        layout.addWidget(self.mode_switch_container)

        # 模式分割线
        mode_divider = QFrame()
        mode_divider.setFrameShape(QFrame.Shape.HLine)
        mode_divider.setFixedHeight(1)
        mode_divider.setStyleSheet(f"background-color: {theme_manager.BORDER_LIGHT};")
        layout.addWidget(mode_divider)

        # 2. 内容区域（使用堆叠组件）
        self.content_stack = QStackedWidget()

        # RAG模式内容
        self.rag_content = self._create_rag_content()
        self.content_stack.addWidget(self.rag_content)

        # 优化模式内容
        self.optimization_content = OptimizationContent(self.project_id, parent=self)
        self.optimization_content.suggestion_applied.connect(self._on_suggestion_applied)
        self.content_stack.addWidget(self.optimization_content)

        layout.addWidget(self.content_stack, stretch=1)

    def _create_rag_content(self) -> QWidget:
        """创建RAG查询模式的内容"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        self.header_bar = QWidget()
        self.header_bar.setFixedHeight(dp(48))
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(dp(16), 0, dp(16), 0)

        title_label = QLabel("RAG 助手")
        title_label.setObjectName("assistant_title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # top_k 选择器
        topk_label = QLabel("返回数量:")
        topk_label.setObjectName("topk_label")
        header_layout.addWidget(topk_label)

        self.topk_spinner = QSpinBox()
        self.topk_spinner.setRange(1, 50)
        self.topk_spinner.setValue(10)
        self.topk_spinner.setFixedWidth(dp(60))
        header_layout.addWidget(self.topk_spinner)

        layout.addWidget(self.header_bar)

        # 分割线
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFixedHeight(1)
        layout.addWidget(self.divider)

        # 结果显示区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.result_content = QWidget()
        self.result_layout = QVBoxLayout(self.result_content)
        self.result_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        self.result_layout.setSpacing(dp(16))
        self.result_layout.addStretch()

        self.scroll_area.setWidget(self.result_content)
        layout.addWidget(self.scroll_area, stretch=1)

        # 输入区域
        self.input_container = QWidget()
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(16))

        self.input_box = ConversationInput()
        self.input_box.setPlaceholder("输入查询文本，测试RAG检索效果...")
        self.input_box.messageSent.connect(self._on_send_query)

        input_layout.addWidget(self.input_box)
        layout.addWidget(self.input_container)

        return container

    def _switch_mode(self, mode: str):
        """切换模式"""
        if self.current_mode == mode:
            return

        self.current_mode = mode

        # 更新按钮状态
        if self.rag_btn:
            self.rag_btn.setChecked(mode == "rag")
        if self.optimize_btn:
            self.optimize_btn.setChecked(mode == "optimize")

        # 切换内容
        if self.content_stack:
            self.content_stack.setCurrentIndex(0 if mode == "rag" else 1)

    def set_chapter_for_optimization(self, chapter_number: int, content: str):
        """
        设置要优化的章节（供外部调用）

        Args:
            chapter_number: 章节号
            content: 章节内容
        """
        if self.optimization_content:
            self.optimization_content.set_chapter(chapter_number, content)
        # 不自动切换模式，让用户手动选择

    def _on_suggestion_applied(self, suggestion: dict):
        """处理建议被应用"""
        self.suggestion_applied.emit(suggestion)

    def _apply_theme(self):
        """应用主题 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        ui_font = theme_manager.ui_font()

        # 背景 - 支持透明效果
        if self._transparency_enabled:
            bg_style = self._get_transparent_bg(
                theme_manager.BG_SECONDARY,
                border_color=theme_manager.BORDER_LIGHT,
                border_opacity=OpacityTokens.BORDER_LIGHT
            )

            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                {bg_style}
                border-left: 1px solid {self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_LIGHT)};
            """)

            # 确保子组件背景透明
            if self.mode_switch_container:
                self.mode_switch_container.setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.mode_switch_container)

            if self.rag_content:
                self.rag_content.setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.rag_content)

            if self.header_bar:
                self.header_bar.setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.header_bar)

            # 滚动区域透明
            if self.scroll_area:
                self.scroll_area.setStyleSheet("""
                    QScrollArea {
                        background-color: transparent;
                        border: none;
                    }
                    QScrollArea > QWidget > QWidget {
                        background-color: transparent;
                    }
                """)
                self.scroll_area.viewport().setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.scroll_area.viewport())

            if self.result_content:
                self.result_content.setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.result_content)

            # 输入区域半透明
            if self.input_container:
                input_opacity = self._current_opacity * 0.8
                input_bg_rgba = self._hex_to_rgba(theme_manager.BG_SECONDARY, input_opacity)
                border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_MEDIUM)
                self.input_container.setStyleSheet(f"""
                    background-color: {input_bg_rgba};
                    border-top: 1px solid {border_rgba};
                """)
                self._make_widget_transparent(self.input_container)

            # content_stack透明
            if self.content_stack:
                self.content_stack.setStyleSheet("background-color: transparent;")
        else:
            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                background-color: {theme_manager.BG_SECONDARY};
                border-left: 1px solid {theme_manager.BORDER_LIGHT};
            """)

        # 模式切换按钮样式
        mode_btn_style = f"""
            QPushButton {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
            }}
            QPushButton:checked {{
                color: {theme_manager.BUTTON_TEXT};
                background-color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """
        if self.rag_btn:
            self.rag_btn.setStyleSheet(mode_btn_style)
        if self.optimize_btn:
            self.optimize_btn.setStyleSheet(mode_btn_style)

        # 标题栏
        if self.header_bar:
            title_label = self.header_bar.findChild(QLabel, "assistant_title")
            if title_label:
                title_label.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_MD};
                    font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                    color: {theme_manager.TEXT_PRIMARY};
                """)

            topk_label = self.header_bar.findChild(QLabel, "topk_label")
            if topk_label:
                topk_label.setStyleSheet(f"""
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {theme_manager.TEXT_SECONDARY};
                """)

        # top_k spinner
        if self.topk_spinner:
            self.topk_spinner.setStyleSheet(f"""
                QSpinBox {{
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {theme_manager.TEXT_PRIMARY};
                    background-color: {theme_manager.BG_PRIMARY};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    width: {dp(16)}px;
                }}
            """)

        # 分割线
        if self.divider:
            self.divider.setStyleSheet(f"background-color: {theme_manager.BORDER_LIGHT};")

        # 滚动区域
        if self.scroll_area:
            self.scroll_area.setStyleSheet("background-color: transparent;")
        if self.result_content:
            self.result_content.setStyleSheet("background-color: transparent;")

        # 输入区域
        if self.input_container:
            self.input_container.setStyleSheet(f"""
                background-color: {theme_manager.BG_SECONDARY};
                border-top: 1px solid {theme_manager.BORDER_LIGHT};
            """)

    def _show_welcome_message(self):
        """显示欢迎/说明信息"""
        self._clear_results()
        self._add_info_message(
            "RAG助手",
            "输入查询文本，测试向量检索效果。\n\n"
            "系统会返回与查询最相关的剧情片段和章节摘要，"
            "并显示相似度分数（越高越相关）。\n\n"
            "注意：需要先有已选定的章节内容才能检索。"
        )

    def _on_send_query(self, text: str):
        """处理查询请求"""
        if not text.strip() or self.is_loading:
            return

        # 清空之前的结果
        self._clear_results()

        # 显示查询文本
        self._add_query_display(text)

        # 禁用输入
        self.input_box.setEnabled(False)
        self.is_loading = True

        # 显示加载状态
        self._add_info_message("正在检索...", "正在生成查询向量并检索相关内容...")

        # 异步请求
        self._cleanup_worker()

        top_k = self.topk_spinner.value()
        self._worker = AsyncAPIWorker(
            self.api_client.query_rag,
            self.project_id,
            text,
            top_k
        )
        self._worker.success.connect(self._on_query_success)
        self._worker.error.connect(self._on_query_error)
        self._worker.start()

    def _on_query_success(self, response: dict):
        """处理查询成功"""
        try:
            self.is_loading = False
            self.input_box.setEnabled(True)

            # 移除加载提示
            self._clear_results(keep_query=True)

            # 检查是否有提示信息
            message = response.get('message')
            if message:
                self._add_info_message("提示", message)

            # 显示统计信息
            chunks = response.get('chunks', [])
            summaries = response.get('summaries', [])
            dimension = response.get('embedding_dimension')

            stats_text = f"检索完成: {len(chunks)}个片段, {len(summaries)}个摘要"
            if dimension:
                stats_text += f" (向量维度: {dimension})"
            self._add_stats_label(stats_text)

            # 显示剧情片段（限制数量避免UI卡顿）
            if chunks:
                display_chunks = chunks[:20]  # 最多显示20个
                section = RAGResultSection("剧情片段", "chunk", display_chunks, self.result_content)
                self.result_layout.insertWidget(self.result_layout.count() - 1, section)
                self._result_widgets.append(section)
                if len(chunks) > 20:
                    self._add_info_message("", f"(仅显示前20个，共{len(chunks)}个)")

            # 显示章节摘要（限制数量避免UI卡顿）
            if summaries:
                display_summaries = summaries[:20]  # 最多显示20个
                section = RAGResultSection("章节摘要", "summary", display_summaries, self.result_content)
                self.result_layout.insertWidget(self.result_layout.count() - 1, section)
                self._result_widgets.append(section)

            # 安全地设置焦点
            if hasattr(self.input_box, 'input_field') and self.input_box.input_field:
                self.input_box.input_field.setFocus()

            self._scroll_to_top()

        except Exception as e:
            logger.error("处理RAG查询结果时出错: %s", e, exc_info=True)
            self._add_info_message("显示错误", f"处理结果时出错: {str(e)}", is_error=True)

    def _on_query_error(self, error_msg: str):
        """处理查询错误"""
        self.is_loading = False
        self.input_box.setEnabled(True)

        # 移除加载提示
        self._clear_results(keep_query=True)

        self._add_info_message("查询失败", error_msg, is_error=True)
        self.input_box.input_field.setFocus()

    def _clear_results(self, keep_query: bool = False):
        """清空结果区域"""
        # 清理结果组件引用
        for widget in self._result_widgets:
            try:
                widget.deleteLater()
            except RuntimeError:
                pass
        self._result_widgets.clear()

        # 收集需要保留和删除的widget
        widgets_to_delete = []
        query_widget = None

        # 遍历布局中的所有组件（除了最后的stretch）
        for i in range(self.result_layout.count() - 1):
            item = self.result_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue

            if keep_query and widget.objectName() == "query_display":
                query_widget = widget
            else:
                widgets_to_delete.append(widget)

        # 删除需要删除的widget
        for widget in widgets_to_delete:
            self.result_layout.removeWidget(widget)
            widget.deleteLater()

        # 如果保留了query_widget，确保它还在_result_widgets列表中
        if query_widget:
            self._result_widgets.append(query_widget)

    def _add_query_display(self, query: str):
        """显示查询文本"""
        container = QWidget()
        container.setObjectName("query_display")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, dp(8))
        layout.setSpacing(dp(4))

        label = QLabel("查询:")
        label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {theme_manager.FONT_SIZE_XS};
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(label)

        query_label = QLabel(query)
        query_label.setWordWrap(True)
        query_label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {theme_manager.FONT_SIZE_SM};
            color: {theme_manager.TEXT_PRIMARY};
            background-color: {theme_manager.BG_PRIMARY};
            border: 1px solid {theme_manager.BORDER_LIGHT};
            border-radius: {dp(6)}px;
            padding: {dp(12)}px;  /* 修正：10不符合8pt网格 */
        """)
        layout.addWidget(query_label)

        self.result_layout.insertWidget(0, container)
        self._result_widgets.append(container)

    def _add_info_message(self, title: str, message: str, is_error: bool = False):
        """添加信息消息"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        title_label = QLabel(title)
        title_color = theme_manager.ERROR if is_error else theme_manager.ACCENT_PRIMARY
        title_label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {theme_manager.FONT_SIZE_SM};
            font-weight: {theme_manager.FONT_WEIGHT_BOLD};
            color: {title_color};
        """)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {theme_manager.FONT_SIZE_SM};
            color: {theme_manager.TEXT_SECONDARY};
            line-height: 1.6;
        """)
        layout.addWidget(msg_label)

        self.result_layout.insertWidget(self.result_layout.count() - 1, container)
        self._result_widgets.append(container)

    def _add_stats_label(self, text: str):
        """添加统计标签"""
        label = QLabel(text)
        label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {theme_manager.FONT_SIZE_XS};
            color: {theme_manager.TEXT_TERTIARY};
            padding: {dp(4)}px 0;
        """)
        self.result_layout.insertWidget(self.result_layout.count() - 1, label)
        self._result_widgets.append(label)

    def _scroll_to_top(self):
        """滚动到顶部"""
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def _cleanup_worker(self):
        """清理异步Worker"""
        if self._worker is None:
            return

        try:
            if self._worker.isRunning():
                self._worker.cancel()
                self._worker.quit()
                self._worker.wait(WorkerTimeouts.DEFAULT_MS)
        except RuntimeError:
            pass
        finally:
            self._worker = None

    def cleanup(self):
        """清理资源"""
        self._cleanup_worker()
        self._clear_results()
        super().cleanup()
