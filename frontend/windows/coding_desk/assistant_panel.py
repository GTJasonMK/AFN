"""
CodingDesk 助手面板

提供RAG检索功能，查询项目相关上下文（功能描述、模块信息等）
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QTextEdit, QScrollArea, QSpinBox, QFrame,
)
from PyQt6.QtCore import Qt

from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class RAGResultCard(ThemeAwareFrame):
    """RAG检索结果卡片（主题感知）"""

    def __init__(self, result_type: str, data: dict, parent=None):
        self.result_type = result_type
        self.data = data
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("rag_result_card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(6))

        # 头部
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        # 来源标签 - 优先使用source（chapter_title），其次使用chapter_number
        source = self.data.get('source', '')
        chapter_num = self.data.get('chapter_number', 0)
        data_type = self.data.get('data_type', '')

        # 根据数据类型生成合适的来源显示
        if source:
            source_text = source[:25] + "..." if len(source) > 25 else source
        elif chapter_num:
            type_prefix = {
                'feature_prompt': 'F',
                'feature_outline': 'FO',
                'system': 'S',
                'module': 'M',
                'inspiration': 'R',
                'architecture': 'A',
                'tech_stack': 'T',
                'requirement': 'Req',
                'challenge': 'Ch',
                'dependency': 'D',
            }.get(data_type, 'F')
            source_text = f"{type_prefix}{chapter_num}"
        else:
            type_names = {
                'inspiration': '灵感对话',
                'architecture': '架构设计',
                'tech_stack': '技术栈',
                'requirement': '核心需求',
                'challenge': '技术挑战',
                'system': '系统划分',
                'module': '模块定义',
                'feature_outline': '功能大纲',
                'dependency': '依赖关系',
                'feature_prompt': '功能Prompt',
            }
            source_text = type_names.get(data_type, data_type or "未知来源")

        source_label = QLabel(source_text)
        source_label.setObjectName("source_label")
        header_layout.addWidget(source_label)

        # 数据类型标签
        if data_type:
            type_names = {
                'inspiration': '对话',
                'architecture': '架构',
                'tech_stack': '技术栈',
                'requirement': '需求',
                'challenge': '挑战',
                'system': '系统',
                'module': '模块',
                'feature_outline': '大纲',
                'dependency': '依赖',
                'feature_prompt': 'Prompt',
            }
            type_text = type_names.get(data_type, data_type)
            type_label = QLabel(type_text)
            type_label.setObjectName("type_label")
            header_layout.addWidget(type_label)

        header_layout.addStretch()

        # 相似度分数
        score = self.data.get('score', 0)
        similarity = max(0, 1 - score) if score < 1 else score
        score_label = QLabel(f"相似度: {similarity:.1%}")
        score_label.setObjectName("score_label")
        header_layout.addWidget(score_label)

        layout.addLayout(header_layout)

        # 内容
        content = self.data.get('content', '') or self.data.get('summary', '')
        display_content = content[:500] + "..." if len(content) > 500 else content

        content_label = QLabel(display_content)
        content_label.setObjectName("content_label")
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content_label)

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#rag_result_card {{
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
            }}
            QLabel#source_label {{
                font-size: {dp(11)}px;
                font-weight: bold;
                color: {theme_manager.PRIMARY};
            }}
            QLabel#type_label {{
                font-size: {dp(10)}px;
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BG_SECONDARY};
                padding: {dp(1)}px {dp(4)}px;
                border-radius: {dp(2)}px;
            }}
            QLabel#score_label {{
                font-size: {dp(10)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#content_label {{
                font-size: {dp(12)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.5;
            }}
        """)


