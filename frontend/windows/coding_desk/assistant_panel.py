"""
编程项目助手面板

提供两种模式：
1. RAG查询模式：检索项目上下文
2. Agent规划模式：智能规划目录结构
"""

import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QLabel, QHBoxLayout, QSpinBox, QSizePolicy,
    QPushButton, QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from api.manager import APIClientManager

# 复用灵感模式的输入组件
from windows.inspiration_mode.components import ConversationInput

# Agent规划内容
from windows.coding_desk.agent_content import AgentPlanningContent


logger = logging.getLogger(__name__)


class RAGResultCard(ThemeAwareFrame):
    """RAG检索结果卡片"""

    def __init__(self, data: dict, parent=None):
        """
        Args:
            data: 结果数据，包含 content, score, metadata 等
        """
        self.data = data
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(6))

        # 头部：数据类型 + 相似度分数
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        # 数据类型标签
        data_type = self.data.get('data_type', 'unknown')
        type_display = self._get_type_display(data_type)
        self.type_label = QLabel(type_display)
        self.type_label.setObjectName("type_label")
        header_layout.addWidget(self.type_label)

        # 来源信息
        metadata = self.data.get('metadata', {})
        source_info = self._get_source_info(metadata)
        if source_info:
            self.source_label = QLabel(source_info)
            self.source_label.setObjectName("source_label")
            self.source_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            header_layout.addWidget(self.source_label)

        header_layout.addStretch()

        # 相似度分数
        score = self.data.get('score', 0)
        similarity = max(0, 1 - score) if score <= 1 else score
        self.score_label = QLabel(f"相似度: {similarity:.1%}")
        self.score_label.setObjectName("score_label")
        header_layout.addWidget(self.score_label)

        layout.addLayout(header_layout)

        # 内容区域
        content = self.data.get('content', '')
        display_content = content[:600] + "..." if len(content) > 600 else content

        self.content_label = QLabel(display_content)
        self.content_label.setObjectName("content_label")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.content_label)

    def _get_type_display(self, data_type: str) -> str:
        """获取数据类型的显示文本"""
        type_map = {
            'blueprint': '蓝图',
            'system': '系统',
            'module': '模块',
            'feature': '功能',
            'dependency': '依赖',
            'directory': '目录',
            'file': '文件',
            'tech_stack': '技术栈',
            'requirement': '需求',
            'risk': '风险',
            'milestone': '里程碑',
        }
        return type_map.get(data_type, data_type)

    def _get_source_info(self, metadata: dict) -> str:
        """从元数据中提取来源信息"""
        parts = []
        if metadata.get('system_name'):
            parts.append(f"系统: {metadata['system_name']}")
        if metadata.get('module_name'):
            parts.append(f"模块: {metadata['module_name']}")
        if metadata.get('feature_name'):
            parts.append(f"功能: {metadata['feature_name']}")
        return " | ".join(parts)

    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
            }}
        """)

        if hasattr(self, 'type_label'):
            self.type_label.setStyleSheet(f"""
                font-size: {dp(12)}px;
                font-weight: 600;
                color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY}15;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            """)

        if hasattr(self, 'source_label'):
            self.source_label.setStyleSheet(f"""
                font-size: {dp(11)}px;
                color: {theme_manager.TEXT_TERTIARY};
            """)

        if hasattr(self, 'score_label'):
            self.score_label.setStyleSheet(f"""
                font-size: {dp(11)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: {theme_manager.book_bg_secondary()};
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(3)}px;
            """)

        if hasattr(self, 'content_label'):
            self.content_label.setStyleSheet(f"""
                font-size: {dp(12)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.5;
            """)


class CodingAssistantPanel(ThemeAwareFrame):
    """编程项目助手面板

    提供两种模式：
    1. RAG查询模式：检索项目上下文（功能描述、模块信息、系统架构、技术栈、依赖关系等）
    2. Agent规划模式：智能规划目录结构
    """

    # 信号
    structureUpdated = pyqtSignal(list, list)  # (directories, files) - 来自Agent的结构更新
    planningCompleted = pyqtSignal()  # Agent规划完成
    planningStarted = pyqtSignal()  # Agent规划开始
    refreshTreeRequested = pyqtSignal()  # 请求刷新目录树

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = APIClientManager.get_client()

        # 当前模式: "rag" 或 "agent"
        self.current_mode = "rag"

        # 状态
        self.is_loading = False
        self._worker: Optional[AsyncAPIWorker] = None
        self._result_widgets = []

        # UI组件引用
        self.header_bar = None
        self.mode_container = None
        self.rag_btn = None
        self.agent_btn = None
        self.content_stack = None
        self.rag_content = None
        self.agent_content = None

        # RAG相关组件
        self.topk_spinner = None
        self.scroll_area = None
        self.result_content = None
        self.result_layout = None
        self.input_container = None
        self.input_box = None

        super().__init__(parent)
        self.setupUI()

        # 初始提示
        QTimer.singleShot(500, self._show_welcome_message)

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏（含模式切换）
        self.header_bar = QWidget()
        self.header_bar.setFixedHeight(dp(48))
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(dp(12), 0, dp(12), 0)
        header_layout.setSpacing(dp(8))

        # 模式切换按钮组
        self.mode_container = QWidget()
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(dp(4))

        self.rag_btn = QPushButton("RAG查询")
        self.rag_btn.setObjectName("mode_btn_rag")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rag_btn.clicked.connect(lambda: self._switch_mode("rag"))
        mode_layout.addWidget(self.rag_btn)

        self.agent_btn = QPushButton("目录规划")
        self.agent_btn.setObjectName("mode_btn_agent")
        self.agent_btn.setCheckable(True)
        self.agent_btn.setChecked(False)
        self.agent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agent_btn.clicked.connect(lambda: self._switch_mode("agent"))
        mode_layout.addWidget(self.agent_btn)

        header_layout.addWidget(self.mode_container)
        header_layout.addStretch()

        layout.addWidget(self.header_bar)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        # 内容堆栈（切换RAG和Agent）
        self.content_stack = QStackedWidget()

        # RAG内容
        self.rag_content = self._create_rag_content()
        self.content_stack.addWidget(self.rag_content)

        # Agent内容
        self.agent_content = AgentPlanningContent(self.project_id, self)
        self.agent_content.structureUpdated.connect(self.structureUpdated.emit)
        self.agent_content.planningCompleted.connect(self.planningCompleted.emit)
        self.agent_content.planningStarted.connect(self.planningStarted.emit)
        self.agent_content.refreshTreeRequested.connect(self.refreshTreeRequested.emit)
        self.content_stack.addWidget(self.agent_content)

        layout.addWidget(self.content_stack, stretch=1)

    def _create_rag_content(self) -> QWidget:
        """创建RAG查询内容区域"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # RAG头部（top_k选择器）
        rag_header = QWidget()
        rag_header.setFixedHeight(dp(36))
        rag_header_layout = QHBoxLayout(rag_header)
        rag_header_layout.setContentsMargins(dp(12), 0, dp(12), 0)

        rag_header_layout.addStretch()

        topk_label = QLabel("返回数量:")
        topk_label.setObjectName("topk_label")
        rag_header_layout.addWidget(topk_label)

        self.topk_spinner = QSpinBox()
        self.topk_spinner.setRange(1, 30)
        self.topk_spinner.setValue(10)
        self.topk_spinner.setFixedWidth(dp(60))
        rag_header_layout.addWidget(self.topk_spinner)

        layout.addWidget(rag_header)

        # 结果显示区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.result_content = QWidget()
        self.result_layout = QVBoxLayout(self.result_content)
        self.result_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        self.result_layout.setSpacing(dp(12))
        self.result_layout.addStretch()

        self.scroll_area.setWidget(self.result_content)
        layout.addWidget(self.scroll_area, stretch=1)

        # 输入区域
        self.input_container = QWidget()
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))

        self.input_box = ConversationInput()
        self.input_box.setPlaceholder("输入查询内容，检索项目相关上下文...")
        self.input_box.messageSent.connect(self._on_send_query)

        input_layout.addWidget(self.input_box)
        layout.addWidget(self.input_container)

        return container

    def _switch_mode(self, mode: str):
        """切换模式"""
        if mode == self.current_mode:
            return

        # 如果Agent正在运行，提示用户
        if self.current_mode == "agent" and self.agent_content and self.agent_content.is_running():
            from utils.message_service import MessageService
            MessageService.show_warning(self, "Agent正在运行中，请先停止后再切换")
            # 恢复按钮状态
            self.rag_btn.setChecked(mode != "rag")
            self.agent_btn.setChecked(mode != "agent")
            return

        self.current_mode = mode
        self.rag_btn.setChecked(mode == "rag")
        self.agent_btn.setChecked(mode == "agent")

        # 切换内容
        self.content_stack.setCurrentIndex(0 if mode == "rag" else 1)

        # 更新按钮样式
        self._apply_mode_button_styles()

    def _apply_theme(self):
        """应用主题"""
        bg_color = theme_manager.book_bg_secondary()

        self.setStyleSheet(f"""
            CodingAssistantPanel {{
                background-color: {bg_color};
                border-left: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
        """)

        # 标题栏
        if self.header_bar:
            self.header_bar.setStyleSheet(f"background-color: transparent;")

        # 模式按钮样式
        self._apply_mode_button_styles()

        # top_k spinner
        if self.topk_spinner:
            self.topk_spinner.setStyleSheet(f"""
                QSpinBox {{
                    font-size: {dp(12)}px;
                    color: {theme_manager.TEXT_PRIMARY};
                    background-color: {theme_manager.book_bg_primary()};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    width: {dp(16)}px;
                }}
            """)

        # topk_label 样式
        if self.rag_content:
            topk_label = self.rag_content.findChild(QLabel, "topk_label")
            if topk_label:
                topk_label.setStyleSheet(f"""
                    font-size: {dp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                """)

        # 分割线
        divider = self.findChild(QFrame, "divider")
        if divider:
            divider.setStyleSheet(f"background-color: {theme_manager.BORDER_DEFAULT};")

        # 滚动区域
        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                {theme_manager.scrollbar()}
            """)

        if self.result_content:
            self.result_content.setStyleSheet("background-color: transparent;")

        # 输入区域
        if self.input_container:
            self.input_container.setStyleSheet(f"""
                background-color: {bg_color};
                border-top: 1px solid {theme_manager.BORDER_DEFAULT};
            """)

    def _apply_mode_button_styles(self):
        """应用模式按钮样式"""
        # 根据当前模式设置按钮样式
        active_style = f"""
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
        """

        inactive_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}10;
                color: {theme_manager.PRIMARY};
            }}
        """

        if self.rag_btn:
            self.rag_btn.setStyleSheet(active_style if self.current_mode == "rag" else inactive_style)
        if self.agent_btn:
            self.agent_btn.setStyleSheet(active_style if self.current_mode == "agent" else inactive_style)

    def _show_welcome_message(self):
        """显示欢迎信息"""
        self._clear_results()
        self._add_info_message(
            "RAG 助手",
            "输入查询内容，检索项目相关上下文。\n\n"
            "可查询内容包括：\n"
            "- 功能描述和实现要点\n"
            "- 模块接口和依赖关系\n"
            "- 系统架构和技术栈\n"
            "- 需求和风险分析\n\n"
            "检索结果可帮助生成更准确的文件Prompt。"
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
            self.api_client.query_coding_rag,
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

            # 移除加载提示，保留查询显示
            self._clear_results(keep_query=True)

            # 检查是否有提示信息
            message = response.get('message')
            if message:
                self._add_info_message("提示", message)

            # 显示统计信息
            chunks = response.get('chunks', [])
            summaries = response.get('summaries', [])

            total = len(chunks) + len(summaries)
            if total == 0:
                self._add_info_message("无结果", "未找到相关内容，请尝试其他查询词。")
                return

            stats_text = f"检索完成: {len(chunks)} 个片段"
            if summaries:
                stats_text += f", {len(summaries)} 个摘要"
            self._add_stats_label(stats_text)

            # 显示检索结果
            all_results = chunks + summaries
            # 按相似度排序（score越小越相似）
            all_results.sort(key=lambda x: x.get('score', 1))

            # 限制显示数量
            display_results = all_results[:20]
            for data in display_results:
                card = RAGResultCard(data, self.result_content)
                self.result_layout.insertWidget(self.result_layout.count() - 1, card)
                self._result_widgets.append(card)

            if len(all_results) > 20:
                self._add_info_message("", f"(仅显示前20个，共{len(all_results)}个)")

            self._scroll_to_top()

            # 设置焦点回输入框
            if hasattr(self.input_box, 'input_field') and self.input_box.input_field:
                self.input_box.input_field.setFocus()

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

        if hasattr(self.input_box, 'input_field') and self.input_box.input_field:
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

        # 收集需要删除的widget
        widgets_to_delete = []
        query_widget = None

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

        for widget in widgets_to_delete:
            self.result_layout.removeWidget(widget)
            widget.deleteLater()

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
            font-size: {dp(11)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(label)

        query_label = QLabel(query)
        query_label.setWordWrap(True)
        query_label.setStyleSheet(f"""
            font-size: {dp(12)}px;
            color: {theme_manager.TEXT_PRIMARY};
            background-color: {theme_manager.book_bg_primary()};
            border: 1px solid {theme_manager.BORDER_DEFAULT};
            border-radius: {dp(6)}px;
            padding: {dp(12)}px;
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

        if title:
            title_label = QLabel(title)
            title_color = theme_manager.ERROR if is_error else theme_manager.PRIMARY
            title_label.setStyleSheet(f"""
                font-size: {dp(13)}px;
                font-weight: 600;
                color: {title_color};
            """)
            layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            font-size: {dp(12)}px;
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
            font-size: {dp(11)}px;
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
                self._worker.wait(3000)
        except RuntimeError:
            pass
        finally:
            self._worker = None

    def cleanup(self):
        """清理资源"""
        self._cleanup_worker()
        self._clear_results()
        if self.agent_content:
            self.agent_content.cleanup()

    def set_has_directories(self, has_directories: bool):
        """设置是否有目录结构（用于Agent优化按钮显示）"""
        if self.agent_content:
            self.agent_content.set_has_directories(has_directories)

    def switch_to_agent_mode(self):
        """切换到Agent模式"""
        self._switch_mode("agent")


__all__ = ["CodingAssistantPanel"]
