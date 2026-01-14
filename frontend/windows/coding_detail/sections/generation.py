"""
生成管理Section - 合并依赖关系和已生成内容

整合原 dependencies.py 和 generated.py 的功能：
- RAG状态展示
- 依赖关系管理
- 已生成文件列表
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

# 复用现有组件
from .dependencies import GroupedDependencyCard
from .generated import GeneratedItemCard

logger = logging.getLogger(__name__)


class GenerationSection(BaseSection):
    """生成管理Section

    展示：
    - RAG状态（完整性、已入库数量）
    - 依赖关系（可折叠）
    - 已生成文件列表
    """

    # 额外信号（editRequested和refreshRequested继承自BaseSection）
    loadingRequested = pyqtSignal(str)
    loadingFinished = pyqtSignal()

    def __init__(
        self,
        dependencies: List[Dict] = None,
        modules: List[Dict] = None,
        features: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.dependencies = dependencies or []
        self.modules = modules or []
        self.features = features or []
        self._dep_cards = []
        self._item_cards = []
        self._workers = []
        self._deps_expanded = True
        self._generated_expanded = True
        self.api_client = APIClientManager.get_client()

        super().__init__([], editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, dp(8), 0)
        layout.setSpacing(dp(16))

        # 1. RAG状态Section
        self.rag_section = self._create_rag_section()
        layout.addWidget(self.rag_section)

        # 2. 依赖关系Section（可折叠）
        self.deps_section = self._create_dependencies_section()
        layout.addWidget(self.deps_section)

        # 3. 已生成文件Section（可折叠）
        self.generated_section = self._create_generated_section()
        layout.addWidget(self.generated_section)

        layout.addStretch()

        scroll.setWidget(content)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self._apply_scroll_style(scroll)

    def _create_rag_section(self) -> QFrame:
        """创建RAG状态Section"""
        section = QFrame()
        section.setObjectName("rag_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题行
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        title = QLabel("RAG状态")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # RAG同步按钮
        if self._editable:
            sync_btn = QPushButton("同步RAG")
            sync_btn.setObjectName("sync_rag_btn")
            sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sync_btn.setToolTip("同步项目数据到向量数据库")
            sync_btn.clicked.connect(self._on_sync_rag)
            header_layout.addWidget(sync_btn)

        layout.addWidget(header)

        # RAG统计卡片
        stats_card = QWidget()
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(dp(24))

        # 完整性指示
        completeness_widget = QWidget()
        comp_layout = QVBoxLayout(completeness_widget)
        comp_layout.setContentsMargins(0, 0, 0, 0)
        comp_layout.setSpacing(dp(4))

        comp_label = QLabel("数据完整性")
        comp_label.setObjectName("stat_label")
        comp_layout.addWidget(comp_label)

        self.completeness_bar = QProgressBar()
        self.completeness_bar.setObjectName("completeness_bar")
        self.completeness_bar.setFixedHeight(dp(8))
        self.completeness_bar.setValue(0)
        self.completeness_bar.setTextVisible(False)
        comp_layout.addWidget(self.completeness_bar)

        self.completeness_text = QLabel("-- / --")
        self.completeness_text.setObjectName("stat_value")
        comp_layout.addWidget(self.completeness_text)

        stats_layout.addWidget(completeness_widget, 1)

        # 已入库数量
        ingested_widget = QWidget()
        ing_layout = QVBoxLayout(ingested_widget)
        ing_layout.setContentsMargins(0, 0, 0, 0)
        ing_layout.setSpacing(dp(4))

        ing_label = QLabel("已入库")
        ing_label.setObjectName("stat_label")
        ing_layout.addWidget(ing_label)

        self.ingested_count = QLabel("0")
        self.ingested_count.setObjectName("stat_count")
        ing_layout.addWidget(self.ingested_count)

        stats_layout.addWidget(ingested_widget)

        # 待入库数量
        pending_widget = QWidget()
        pend_layout = QVBoxLayout(pending_widget)
        pend_layout.setContentsMargins(0, 0, 0, 0)
        pend_layout.setSpacing(dp(4))

        pend_label = QLabel("待入库")
        pend_label.setObjectName("stat_label")
        pend_layout.addWidget(pend_label)

        self.pending_count = QLabel("0")
        self.pending_count.setObjectName("stat_count_warn")
        pend_layout.addWidget(self.pending_count)

        stats_layout.addWidget(pending_widget)

        stats_layout.addStretch()
        layout.addWidget(stats_card)

        self._apply_rag_style(section)
        return section

    def _create_dependencies_section(self) -> QFrame:
        """创建依赖关系Section（可折叠）"""
        section = QFrame()
        section.setObjectName("deps_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题栏（可折叠）
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        self.deps_expand_icon = QLabel("-")
        self.deps_expand_icon.setObjectName("expand_icon")
        self.deps_expand_icon.setFixedWidth(dp(20))
        header_layout.addWidget(self.deps_expand_icon)

        title = QLabel("依赖关系")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        # 依赖数量
        count = len(self.dependencies)
        self.deps_count_label = QLabel(f"({count})")
        self.deps_count_label.setObjectName("count_label")
        header_layout.addWidget(self.deps_count_label)

        header_layout.addStretch()

        # 同步依赖按钮
        if self._editable:
            sync_btn = QPushButton("同步依赖")
            sync_btn.setObjectName("sync_dep_btn")
            sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sync_btn.setToolTip("根据模块定义同步依赖关系")
            sync_btn.clicked.connect(self._on_sync_dependencies)
            header_layout.addWidget(sync_btn)

        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.mousePressEvent = self._on_deps_header_click
        layout.addWidget(header)

        # 依赖内容容器
        self.deps_content = QWidget()
        deps_layout = QVBoxLayout(self.deps_content)
        deps_layout.setContentsMargins(dp(28), 0, 0, 0)
        deps_layout.setSpacing(dp(8))

        self._populate_dependencies(deps_layout)

        layout.addWidget(self.deps_content)

        self._apply_deps_style(section)
        return section

    def _create_generated_section(self) -> QFrame:
        """创建已生成文件Section（可折叠）"""
        section = QFrame()
        section.setObjectName("generated_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题栏（可折叠）
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        self.generated_expand_icon = QLabel("-")
        self.generated_expand_icon.setObjectName("expand_icon")
        self.generated_expand_icon.setFixedWidth(dp(20))
        header_layout.addWidget(self.generated_expand_icon)

        title = QLabel("已生成内容")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        # 生成数量（从features中筛选has_content=True的）
        generated_features = [f for f in self.features if f.get('has_content')]
        count = len(generated_features)
        self.generated_count_label = QLabel(f"({count})")
        self.generated_count_label.setObjectName("count_label")
        header_layout.addWidget(self.generated_count_label)

        # 统计总版本数
        total_versions = sum(f.get('version_count', 0) or 0 for f in generated_features)
        if total_versions > 0:
            self.versions_label = QLabel(f"{total_versions} 版本")
            self.versions_label.setObjectName("words_label")
            header_layout.addWidget(self.versions_label)

        header_layout.addStretch()

        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.mousePressEvent = self._on_generated_header_click
        layout.addWidget(header)

        # 已生成内容容器
        self.generated_content = QWidget()
        gen_layout = QVBoxLayout(self.generated_content)
        gen_layout.setContentsMargins(dp(28), 0, 0, 0)
        gen_layout.setSpacing(dp(8))

        self._populate_generated(gen_layout)

        layout.addWidget(self.generated_content)

        self._apply_generated_style(section)
        return section

    def _populate_dependencies(self, layout: QVBoxLayout):
        """填充依赖关系列表"""
        # 清除现有卡片
        for card in self._dep_cards:
            try:
                card.deleteLater()
            except RuntimeError:
                pass
        self._dep_cards.clear()

        if not self.dependencies:
            empty_label = QLabel("暂无依赖关系")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_label)
            self._dep_cards.append(empty_label)
            return

        # 按源模块分组
        grouped_deps = {}
        for dep in self.dependencies:
            source = dep.get('source') or dep.get('from_module', '未知模块')
            if source not in grouped_deps:
                grouped_deps[source] = []
            grouped_deps[source].append(dep)

        # 创建分组卡片
        for source_module in sorted(grouped_deps.keys()):
            deps = grouped_deps[source_module]
            card = GroupedDependencyCard(source_module, deps)
            layout.addWidget(card)
            self._dep_cards.append(card)

    def _populate_generated(self, layout: QVBoxLayout):
        """填充已生成内容列表"""
        # 清除现有卡片
        for card in self._item_cards:
            try:
                card.deleteLater()
            except RuntimeError:
                pass
        self._item_cards.clear()

        # 筛选已生成内容的功能
        generated_features = [f for f in self.features if f.get('has_content')]

        if not generated_features:
            empty_widget = self._create_empty_generated_state()
            layout.addWidget(empty_widget)
            self._item_cards.append(empty_widget)
            return

        # 构建功能卡片
        for feature in generated_features:
            feature_number = feature.get('feature_number', 0)
            feature_title = feature.get('name') or feature.get('title') or f'功能 {feature_number}'
            feature_summary = feature.get('description') or ''

            item_data = {
                'title': feature_title,
                'summary': feature_summary,
                'word_count': 0,  # Coding项目不统计字数
                'version_count': feature.get('version_count', 0) or 0,
                'status': feature.get('status', 'successful') or 'successful',
                'created_at': '',
            }

            card = GeneratedItemCard(feature_number, item_data)
            card.viewClicked.connect(self._on_view_item)
            card.editClicked.connect(self._on_edit_item)
            layout.addWidget(card)
            self._item_cards.append(card)

    def _create_empty_generated_state(self) -> QWidget:
        """创建空状态组件"""
        empty = QFrame()
        empty.setObjectName("empty_generated")

        layout = QVBoxLayout(empty)
        layout.setContentsMargins(dp(20), dp(30), dp(20), dp(30))
        layout.setSpacing(dp(8))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_label = QLabel("暂无已生成内容")
        text_label.setObjectName("empty_text")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)

        hint_label = QLabel("请先在目录结构Tab中生成文件Prompt")
        hint_label.setObjectName("empty_hint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        return empty

    def _on_deps_header_click(self, event):
        """依赖标题点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._deps_expanded = not self._deps_expanded
            self.deps_content.setVisible(self._deps_expanded)
            self.deps_expand_icon.setText("-" if self._deps_expanded else "+")

    def _on_generated_header_click(self, event):
        """已生成标题点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._generated_expanded = not self._generated_expanded
            self.generated_content.setVisible(self._generated_expanded)
            self.generated_expand_icon.setText("-" if self._generated_expanded else "+")

    def _on_sync_rag(self):
        """同步RAG数据"""
        if not self.project_id:
            MessageService.show_warning(self, "未设置项目ID")
            return

        logger.info(f"同步RAG数据: project_id={self.project_id}")
        self.loadingRequested.emit("正在同步RAG数据...")

        worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            force=True
        )
        worker.success.connect(self._on_rag_sync_success)
        worker.error.connect(self._on_rag_sync_error)
        self._workers.append(worker)
        worker.start()

    def _on_rag_sync_success(self, result):
        """RAG同步成功"""
        self.loadingFinished.emit()
        added = result.get('added', 0)
        total = result.get('total_items', 0)
        logger.info(f"RAG同步完成: added={added}, total={total}")
        MessageService.show_success(self, f"RAG同步完成：已入库 {added}/{total} 项")

        # 更新显示
        self.ingested_count.setText(str(total))
        self.pending_count.setText("0")
        if total > 0:
            self.completeness_bar.setValue(100)
            self.completeness_text.setText(f"{total} / {total}")

    def _on_rag_sync_error(self, error_msg: str):
        """RAG同步失败"""
        self.loadingFinished.emit()
        logger.error(f"RAG同步失败: {error_msg}")
        MessageService.show_error(self, f"RAG同步失败：{error_msg}")

    def _on_sync_dependencies(self):
        """同步依赖关系"""
        if not self.project_id:
            MessageService.show_warning(self, "未设置项目ID")
            return

        logger.info(f"同步依赖关系: project_id={self.project_id}")
        self.loadingRequested.emit("正在同步依赖关系...")

        worker = AsyncAPIWorker(
            self.api_client.sync_coding_dependencies,
            self.project_id
        )
        worker.success.connect(self._on_deps_sync_success)
        worker.error.connect(self._on_deps_sync_error)
        self._workers.append(worker)
        worker.start()

    def _on_deps_sync_success(self, result):
        """依赖同步成功"""
        self.loadingFinished.emit()
        synced_count = result.get('synced_count', 0)
        logger.info(f"依赖同步完成: {synced_count} 条")
        MessageService.show_success(self, f"成功同步 {synced_count} 条依赖关系")
        self.refreshRequested.emit()

    def _on_deps_sync_error(self, error_msg: str):
        """依赖同步失败"""
        self.loadingFinished.emit()
        logger.error(f"依赖同步失败: {error_msg}")
        MessageService.show_error(self, f"同步失败：{error_msg}")

    def _on_view_item(self, feature_number: int):
        """查看已生成项目"""
        logger.info(f"查看已生成项目: feature_number={feature_number}")
        MessageService.show_info(self, f"查看功能 {feature_number} 的Prompt（开发中）")

    def _on_edit_item(self, feature_number: int):
        """编辑已生成项目"""
        logger.info(f"编辑已生成项目: feature_number={feature_number}")
        MessageService.show_info(self, f"编辑功能 {feature_number} 的Prompt（开发中）")

    def _apply_rag_style(self, section: QFrame):
        """应用RAG样式"""
        section.setStyleSheet(f"""
            QFrame#rag_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QPushButton#sync_rag_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton#sync_rag_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QLabel#stat_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(12)}px;
            }}
            QLabel#stat_value {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(13)}px;
            }}
            QLabel#stat_count {{
                color: {theme_manager.SUCCESS};
                font-size: {sp(18)}px;
                font-weight: 600;
            }}
            QLabel#stat_count_warn {{
                color: {theme_manager.WARNING};
                font-size: {sp(18)}px;
                font-weight: 600;
            }}
            QProgressBar#completeness_bar {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border: none;
                border-radius: {dp(4)}px;
            }}
            QProgressBar#completeness_bar::chunk {{
                background-color: {theme_manager.SUCCESS};
                border-radius: {dp(4)}px;
            }}
        """)

    def _apply_deps_style(self, section: QFrame):
        """应用依赖样式"""
        section.setStyleSheet(f"""
            QFrame#deps_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#expand_icon {{
                color: {theme_manager.PRIMARY};
                font-size: {sp(16)}px;
                font-weight: bold;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QLabel#count_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(13)}px;
            }}
            QPushButton#sync_dep_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(6)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton#sync_dep_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(13)}px;
                padding: {dp(20)}px;
            }}
        """)

    def _apply_generated_style(self, section: QFrame):
        """应用已生成样式"""
        section.setStyleSheet(f"""
            QFrame#generated_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#expand_icon {{
                color: {theme_manager.PRIMARY};
                font-size: {sp(16)}px;
                font-weight: bold;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QLabel#count_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(13)}px;
            }}
            QLabel#words_label {{
                color: {theme_manager.PRIMARY};
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QFrame#empty_generated {{
                background-color: {theme_manager.book_bg_primary()};
                border: 1px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
            }}
            QLabel#empty_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(14)}px;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(12)}px;
            }}
        """)

    def _apply_scroll_style(self, scroll: QScrollArea):
        """应用滚动区域样式"""
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

    def _apply_theme(self):
        """应用主题"""
        if hasattr(self, 'rag_section'):
            self._apply_rag_style(self.rag_section)
        if hasattr(self, 'deps_section'):
            self._apply_deps_style(self.deps_section)
        if hasattr(self, 'generated_section'):
            self._apply_generated_style(self.generated_section)
        for card in self._dep_cards:
            if hasattr(card, '_apply_style'):
                card._apply_style()
        for card in self._item_cards:
            if hasattr(card, '_apply_style'):
                card._apply_style()

    def updateData(
        self,
        dependencies: List[Dict] = None,
        modules: List[Dict] = None,
        features: List[Dict] = None
    ):
        """更新数据"""
        if dependencies is not None:
            self.dependencies = dependencies
        if modules is not None:
            self.modules = modules
        if features is not None:
            self.features = features

        # 更新依赖计数
        if hasattr(self, 'deps_count_label') and self.deps_count_label:
            self.deps_count_label.setText(f"({len(self.dependencies)})")

        # 更新已生成计数（从features中筛选has_content=True的）
        generated_features = [f for f in self.features if f.get('has_content')]
        if hasattr(self, 'generated_count_label') and self.generated_count_label:
            self.generated_count_label.setText(f"({len(generated_features)})")

        # 更新总版本数
        if hasattr(self, 'versions_label'):
            total_versions = sum(f.get('version_count', 0) or 0 for f in generated_features)
            self.versions_label.setText(f"{total_versions} 版本")

        # 重新填充内容
        if hasattr(self, 'deps_content'):
            deps_layout = self.deps_content.layout()
            if deps_layout:
                self._populate_dependencies(deps_layout)

        if hasattr(self, 'generated_content'):
            gen_layout = self.generated_content.layout()
            if gen_layout:
                self._populate_generated(gen_layout)

    def cleanup(self):
        """清理资源"""
        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()


__all__ = ["GenerationSection"]
