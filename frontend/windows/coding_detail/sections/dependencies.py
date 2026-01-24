"""
模块依赖Section

显示编程项目的模块依赖关系，支持实时同步和刷新。
"""

import logging
from typing import Dict, Any, List, Tuple

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)

def group_dependencies_by_source(
    dependencies: List[Dict[str, Any]]
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """按源模块分组依赖并排序"""
    grouped = {}
    for dep in dependencies:
        source = dep.get('source') or dep.get('from_module', '未知模块')
        if source not in grouped:
            grouped[source] = []
        grouped[source].append(dep)
    return [(source, grouped[source]) for source in sorted(grouped.keys())]


class GroupedDependencyCard(QFrame):
    """分组依赖关系卡片

    将同一源模块的所有依赖关系聚合显示在一个卡片中。
    """

    def __init__(self, source_module: str, dependencies: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.source_module = source_module
        self.dependencies = dependencies
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("grouped_dep_card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 源模块标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        source_label = QLabel(self.source_module)
        source_label.setObjectName("source_module_title")
        header_layout.addWidget(source_label)

        # 依赖数量徽章
        count_badge = QLabel(f"{len(self.dependencies)} 个依赖")
        count_badge.setObjectName("dep_count_badge")
        header_layout.addWidget(count_badge)

        header_layout.addStretch()
        layout.addWidget(header)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("dep_separator")
        layout.addWidget(separator)

        # 依赖列表
        for idx, dep in enumerate(self.dependencies):
            dep_item = self._create_dependency_item(dep, idx == len(self.dependencies) - 1)
            layout.addWidget(dep_item)

        self._apply_style()

    def _create_dependency_item(self, dep: Dict[str, Any], is_last: bool) -> QWidget:
        """创建单个依赖项"""
        item = QWidget()
        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(dp(8), dp(4), 0, dp(4))
        item_layout.setSpacing(dp(4))

        # 目标模块行
        target_row = QWidget()
        target_layout = QHBoxLayout(target_row)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(dp(8))

        # 树形连接符
        connector = QLabel("-->" if is_last else "-->")
        connector.setObjectName("tree_connector")
        target_layout.addWidget(connector)

        # 目标模块名
        target = dep.get('target') or dep.get('to_module', '')
        target_label = QLabel(target or "未知模块")
        target_label.setObjectName("target_module")
        target_layout.addWidget(target_label)

        # 依赖类型
        dep_type = dep.get('type', 'uses')
        type_badge = QLabel(self._get_dep_type_label(dep_type))
        type_badge.setObjectName("dep_type_badge")
        target_layout.addWidget(type_badge)

        target_layout.addStretch()
        item_layout.addWidget(target_row)

        # 描述（如果有）
        description = dep.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("dep_item_desc")
            desc_label.setWordWrap(True)
            desc_label.setContentsMargins(dp(32), 0, 0, 0)
            item_layout.addWidget(desc_label)

        # 接口（如果有）
        interface = dep.get('interface', '')
        if interface:
            interface_label = QLabel(f"接口: {interface}")
            interface_label.setObjectName("dep_interface")
            interface_label.setContentsMargins(dp(32), 0, 0, 0)
            item_layout.addWidget(interface_label)

        return item

    def _get_dep_type_label(self, dep_type: str) -> str:
        """获取依赖类型标签"""
        labels = {
            'uses': '使用',
            'extends': '继承',
            'implements': '实现',
            'calls': '调用',
            'depends': '依赖',
        }
        return labels.get(dep_type, dep_type)

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame#grouped_dep_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#source_module_title {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(15)}px;
                font-weight: 600;
            }}
            QLabel#dep_count_badge {{
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BORDER_DEFAULT};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(10)}px;
            }}
            QFrame#dep_separator {{
                background-color: {theme_manager.BORDER_DEFAULT};
                max-height: 1px;
            }}
            QLabel#tree_connector {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#target_module {{
                color: {theme_manager.SUCCESS};
                font-size: {dp(14)}px;
                font-weight: 500;
            }}
            QLabel#dep_type_badge {{
                color: {theme_manager.TEXT_SECONDARY};
                background-color: {theme_manager.book_bg_primary()};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#dep_item_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
            QLabel#dep_interface {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-family: Consolas, monospace;
            }}
        """)


class DependenciesSection(BaseSection):
    """模块依赖Section

    显示：
    - 依赖关系列表
    - 每个依赖的源模块、目标模块、类型、描述
    - 支持同步和刷新依赖关系
    """

    # 信号
    syncRequested = pyqtSignal()  # 请求同步依赖
    refreshRequested = pyqtSignal()  # 请求刷新
    loadingRequested = pyqtSignal(str)  # 请求显示加载状态
    loadingFinished = pyqtSignal()  # 请求隐藏加载状态

    def __init__(
        self,
        data: List[Dict] = None,
        modules: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.modules = modules or []
        self.project_id = project_id
        self._dep_cards = []
        self.api_client = APIClientManager.get_client()
        super().__init__(data or [], editable, parent)
        self.setupUI()

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        self.project_id = project_id

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        count = len(self._data) if self._data else 0
        right_widgets = []
        if self._editable:
            # 同步依赖按钮
            sync_btn = QPushButton("同步依赖")
            sync_btn.setObjectName("sync_dep_btn")
            sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sync_btn.setToolTip("根据模块的dependencies字段同步依赖关系")
            sync_btn.clicked.connect(self._on_sync_dependencies)
            right_widgets.append(sync_btn)

            # 添加依赖按钮
            add_btn = QPushButton("添加依赖")
            add_btn.setObjectName("add_dep_btn")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._on_add_dependency)
            right_widgets.append(add_btn)

        header, labels = self._build_section_header(
            "模块依赖",
            stat_items=[(f"共 {count} 个依赖关系", "dep_count")],
            right_widgets=right_widgets,
        )
        self.count_label = labels.get("dep_count")
        layout.addWidget(header)

        # 依赖关系统计
        if self._data:
            stats_widget = self._create_stats_widget()
            layout.addWidget(stats_widget)

        # 依赖列表容器
        self.deps_container = QWidget()
        self.deps_layout = QVBoxLayout(self.deps_container)
        self.deps_layout.setContentsMargins(0, 0, 0, 0)
        self.deps_layout.setSpacing(dp(12))

        # 填充依赖卡片
        self._populate_dependencies()

        layout.addWidget(self.deps_container)
        layout.addStretch()

        self._apply_header_style()

    def _create_stats_widget(self) -> QWidget:
        """创建统计信息组件"""
        stats = QFrame()
        stats.setObjectName("stats_frame")

        layout = QHBoxLayout(stats)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(24))

        # 统计各类型依赖数量
        type_counts = {}
        for dep in self._data:
            dep_type = dep.get('type', 'uses')
            type_counts[dep_type] = type_counts.get(dep_type, 0) + 1

        type_labels = {
            'uses': '使用',
            'extends': '继承',
            'implements': '实现',
            'calls': '调用',
            'depends': '依赖',
        }

        for dep_type, count in type_counts.items():
            stat_item = QWidget()
            stat_layout = QVBoxLayout(stat_item)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(dp(4))

            count_label = QLabel(str(count))
            count_label.setObjectName("stat_count")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_layout.addWidget(count_label)

            type_label = QLabel(type_labels.get(dep_type, dep_type))
            type_label.setObjectName("stat_label")
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_layout.addWidget(type_label)

            layout.addWidget(stat_item)

        layout.addStretch()

        stats.setStyleSheet(f"""
            QFrame#stats_frame {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#stat_count {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(20)}px;
                font-weight: 600;
            }}
            QLabel#stat_label {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
        """)

        return stats

    def _populate_dependencies(self):
        """填充依赖卡片（按源模块分组）"""
        def build_card(group_data):
            source_module, deps = group_data
            return GroupedDependencyCard(source_module, deps)

        grouped = list(group_dependencies_by_source(self._data or []))
        self._render_card_list(
            items=grouped,
            layout=self.deps_layout,
            cards=self._dep_cards,
            card_factory=build_card,
            empty_factory=lambda: self._create_empty_label("暂无依赖关系"),
        )

    def _apply_header_style(self):
        """应用标题样式"""
        self.setStyleSheet(
            self._build_basic_header_style("dep_count") + f"""
                QPushButton#add_dep_btn {{
                    background-color: {theme_manager.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {dp(12)}px;
                }}
                QPushButton#add_dep_btn:hover {{
                    background-color: {theme_manager.PRIMARY_DARK};
                }}
                QPushButton#sync_dep_btn {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {dp(12)}px;
                }}
                QPushButton#sync_dep_btn:hover {{
                    background-color: {theme_manager.PRIMARY}10;
                }}
            """
        )

    def _apply_theme(self):
        """应用主题"""
        self._apply_header_style()
        for card in self._dep_cards:
            if isinstance(card, GroupedDependencyCard):
                card._apply_style()

    def _on_add_dependency(self):
        """添加依赖"""
        self.requestEdit('dependencies.add', '添加依赖关系', '')

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
        worker.success.connect(self._on_sync_success)
        worker.error.connect(self._on_sync_error)
        self._register_worker(worker)
        worker.start()

    def _on_sync_success(self, result):
        """同步成功"""
        self.loadingFinished.emit()
        synced_count = result.get('synced_count', 0)
        logger.info(f"依赖同步完成: {synced_count} 条")
        MessageService.show_success(self, f"成功同步 {synced_count} 条依赖关系")
        self.refreshRequested.emit()

    def _on_sync_error(self, error_msg: str):
        """同步失败"""
        self.loadingFinished.emit()
        logger.error(f"依赖同步失败: {error_msg}")
        MessageService.show_error(self, f"同步失败：{error_msg}")

    def updateData(self, data: List[Dict]):
        """更新数据"""
        self._data = data or []

        # 更新计数
        if hasattr(self, 'count_label') and self.count_label:
            count = len(self._data)
            self.count_label.setText(f"共 {count} 个依赖关系")

        # 重新填充依赖
        self._populate_dependencies()

    def cleanup(self):
        """清理资源"""
        self._cleanup_workers()


__all__ = ["DependenciesSection"]
