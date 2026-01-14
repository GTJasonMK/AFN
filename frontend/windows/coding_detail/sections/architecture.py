"""
架构设计Section - 合并蓝图展示和三层结构

整合原 planning.py 和 systems.py 的功能：
- 蓝图核心信息展示（技术栈、核心需求、技术挑战）
- 三层结构展示（系统 -> 模块 -> 功能）
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker
from utils.message_service import MessageService

# 复用 systems.py 中的组件
from .systems import SystemNode

logger = logging.getLogger(__name__)


class ArchitectureSection(BaseSection):
    """架构设计Section

    展示：
    - 蓝图概要（可折叠）
    - 两层结构（系统 -> 模块）
    """

    # 额外信号（editRequested和refreshRequested继承自BaseSection）
    loadingRequested = pyqtSignal(str)
    loadingFinished = pyqtSignal()

    def __init__(
        self,
        blueprint: Dict[str, Any] = None,
        planning_data: Dict[str, Any] = None,
        systems: List[Dict] = None,
        modules: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.blueprint = blueprint or {}
        self.planning_data = planning_data or {}
        self.systems = systems or []
        self.modules = modules or []
        self._system_nodes = []
        self._workers = []
        self._blueprint_expanded = True
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

        # 1. 蓝图概要Section（可折叠）
        self.blueprint_section = self._create_blueprint_section()
        layout.addWidget(self.blueprint_section)

        # 2. 三层结构Section
        self.structure_section = self._create_structure_section()
        layout.addWidget(self.structure_section)

        layout.addStretch()

        scroll.setWidget(content)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self._apply_scroll_style(scroll)

    def _create_blueprint_section(self) -> QFrame:
        """创建蓝图概要Section"""
        section = QFrame()
        section.setObjectName("blueprint_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题栏（可折叠）
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        self.blueprint_expand_icon = QLabel("-")
        self.blueprint_expand_icon.setObjectName("expand_icon")
        self.blueprint_expand_icon.setFixedWidth(dp(20))
        header_layout.addWidget(self.blueprint_expand_icon)

        title = QLabel("蓝图概要")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.mousePressEvent = self._on_blueprint_header_click
        layout.addWidget(header)

        # 蓝图内容容器
        self.blueprint_content = QWidget()
        content_layout = QVBoxLayout(self.blueprint_content)
        content_layout.setContentsMargins(dp(28), 0, 0, 0)
        content_layout.setSpacing(dp(12))

        # 技术栈信息
        tech_stack = self.blueprint.get('tech_stack', {})
        if tech_stack:
            tech_card = self._create_tech_stack_card(tech_stack)
            content_layout.addWidget(tech_card)

        # 核心需求（简化显示）
        requirements = self.planning_data.get('core_requirements', [])
        if requirements:
            req_card = self._create_simple_list_card("核心需求", requirements, 'requirement')
            content_layout.addWidget(req_card)

        # 技术挑战（简化显示）
        challenges = self.planning_data.get('technical_challenges', [])
        if challenges:
            challenge_card = self._create_simple_list_card("技术挑战", challenges, 'challenge')
            content_layout.addWidget(challenge_card)

        layout.addWidget(self.blueprint_content)

        self._apply_blueprint_style(section)
        return section

    def _create_tech_stack_card(self, tech_stack: Dict) -> QFrame:
        """创建技术栈卡片"""
        card = QFrame()
        card.setObjectName("tech_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # 技术栈标题
        title = QLabel("技术栈")
        title.setObjectName("card_title")
        layout.addWidget(title)

        # 组件列表
        components = tech_stack.get('components', [])
        if components:
            comp_layout = QHBoxLayout()
            comp_layout.setSpacing(dp(8))
            for comp in components[:6]:  # 最多显示6个
                name = comp.get('name', '') if isinstance(comp, dict) else str(comp)
                tag = QLabel(name)
                tag.setObjectName("tech_tag")
                comp_layout.addWidget(tag)
            comp_layout.addStretch()
            layout.addLayout(comp_layout)

        # 核心约束
        constraints = tech_stack.get('core_constraints', '')
        if constraints:
            constraint_label = QLabel(f"约束: {constraints[:100]}..." if len(constraints) > 100 else f"约束: {constraints}")
            constraint_label.setObjectName("constraint_text")
            constraint_label.setWordWrap(True)
            layout.addWidget(constraint_label)

        return card

    def _create_simple_list_card(self, title: str, items: List[Dict], key: str) -> QFrame:
        """创建简化列表卡片"""
        card = QFrame()
        card.setObjectName("list_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(6))

        # 标题
        title_label = QLabel(f"{title} ({len(items)})")
        title_label.setObjectName("card_title")
        layout.addWidget(title_label)

        # 列表项（最多显示3个）
        for item in items[:3]:
            text = item.get(key, item.get('requirement', item.get('challenge', str(item))))
            if isinstance(text, str):
                text = text[:80] + '...' if len(text) > 80 else text
                item_label = QLabel(f"- {text}")
                item_label.setObjectName("list_item")
                item_label.setWordWrap(True)
                layout.addWidget(item_label)

        if len(items) > 3:
            more_label = QLabel(f"... 还有 {len(items) - 3} 项")
            more_label.setObjectName("more_hint")
            layout.addWidget(more_label)

        return card

    def _create_structure_section(self) -> QWidget:
        """创建两层结构Section"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("项目结构")
        title.setObjectName("structure_title")
        header_layout.addWidget(title)

        # 统计信息
        stats_text = f"{len(self.systems)} 系统 / {len(self.modules)} 模块"
        self.stats_label = QLabel(stats_text)
        self.stats_label.setObjectName("stats_label")
        header_layout.addWidget(self.stats_label)

        header_layout.addStretch()

        # 一键生成所有模块按钮
        if self._editable:
            gen_all_modules_btn = QPushButton("一键生成所有模块")
            gen_all_modules_btn.setObjectName("gen_all_modules_btn")
            gen_all_modules_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_all_modules_btn.clicked.connect(self._on_generate_all_modules)
            header_layout.addWidget(gen_all_modules_btn)

        # 生成系统按钮
        if self._editable:
            gen_btn = QPushButton("生成系统划分")
            gen_btn.setObjectName("gen_systems_btn")
            gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_btn.clicked.connect(self._on_generate_systems)
            header_layout.addWidget(gen_btn)

        layout.addWidget(header)

        # 系统列表容器
        self.systems_container = QWidget()
        self.systems_layout = QVBoxLayout(self.systems_container)
        self.systems_layout.setContentsMargins(0, 0, 0, 0)
        self.systems_layout.setSpacing(dp(12))

        self._populate_systems()
        layout.addWidget(self.systems_container)

        self._apply_structure_style()

        return section

    def _populate_systems(self):
        """填充系统列表"""
        for node in self._system_nodes:
            try:
                node.deleteLater()
            except RuntimeError:
                pass
        self._system_nodes.clear()

        if not self.systems:
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setContentsMargins(dp(20), dp(40), dp(20), dp(40))
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            empty_label = QLabel("暂无系统划分\n\n点击「生成系统划分」按钮，AI将自动将项目划分为多个子系统")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setWordWrap(True)
            empty_layout.addWidget(empty_label)

            self.systems_layout.addWidget(empty_widget)
            self._system_nodes.append(empty_widget)
            return

        for system in self.systems:
            system_num = system.get('system_number', 0)
            # 筛选该系统下的模块
            system_modules = [
                m for m in self.modules
                if m.get('system_number') == system_num
            ]

            node = SystemNode(system, system_modules)
            node.clicked.connect(self._on_item_clicked)
            node.generateModulesClicked.connect(self._on_generate_modules)
            self.systems_layout.addWidget(node)
            self._system_nodes.append(node)

    def _on_blueprint_header_click(self, event):
        """蓝图标题点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._blueprint_expanded = not self._blueprint_expanded
            self.blueprint_content.setVisible(self._blueprint_expanded)
            self.blueprint_expand_icon.setText("-" if self._blueprint_expanded else "+")

    def _on_item_clicked(self, data: Dict):
        """项目点击处理"""
        logger.info(f"项目点击: {data}")

    def _on_generate_systems(self):
        """生成系统划分"""
        from components.dialogs import get_regenerate_preference

        logger.info(f"生成系统划分: project_id={self.project_id}")

        preference = None

        if self.systems and len(self.systems) > 0:
            preference, ok = get_regenerate_preference(
                self,
                title="重新生成系统划分",
                message=f"当前已有 {len(self.systems)} 个系统划分。\n\n"
                        "重新生成将覆盖现有的系统、模块和功能大纲数据。",
                placeholder="例如：希望更细粒度划分、合并某些系统、增加某类系统等"
            )
            if not ok:
                return

        self.loadingRequested.emit("正在生成系统划分，请稍候...")

        worker = AsyncAPIWorker(
            self.api_client.generate_coding_systems,
            self.project_id,
            min_systems=3,
            max_systems=8,
            preference=preference
        )
        worker.success.connect(self._on_systems_generated)
        worker.error.connect(self._on_generate_error)
        self._workers.append(worker)
        worker.start()

    def _on_systems_generated(self, result):
        """系统生成完成"""
        self.loadingFinished.emit()
        logger.info(f"系统生成完成: {len(result)} 个系统")
        MessageService.show_success(self, f"成功生成 {len(result)} 个系统")
        self.refreshRequested.emit()

    def _on_generate_modules(self, system_number: int):
        """生成模块"""
        from components.dialogs import get_regenerate_preference

        logger.info(f"生成模块: system_number={system_number}")

        preference = None
        existing_modules = [m for m in self.modules if m.get('system_number') == system_number]

        if existing_modules:
            system_name = next(
                (s.get('name', f'系统{system_number}') for s in self.systems if s.get('system_number') == system_number),
                f'系统{system_number}'
            )
            preference, ok = get_regenerate_preference(
                self,
                title=f"重新生成模块 - {system_name}",
                message=f"系统 [{system_name}] 下已有 {len(existing_modules)} 个模块。\n\n"
                        "重新生成将覆盖现有的模块和功能大纲数据。",
                placeholder="例如：增加某类模块、更关注某类功能、合并某些模块等"
            )
            if not ok:
                return

        self.loadingRequested.emit("正在生成模块，请稍候...")

        worker = AsyncAPIWorker(
            self.api_client.generate_coding_modules,
            self.project_id,
            system_number,
            min_modules=3,
            max_modules=8,
            preference=preference
        )
        worker.success.connect(self._on_modules_generated)
        worker.error.connect(self._on_generate_error)
        self._workers.append(worker)
        worker.start()

    def _on_modules_generated(self, result):
        """模块生成完成"""
        self.loadingFinished.emit()
        logger.info(f"模块生成完成: {len(result)} 个模块")
        MessageService.show_success(self, f"成功生成 {len(result)} 个模块")
        self.refreshRequested.emit()

    def _on_generate_all_modules(self):
        """一键生成所有系统的模块"""
        from components.dialogs import get_regenerate_preference, ConfirmDialog
        from PyQt6.QtWidgets import QDialog

        if not self.project_id:
            MessageService.show_warning(self, "请先保存项目")
            return

        if not self.systems:
            MessageService.show_warning(self, "请先生成系统划分")
            return

        # 检查是否已有模块
        if self.modules and len(self.modules) > 0:
            dialog = ConfirmDialog(
                self,
                title="一键生成所有模块",
                message=f"当前已有 {len(self.modules)} 个模块。\n\n"
                        f"一键生成将为所有 {len(self.systems)} 个系统重新生成模块，\n"
                        "现有的模块和功能大纲数据将被覆盖。\n\n"
                        "确定要继续吗？",
                confirm_text="确定",
                cancel_text="取消"
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

        logger.info(f"一键生成所有模块: project_id={self.project_id}, systems={len(self.systems)}")

        self.loadingRequested.emit(f"正在为 {len(self.systems)} 个系统生成模块...")

        # 使用SSE流式处理
        url = self.api_client.get_generate_all_modules_stream_url(self.project_id)
        self._all_modules_sse_worker = SSEWorker(url, {})
        self._all_modules_sse_worker.event_received.connect(self._on_all_modules_event)
        self._all_modules_sse_worker.error.connect(self._on_all_modules_error)
        self._all_modules_sse_worker.finished.connect(self._on_all_modules_finished)
        self._all_modules_sse_worker.start()

    def _on_all_modules_event(self, event_type: str, data: dict):
        """处理批量生成模块的SSE事件"""
        if event_type == "start":
            total = data.get("total_systems", 0)
            logger.info(f"开始批量生成模块: {total} 个系统")
            self.loadingRequested.emit(f"开始为 {total} 个系统生成模块...")

        elif event_type == "system_start":
            system_name = data.get("system_name", "")
            index = data.get("index", 0)
            total = data.get("total", 0)
            self.loadingRequested.emit(f"正在生成模块 ({index}/{total}): {system_name}...")

        elif event_type == "system_complete":
            system_name = data.get("system_name", "")
            modules_created = data.get("modules_created", 0)
            logger.info(f"系统 {system_name} 模块生成完成: {modules_created} 个")

        elif event_type == "system_error":
            system_name = data.get("system_name", "")
            error = data.get("error", "")
            logger.warning(f"系统 {system_name} 模块生成失败: {error}")

        elif event_type == "complete":
            total_modules = data.get("total_modules", 0)
            systems_processed = data.get("systems_processed", 0)
            total_systems = data.get("total_systems", 0)
            logger.info(f"批量生成完成: {systems_processed}/{total_systems} 系统, {total_modules} 模块")
            MessageService.show_success(
                self,
                f"成功为 {systems_processed} 个系统生成 {total_modules} 个模块"
            )

        elif event_type == "error":
            error_msg = data.get("message", "未知错误")
            logger.error(f"批量生成失败: {error_msg}")
            MessageService.show_error(self, f"生成失败：{error_msg}")

    def _on_all_modules_error(self, error_msg: str):
        """批量生成模块SSE错误"""
        self.loadingFinished.emit()
        logger.error(f"批量生成模块连接错误: {error_msg}")
        MessageService.show_error(self, f"连接错误：{error_msg}")

    def _on_all_modules_finished(self):
        """批量生成模块SSE完成"""
        self.loadingFinished.emit()
        if hasattr(self, '_all_modules_sse_worker'):
            self._all_modules_sse_worker = None
        self.refreshRequested.emit()

    def _on_generate_error(self, error_msg: str):
        """生成失败"""
        self.loadingFinished.emit()
        logger.error(f"生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败：{error_msg}")

    def _apply_blueprint_style(self, section: QFrame):
        """应用蓝图样式"""
        section.setStyleSheet(f"""
            QFrame#blueprint_section {{
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
            QFrame#tech_card, QFrame#list_card {{
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(6)}px;
            }}
            QLabel#card_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QLabel#tech_tag {{
                color: {theme_manager.PRIMARY};
                font-size: {sp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {theme_manager.PRIMARY}15;
                border-radius: {dp(4)}px;
            }}
            QLabel#constraint_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(12)}px;
            }}
            QLabel#list_item {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(12)}px;
            }}
            QLabel#more_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(11)}px;
                font-style: italic;
            }}
        """)

    def _apply_structure_style(self):
        """应用结构样式"""
        self.setStyleSheet(f"""
            QLabel#structure_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(16)}px;
                font-weight: 600;
            }}
            QLabel#stats_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(13)}px;
                margin-left: {dp(12)}px;
            }}
            QPushButton#gen_systems_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton#gen_systems_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#gen_all_modules_btn {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton#gen_all_modules_btn:hover {{
                background-color: {theme_manager.SUCCESS}DD;
            }}
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(14)}px;
                line-height: 1.6;
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
        if hasattr(self, 'blueprint_section'):
            self._apply_blueprint_style(self.blueprint_section)
        self._apply_structure_style()
        for node in self._system_nodes:
            if hasattr(node, '_apply_style'):
                node._apply_style()

    def updateData(
        self,
        blueprint: Dict[str, Any] = None,
        planning_data: Dict[str, Any] = None,
        systems: List[Dict] = None,
        modules: List[Dict] = None
    ):
        """更新数据"""
        if blueprint is not None:
            self.blueprint = blueprint
        if planning_data is not None:
            self.planning_data = planning_data
        if systems is not None:
            self.systems = systems
        if modules is not None:
            self.modules = modules

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            stats_text = f"{len(self.systems)} 系统 / {len(self.modules)} 模块"
            self.stats_label.setText(stats_text)

        self._populate_systems()

    def cleanup(self):
        """清理资源"""
        # 清理SSE worker
        if hasattr(self, '_all_modules_sse_worker') and self._all_modules_sse_worker:
            try:
                self._all_modules_sse_worker.stop()
            except Exception:
                pass
            self._all_modules_sse_worker = None

        # 清理AsyncWorker
        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()


__all__ = ["ArchitectureSection"]
