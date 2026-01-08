"""
CodingDesk 助手面板

支持两种模式：
1. RAG检索 - 查询项目相关上下文（功能描述、模块信息等）
2. Prompt优化 - 分析当前Prompt并提供改进建议
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QTextEdit, QStackedWidget, QScrollArea, QSpinBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class RAGResultCard(QFrame):
    """RAG检索结果卡片"""

    def __init__(self, result_type: str, data: dict, parent=None):
        super().__init__(parent)
        self.result_type = result_type
        self.data = data
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
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

        # 调试日志：追踪RAG结果卡片接收到的数据
        logger.info(
            "RAGResultCard接收数据: source='%s' chapter_num=%s data_type='%s' data_keys=%s",
            source, chapter_num, data_type, list(self.data.keys())
        )

        # 根据数据类型生成合适的来源显示
        if source:
            # 后端已经设置了有意义的chapter_title
            source_text = source[:25] + "..." if len(source) > 25 else source
            logger.info("使用source字段: '%s' -> '%s'", source, source_text)
        elif chapter_num:
            # 根据数据类型选择前缀
            type_prefix = {
                'feature_prompt': 'F',
                'feature_outline': 'FO',
                'system': 'S',
                'module': 'M',
                'inspiration': 'R',  # Round
                'architecture': 'A',
                'tech_stack': 'T',
                'requirement': 'Req',
                'challenge': 'Ch',
                'dependency': 'D',
            }.get(data_type, 'F')
            source_text = f"{type_prefix}{chapter_num}"
            logger.info("回退到chapter_num: prefix='%s' data_type='%s' -> '%s'", type_prefix, data_type, source_text)
        else:
            # 使用数据类型的显示名称
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

        # 数据类型标签（如果有）
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

        self._apply_style()

    def _apply_style(self):
        """应用样式"""
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


class CodingAssistantPanel(QFrame):
    """编程项目助手面板 - RAG检索和Prompt优化"""

    # 信号
    optimizationApplied = pyqtSignal(str)  # 优化后的内容

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.project_id = None
        self.current_mode = "rag"  # "rag" 或 "optimize"
        self.current_prompt = ""  # 当前要优化的Prompt
        self.is_loading = False
        self._worker = None
        self._result_widgets = []
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("coding_assistant_panel")
        self.setFixedWidth(dp(320))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 模式切换
        self.mode_container = QWidget()
        self.mode_container.setFixedHeight(dp(48))
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        mode_layout.setSpacing(dp(8))

        self.rag_btn = QPushButton("RAG检索")
        self.rag_btn.setCheckable(True)
        self.rag_btn.setChecked(True)
        self.rag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rag_btn.clicked.connect(lambda: self._switch_mode("rag"))
        mode_layout.addWidget(self.rag_btn)

        self.optimize_btn = QPushButton("Prompt优化")
        self.optimize_btn.setCheckable(True)
        self.optimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.optimize_btn.clicked.connect(lambda: self._switch_mode("optimize"))
        mode_layout.addWidget(self.optimize_btn)

        mode_layout.addStretch()
        layout.addWidget(self.mode_container)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme_manager.BORDER_LIGHT};")
        layout.addWidget(divider)

        # 内容堆栈
        self.content_stack = QStackedWidget()

        # RAG模式
        self.rag_content = self._create_rag_content()
        self.content_stack.addWidget(self.rag_content)

        # 优化模式
        self.optimize_content = self._create_optimize_content()
        self.content_stack.addWidget(self.optimize_content)

        layout.addWidget(self.content_stack, 1)

        self._apply_style()

    def _create_rag_content(self) -> QWidget:
        """创建RAG检索内容"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setFixedHeight(dp(44))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(12), 0, dp(12), 0)

        title_label = QLabel("上下文检索")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 入库按钮区域
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(6))

        # 智能同步按钮（合并了检查状态和入库功能）
        self.sync_btn = QPushButton("同步RAG")
        self.sync_btn.setObjectName("sync_btn")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setToolTip("智能同步：检查完整性，仅入库缺失的数据类型")
        self.sync_btn.clicked.connect(self._on_sync_rag)
        btn_layout.addWidget(self.sync_btn)

        # 强制重建按钮
        self.rebuild_btn = QPushButton("重建")
        self.rebuild_btn.setObjectName("rebuild_btn")
        self.rebuild_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rebuild_btn.setToolTip("强制重建：重新入库所有数据（用于修复来源信息）")
        self.rebuild_btn.clicked.connect(self._on_force_rebuild)
        btn_layout.addWidget(self.rebuild_btn)

        header_layout.addWidget(btn_container)

        topk_label = QLabel("数量:")
        topk_label.setObjectName("topk_label")
        header_layout.addWidget(topk_label)

        self.topk_spinner = QSpinBox()
        self.topk_spinner.setRange(1, 20)
        self.topk_spinner.setValue(5)
        self.topk_spinner.setFixedWidth(dp(50))
        header_layout.addWidget(self.topk_spinner)

        layout.addWidget(header)

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

    def _create_optimize_content(self) -> QWidget:
        """创建Prompt优化内容"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setFixedHeight(dp(44))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(12), 0, dp(12), 0)

        title_label = QLabel("Prompt优化")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()
        layout.addWidget(header)

        # 当前Prompt显示
        prompt_container = QWidget()
        prompt_layout = QVBoxLayout(prompt_container)
        prompt_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        prompt_layout.setSpacing(dp(8))

        prompt_label = QLabel("当前Prompt:")
        prompt_label.setObjectName("prompt_label")
        prompt_layout.addWidget(prompt_label)

        self.prompt_display = QTextEdit()
        self.prompt_display.setObjectName("prompt_display")
        self.prompt_display.setReadOnly(True)
        self.prompt_display.setPlaceholderText("生成功能后，Prompt将显示在这里...")
        self.prompt_display.setMinimumHeight(dp(150))
        prompt_layout.addWidget(self.prompt_display, 1)

        # 优化按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(8))

        self.analyze_btn = QPushButton("分析优化")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._on_analyze)
        btn_layout.addWidget(self.analyze_btn)

        self.apply_btn = QPushButton("应用建议")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)

        prompt_layout.addLayout(btn_layout)
        layout.addWidget(prompt_container)

        # 优化建议区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            {theme_manager.scrollbar()}
        """)

        self.optimize_results = QWidget()
        self.optimize_results.setStyleSheet("background: transparent;")
        self.optimize_results_layout = QVBoxLayout(self.optimize_results)
        self.optimize_results_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(12))
        self.optimize_results_layout.setSpacing(dp(8))

        # 建议显示区域
        self.suggestion_label = QLabel("优化建议:")
        self.suggestion_label.setObjectName("suggestion_title")
        self.suggestion_label.setVisible(False)
        self.optimize_results_layout.addWidget(self.suggestion_label)

        self.suggestion_display = QTextEdit()
        self.suggestion_display.setObjectName("suggestion_display")
        self.suggestion_display.setReadOnly(True)
        self.suggestion_display.setVisible(False)
        self.optimize_results_layout.addWidget(self.suggestion_display)

        self.optimize_results_layout.addStretch()

        scroll.setWidget(self.optimize_results)
        layout.addWidget(scroll, 1)

        return container

    def _switch_mode(self, mode: str):
        """切换模式"""
        if self.current_mode == mode:
            return

        self.current_mode = mode
        self.rag_btn.setChecked(mode == "rag")
        self.optimize_btn.setChecked(mode == "optimize")
        self.content_stack.setCurrentIndex(0 if mode == "rag" else 1)

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        self.project_id = project_id

    def setPromptContent(self, content: str):
        """设置要优化的Prompt内容"""
        self.current_prompt = content
        self.prompt_display.setPlainText(content)
        # 清空之前的建议
        self.suggestion_display.clear()
        self.suggestion_label.setVisible(False)
        self.suggestion_display.setVisible(False)
        self.apply_btn.setEnabled(False)

    def _on_sync_rag(self):
        """智能同步RAG数据（检查完整性并入库缺失数据）"""
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

        # 调用智能入库API（默认只入库不完整的类型）
        self._worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            False  # force=False，智能模式
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
            # 入库前已完整，无需操作
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
        """强制重建RAG数据（重新入库所有类型）"""
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

        # 调用强制入库API
        self._worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            True  # force=True，强制重建
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

        # 调试日志：追踪API响应
        logger.info("RAG检索成功: chunks数量=%d, summaries数量=%d", len(chunks), len(summaries))
        if chunks:
            sample = chunks[0]
            logger.info(
                "RAG首条chunk样本: source='%s' chapter_number=%s data_type='%s' keys=%s",
                sample.get('source', '(无)'),
                sample.get('chapter_number', '(无)'),
                sample.get('data_type', '(无)'),
                list(sample.keys())
            )

        if not chunks and not summaries:
            self._add_rag_message("未找到相关内容", "尝试使用不同的关键词进行检索")
            return

        # 显示结果
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
        # 标题
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

        # 结果卡片
        for data in results[:10]:  # 限制显示数量
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

    def _on_analyze(self):
        """分析优化Prompt"""
        if not self.current_prompt:
            MessageService.show_warning(self, "没有可优化的Prompt")
            return

        if self.is_loading:
            return

        self.is_loading = True
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")

        # 显示分析提示
        self.suggestion_label.setVisible(True)
        self.suggestion_display.setVisible(True)
        self.suggestion_display.setPlainText("正在分析Prompt并生成优化建议...")

        # 模拟分析（实际应调用后端API）
        QTimer.singleShot(1500, self._generate_suggestions)

    def _generate_suggestions(self):
        """生成优化建议（模拟）"""
        self.is_loading = False
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("分析优化")

        # 生成基于规则的建议
        suggestions = []
        prompt = self.current_prompt

        if len(prompt) < 200:
            suggestions.append("- Prompt内容较短，建议补充更多功能描述和实现细节")

        if "错误处理" not in prompt and "error" not in prompt.lower():
            suggestions.append("- 建议添加错误处理相关的描述")

        if "参数" not in prompt and "parameter" not in prompt.lower():
            suggestions.append("- 建议明确输入参数的类型和校验规则")

        if "返回" not in prompt and "return" not in prompt.lower():
            suggestions.append("- 建议明确返回值的类型和格式")

        if "依赖" not in prompt and "dependency" not in prompt.lower():
            suggestions.append("- 建议说明该功能的依赖模块")

        if not suggestions:
            suggestions.append("- Prompt结构完整，内容清晰")
            suggestions.append("- 可以考虑添加更多边界条件说明")
            suggestions.append("- 可以补充性能相关的注意事项")

        self.suggestion_display.setPlainText("\n".join(suggestions))
        self.apply_btn.setEnabled(True)

    def _on_apply(self):
        """应用优化建议"""
        # 这里可以实现自动应用建议的逻辑
        # 目前只是提示用户手动修改
        MessageService.show_info(self, "请根据建议手动优化Prompt内容")

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

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame#coding_assistant_panel {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#topk_label, QLabel#prompt_label {{
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
            QTextEdit#rag_input, QTextEdit#prompt_display {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
                font-size: {dp(12)}px;
            }}
            QTextEdit#suggestion_display {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
                font-size: {dp(12)}px;
            }}
            QLabel#suggestion_title {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(13)}px;
                font-weight: bold;
            }}
            QPushButton#search_btn, QPushButton#analyze_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#search_btn:hover, QPushButton#analyze_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#search_btn:disabled, QPushButton#analyze_btn:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QPushButton#apply_btn {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#apply_btn:hover {{
                background-color: {theme_manager.SUCCESS}dd;
            }}
            QPushButton#apply_btn:disabled {{
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

        # 模式切换按钮样式
        mode_btn_style = f"""
            QPushButton {{
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QPushButton:checked {{
                color: white;
                background-color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """
        self.rag_btn.setStyleSheet(mode_btn_style)
        self.optimize_btn.setStyleSheet(mode_btn_style)

    def cleanup(self):
        """清理资源"""
        self._cleanup_worker()
        self._clear_rag_results()


__all__ = ["CodingAssistantPanel"]