class CodingAssistantPanel(ThemeAwareFrame):
    """编程项目助手面板 - RAG检索（主题感知）"""

    def __init__(self, parent=None):
        # 初始化所有组件引用
        self.api_client = APIClientManager.get_client()
        self.project_id = None
        self.is_loading = False
        self._worker = None
        self._result_widgets = []
        # UI组件引用
        self.sync_btn = None
        self.rebuild_btn = None
        self.topk_spinner = None
        self.rag_input = None
        self.search_btn = None
        self.rag_results = None
        self.rag_results_layout = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("coding_assistant_panel")
        self.setFixedWidth(dp(320))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setFixedHeight(dp(48))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))

        title_label = QLabel("RAG检索")
        title_label.setObjectName("panel_title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()
        layout.addWidget(header)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme_manager.BORDER_LIGHT};")
        layout.addWidget(divider)

        # RAG内容
        rag_content = self._create_rag_content()
        layout.addWidget(rag_content, 1)

    def _create_rag_content(self) -> QWidget:
        """创建RAG检索内容"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = QWidget()
        toolbar.setFixedHeight(dp(44))
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(dp(12), 0, dp(12), 0)

        toolbar_layout.addStretch()

        # 入库按钮
        self.sync_btn = QPushButton("同步RAG")
        self.sync_btn.setObjectName("sync_btn")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setToolTip("智能同步：检查完整性，仅入库缺失的数据类型")
        self.sync_btn.clicked.connect(self._on_sync_rag)
        toolbar_layout.addWidget(self.sync_btn)

        self.rebuild_btn = QPushButton("重建")
        self.rebuild_btn.setObjectName("rebuild_btn")
        self.rebuild_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rebuild_btn.setToolTip("强制重建：重新入库所有数据")
        self.rebuild_btn.clicked.connect(self._on_force_rebuild)
        toolbar_layout.addWidget(self.rebuild_btn)

        topk_label = QLabel("数量:")
        topk_label.setObjectName("topk_label")
        toolbar_layout.addWidget(topk_label)

        self.topk_spinner = QSpinBox()
        self.topk_spinner.setRange(1, 20)
        self.topk_spinner.setValue(5)
        self.topk_spinner.setFixedWidth(dp(50))
        toolbar_layout.addWidget(self.topk_spinner)

        layout.addWidget(toolbar)

        # 输入区域
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        input_layout.setSpacing(dp(8))

        self.rag_input = QTextEdit()
        self.rag_input.setObjectName("rag_input")
        self.rag_input.setPlaceholderText("输入查询内容，检索相关上下文...")
        self.rag_input.setFixedHeight(dp(80))
        input_layout.addWidget(self.rag_input)

        self.search_btn = QPushButton("检索")
        self.search_btn.setObjectName("search_btn")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._on_search)
        input_layout.addWidget(self.search_btn)

        layout.addWidget(input_container)

        # 结果区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            {theme_manager.scrollbar()}
        """)

        self.rag_results = QWidget()
        self.rag_results.setStyleSheet("background: transparent;")
        self.rag_results_layout = QVBoxLayout(self.rag_results)
        self.rag_results_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(12))
        self.rag_results_layout.setSpacing(dp(8))
        self.rag_results_layout.addStretch()

        scroll.setWidget(self.rag_results)
        layout.addWidget(scroll, 1)

        return container

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        logger.info("CodingAssistantPanel.setProjectId: project_id=%s", project_id)
        self.project_id = project_id

    def _on_sync_rag(self):
        """智能同步RAG数据"""
        if not self.project_id:
            MessageService.show_warning(self, "项目未加载")
            return

        if self.is_loading:
            return

        self.is_loading = True
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("同步中...")
        self.rebuild_btn.setEnabled(False)

        self._cleanup_worker()

        self._worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            False  # force=False
        )
        self._worker.success.connect(self._on_sync_success)
        self._worker.error.connect(self._on_sync_error)
        self._worker.start()

    def _on_sync_success(self, response: dict):
        """同步成功"""
        self.is_loading = False
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("同步RAG")
        self.rebuild_btn.setEnabled(True)

        is_complete = response.get('is_complete', False)
        added = response.get('added', 0)
        skipped = response.get('skipped', 0)
        failed = response.get('failed', 0)

        if is_complete:
            MessageService.show_success(self, "RAG数据已完整，无需同步")
        elif failed == 0:
            if added > 0:
                msg = f"同步完成：新增 {added} 条"
                if skipped > 0:
                    msg += f"，跳过 {skipped} 类型"
                MessageService.show_success(self, msg)
            else:
                MessageService.show_success(self, "RAG数据已完整")
        else:
            MessageService.show_warning(self, f"同步完成：成功 {added}，失败 {failed}")

    def _on_sync_error(self, error_msg: str):
        """同步失败"""
        self.is_loading = False
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("同步RAG")
        self.rebuild_btn.setEnabled(True)
        MessageService.show_error(self, f"同步失败：{error_msg}")

    def _on_force_rebuild(self):
        """强制重建RAG数据"""
        if not self.project_id:
            MessageService.show_warning(self, "项目未加载")
            return

        if self.is_loading:
            return

        self.is_loading = True
        self.rebuild_btn.setEnabled(False)
        self.rebuild_btn.setText("重建中...")
        self.sync_btn.setEnabled(False)

        self._cleanup_worker()

        self._worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            True  # force=True
        )
        self._worker.success.connect(self._on_rebuild_success)
        self._worker.error.connect(self._on_rebuild_error)
        self._worker.start()

    def _on_rebuild_success(self, response: dict):
        """重建成功"""
        self.is_loading = False
        self.rebuild_btn.setEnabled(True)
        self.rebuild_btn.setText("重建")
        self.sync_btn.setEnabled(True)

        added = response.get('added', 0)
        failed = response.get('failed', 0)

        if failed == 0:
            MessageService.show_success(self, f"重建完成：更新 {added} 条记录")
        else:
            MessageService.show_warning(self, f"重建完成：成功 {added}，失败 {failed}")

    def _on_rebuild_error(self, error_msg: str):
        """重建失败"""
        self.is_loading = False
        self.rebuild_btn.setEnabled(True)
        self.rebuild_btn.setText("重建")
        self.sync_btn.setEnabled(True)
        MessageService.show_error(self, f"重建失败：{error_msg}")

    def _on_search(self):
        """执行RAG检索"""
        query = self.rag_input.toPlainText().strip()
        if not query:
            MessageService.show_warning(self, "请输入查询内容")
            return

        if not self.project_id:
            MessageService.show_warning(self, "项目未加载")
            return

        if self.is_loading:
            return

        self._clear_rag_results()
        self.is_loading = True
        self.search_btn.setEnabled(False)
        self.search_btn.setText("检索中...")

        self._cleanup_worker()

        top_k = self.topk_spinner.value()
        self._worker = AsyncAPIWorker(
            self.api_client.query_coding_rag,
            self.project_id,
            query,
            top_k
        )
        self._worker.success.connect(self._on_search_success)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_search_success(self, response: dict):
        """检索成功"""
        self.is_loading = False
        self.search_btn.setEnabled(True)
        self.search_btn.setText("检索")

        chunks = response.get('chunks', [])
        summaries = response.get('summaries', [])

        if not chunks and not summaries:
            self._add_rag_message("未找到相关内容", "尝试使用不同的关键词进行检索")
            return

        if chunks:
            self._add_rag_section("相关片段", chunks, "chunk")
        if summaries:
            self._add_rag_section("相关摘要", summaries, "summary")

    def _on_search_error(self, error_msg: str):
        """检索失败"""
        self.is_loading = False
        self.search_btn.setEnabled(True)
        self.search_btn.setText("检索")
        self._add_rag_message("检索失败", error_msg, is_error=True)

    def _add_rag_section(self, title: str, results: list, result_type: str):
        """添加RAG结果分组"""
        title_label = QLabel(f"{title} ({len(results)})")
        title_label.setObjectName("result_section_title")
        title_label.setStyleSheet(f"""
            font-size: {dp(13)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
            padding: {dp(4)}px 0;
        """)
        self.rag_results_layout.insertWidget(self.rag_results_layout.count() - 1, title_label)
        self._result_widgets.append(title_label)

        for data in results[:10]:
            card = RAGResultCard(result_type, data, self.rag_results)
            self.rag_results_layout.insertWidget(self.rag_results_layout.count() - 1, card)
            self._result_widgets.append(card)

    def _add_rag_message(self, title: str, message: str, is_error: bool = False):
        """添加RAG消息"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        title_label = QLabel(title)
        title_color = theme_manager.ERROR if is_error else theme_manager.PRIMARY
        title_label.setStyleSheet(f"""
            font-size: {dp(13)}px;
            font-weight: bold;
            color: {title_color};
        """)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            font-size: {dp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(msg_label)

        self.rag_results_layout.insertWidget(self.rag_results_layout.count() - 1, container)
        self._result_widgets.append(container)

    def _clear_rag_results(self):
        """清空RAG结果"""
        for widget in self._result_widgets:
            try:
                widget.deleteLater()
            except RuntimeError:
                pass
        self._result_widgets.clear()

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

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#coding_assistant_panel {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#panel_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#topk_label {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
            QSpinBox {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
                padding: {dp(2)}px;
            }}
            QTextEdit#rag_input {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#search_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#search_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#search_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QPushButton#sync_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#sync_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#sync_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QPushButton#rebuild_btn {{
                background-color: {theme_manager.WARNING};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#rebuild_btn:hover {{
                background-color: {theme_manager.WARNING}dd;
            }}
            QPushButton#rebuild_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
        """)

    def cleanup(self):
        """清理资源"""
        self._cleanup_worker()
        self._clear_rag_results()


__all__ = ["CodingAssistantPanel"]
