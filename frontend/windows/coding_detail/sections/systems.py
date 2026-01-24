"""
两层结构Section - 系统/模块层级展示

提供编程项目的系统->模块两层可折叠树形结构展示。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from windows.base.sections import BaseSection, toggle_expand_state
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class ModuleNode(QFrame):
    """模块节点组件 - 简化版，只展示模块信息"""

    clicked = pyqtSignal(dict)

    def __init__(self, module_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("module_node")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 模块头部容器
        self.header = QFrame()
        self.header.setObjectName("module_header")
        header_main_layout = QVBoxLayout(self.header)
        header_main_layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        header_main_layout.setSpacing(dp(6))

        # 第一行：基本信息
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(8))

        # 模块编号
        module_num = self.module_data.get('module_number', 0)
        num_label = QLabel(f"M{module_num}")
        num_label.setObjectName("module_num")
        num_label.setFixedWidth(dp(40))
        title_layout.addWidget(num_label)

        # 模块名称
        name = self.module_data.get('name', '未命名模块')
        name_label = QLabel(name)
        name_label.setObjectName("module_name")
        title_layout.addWidget(name_label, 1)

        # 模块类型
        module_type = self.module_data.get('type', '')
        if module_type:
            type_label = QLabel(module_type)
            type_label.setObjectName("module_type")
            title_layout.addWidget(type_label)

        header_main_layout.addWidget(title_row)

        # 第二行：描述信息（如果有）
        description = self.module_data.get('description', '')
        if description:
            desc_label = QLabel(description[:150] + '...' if len(description) > 150 else description)
            desc_label.setObjectName("module_desc")
            desc_label.setWordWrap(True)
            header_main_layout.addWidget(desc_label)

        # 第三行：依赖和接口信息（如果有）
        dependencies = self.module_data.get('dependencies', [])
        interface = self.module_data.get('interface', '')

        if dependencies or interface:
            meta_row = QWidget()
            meta_layout = QHBoxLayout(meta_row)
            meta_layout.setContentsMargins(dp(40), 0, 0, 0)
            meta_layout.setSpacing(dp(16))

            if dependencies:
                if isinstance(dependencies, list):
                    deps_str = ', '.join(dependencies[:3])
                    if len(dependencies) > 3:
                        deps_str += f' +{len(dependencies)-3}'
                else:
                    deps_str = str(dependencies)[:50]
                deps_label = QLabel(f"依赖: {deps_str}")
                deps_label.setObjectName("module_deps")
                meta_layout.addWidget(deps_label)

            if interface:
                iface_label = QLabel(f"接口: {interface[:40]}..." if len(interface) > 40 else f"接口: {interface}")
                iface_label.setObjectName("module_interface")
                meta_layout.addWidget(iface_label)

            meta_layout.addStretch()
            header_main_layout.addWidget(meta_row)

        layout.addWidget(self.header)

        self._apply_style()

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame#module_node {{
                background-color: transparent;
                border: none;
            }}
            QFrame#module_header {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
            }}
            QFrame#module_header:hover {{
                border-color: {theme_manager.PRIMARY};
            }}
            QLabel#module_num {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(12)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#module_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 500;
            }}
            QLabel#module_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                padding-left: {dp(40)}px;
            }}
            QLabel#module_deps {{
                color: {theme_manager.WARNING};
                font-size: {dp(11)}px;
            }}
            QLabel#module_interface {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#module_type {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {theme_manager.PRIMARY}15;
                border-radius: {dp(4)}px;
            }}
        """)


class SystemNode(QFrame):
    """系统节点组件 - 可折叠展示模块列表（两层结构）"""

    clicked = pyqtSignal(dict)
    generateModulesClicked = pyqtSignal(int)  # system_number

    def __init__(
        self,
        system_data: Dict[str, Any],
        modules: List[Dict] = None,
        parent=None
    ):
        super().__init__(parent)
        self.system_data = system_data
        self.modules = modules or []
        self._expanded = True  # 默认展开
        self._module_nodes = []
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("system_node")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 系统头部容器（包含标题行和描述行）
        self.header = QFrame()
        self.header.setObjectName("system_header")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_main_layout = QVBoxLayout(self.header)
        header_main_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        header_main_layout.setSpacing(dp(8))

        # 第一行：基本信息
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(10))

        # 展开/折叠图标
        self.expand_icon = QLabel("-")
        self.expand_icon.setObjectName("expand_icon")
        self.expand_icon.setFixedWidth(dp(20))
        title_layout.addWidget(self.expand_icon)

        # 系统编号
        system_num = self.system_data.get('system_number', 0)
        num_label = QLabel(f"S{system_num}")
        num_label.setObjectName("system_num")
        num_label.setFixedWidth(dp(40))
        title_layout.addWidget(num_label)

        # 系统名称
        name = self.system_data.get('name', '未命名系统')
        name_label = QLabel(name)
        name_label.setObjectName("system_name")
        title_layout.addWidget(name_label, 1)

        # 模块数量
        module_count = len(self.modules)
        count_label = QLabel(f"{module_count} 模块")
        count_label.setObjectName("module_count")
        title_layout.addWidget(count_label)

        # 生成模块按钮
        gen_btn = QPushButton("生成模块")
        gen_btn.setObjectName("gen_modules_btn")
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.clicked.connect(self._on_generate_modules)
        title_layout.addWidget(gen_btn)

        header_main_layout.addWidget(title_row)

        # 第二行：描述信息（如果有）
        description = self.system_data.get('description', '')
        if description:
            desc_label = QLabel(description[:200] + '...' if len(description) > 200 else description)
            desc_label.setObjectName("system_desc")
            desc_label.setWordWrap(True)
            header_main_layout.addWidget(desc_label)

        # 第三行：职责列表（如果有）
        responsibilities = self.system_data.get('responsibilities', [])
        if responsibilities:
            resp_row = QWidget()
            resp_layout = QHBoxLayout(resp_row)
            resp_layout.setContentsMargins(dp(30), 0, 0, 0)
            resp_layout.setSpacing(dp(8))

            resp_title = QLabel("职责:")
            resp_title.setObjectName("resp_title")
            resp_layout.addWidget(resp_title)

            if isinstance(responsibilities, list):
                resp_str = ' | '.join(responsibilities[:4])
                if len(responsibilities) > 4:
                    resp_str += f' +{len(responsibilities)-4}'
            else:
                resp_str = str(responsibilities)[:100]

            resp_content = QLabel(resp_str)
            resp_content.setObjectName("resp_content")
            resp_content.setWordWrap(True)
            resp_layout.addWidget(resp_content, 1)

            header_main_layout.addWidget(resp_row)

        # 第四行：技术要求（如果有）
        tech_requirements = self.system_data.get('tech_requirements', '')
        if tech_requirements:
            tech_row = QWidget()
            tech_layout = QHBoxLayout(tech_row)
            tech_layout.setContentsMargins(dp(30), 0, 0, 0)
            tech_layout.setSpacing(dp(8))

            tech_title = QLabel("技术:")
            tech_title.setObjectName("tech_title")
            tech_layout.addWidget(tech_title)

            tech_content = QLabel(tech_requirements[:80] + '...' if len(tech_requirements) > 80 else tech_requirements)
            tech_content.setObjectName("tech_content")
            tech_layout.addWidget(tech_content, 1)

            header_main_layout.addWidget(tech_row)

        layout.addWidget(self.header)

        # 模块列表容器
        self.modules_container = QWidget()
        self.modules_container.setObjectName("modules_container")
        modules_layout = QVBoxLayout(self.modules_container)
        modules_layout.setContentsMargins(dp(24), dp(8), 0, dp(8))
        modules_layout.setSpacing(dp(8))

        self._populate_modules(modules_layout)
        layout.addWidget(self.modules_container)

        # 绑定点击事件
        self.header.mousePressEvent = self._on_header_click

        self._apply_style()

    def _create_modules_empty_hint(self) -> QLabel:
        """创建模块空状态提示"""
        empty_label = QLabel("暂无模块，点击「生成模块」添加")
        empty_label.setObjectName("empty_hint")
        return empty_label

    def _populate_modules(self, layout):
        """填充模块列表"""
        def build_node(module):
            node = ModuleNode(module)
            node.clicked.connect(self.clicked.emit)
            return node

        self._render_card_list(
            items=self.modules,
            layout=layout,
            cards=self._module_nodes,
            card_factory=build_node,
            empty_factory=self._create_modules_empty_hint,
        )

    def _on_header_click(self, event):
        """头部点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()

    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self._expanded = toggle_expand_state(
            self._expanded,
            self.modules_container,
            self.expand_icon,
        )

    def _on_generate_modules(self):
        """生成模块按钮点击"""
        system_num = self.system_data.get('system_number', 1)
        self.generateModulesClicked.emit(system_num)

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame#system_node {{
                background-color: transparent;
                border: none;
            }}
            QFrame#system_header {{
                background-color: {theme_manager.PRIMARY}08;
                border: 2px solid {theme_manager.PRIMARY}40;
                border-radius: {dp(8)}px;
            }}
            QFrame#system_header:hover {{
                border-color: {theme_manager.PRIMARY};
            }}
            QLabel#expand_icon {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(16)}px;
                font-weight: bold;
            }}
            QLabel#system_num {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(14)}px;
                font-weight: bold;
                font-family: Consolas, monospace;
            }}
            QLabel#system_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QLabel#system_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
                padding-left: {dp(30)}px;
            }}
            QLabel#resp_title {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#resp_content {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
            QLabel#tech_title {{
                color: {theme_manager.SUCCESS};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#tech_content {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#module_count {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
            }}
            QPushButton#gen_modules_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#gen_modules_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QWidget#modules_container {{
                background-color: transparent;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                font-style: italic;
                padding: {dp(12)}px;
            }}
        """)


class SystemsSection(BaseSection):
    """两层结构Section

    展示：系统 -> 模块 的可折叠树形结构
    """

    refreshRequested = pyqtSignal()
    loadingRequested = pyqtSignal(str)  # 请求显示加载状态
    loadingFinished = pyqtSignal()  # 请求隐藏加载状态

    def __init__(
        self,
        systems: List[Dict] = None,
        modules: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.systems = systems or []
        self.modules = modules or []
        self._system_nodes = []
        self.api_client = APIClientManager.get_client()

        super().__init__([], editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        stats_text = f"{len(self.systems)} 系统 / {len(self.modules)} 模块"

        right_widgets = []
        if self._editable:
            gen_systems_btn = QPushButton("生成系统划分")
            gen_systems_btn.setObjectName("gen_systems_btn")
            gen_systems_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_systems_btn.clicked.connect(self._on_generate_systems)
            right_widgets.append(gen_systems_btn)

        header, labels = self._build_section_header(
            "项目结构",
            stat_items=[(stats_text, "stats_label")],
            right_widgets=right_widgets,
        )
        self.stats_label = labels.get("stats_label")
        layout.addWidget(header)

        # 系统列表容器
        self.systems_container = QWidget()
        self.systems_layout = QVBoxLayout(self.systems_container)
        self.systems_layout.setContentsMargins(0, 0, 0, 0)
        self.systems_layout.setSpacing(dp(16))

        self._populate_systems()
        layout.addWidget(self.systems_container)
        layout.addStretch()

        self._apply_header_style()

    def _populate_systems(self):
        """填充系统列表"""
        def build_node(system):
            system_num = system.get('system_number', 0)
            system_modules = [
                m for m in self.modules
                if m.get('system_number') == system_num
            ]
            node = SystemNode(system, system_modules)
            node.clicked.connect(self._on_item_clicked)
            node.generateModulesClicked.connect(self._on_generate_modules)
            return node

        self._render_card_list(
            items=self.systems,
            layout=self.systems_layout,
            cards=self._system_nodes,
            card_factory=build_node,
            empty_factory=lambda: self._create_empty_hint_widget(
                "暂无系统划分\n\n点击「生成系统划分」按钮，AI将自动将项目划分为多个子系统"
            ),
        )

    def _apply_header_style(self):
        """应用标题样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(18)}px;
                font-weight: 600;
            }}
            QLabel#stats_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(12)}px;
            }}
            QPushButton#gen_systems_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
                font-weight: 500;
            }}
            QPushButton#gen_systems_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(14)}px;
                line-height: 1.6;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_header_style()
        for node in self._system_nodes:
            if isinstance(node, SystemNode):
                node._apply_style()

    def _on_item_clicked(self, data: Dict):
        """项目点击处理"""
        logger.info(f"项目点击: {data}")

    def _on_generate_systems(self):
        """生成系统划分"""
        from components.dialogs import get_regenerate_preference

        logger.info(f"生成系统划分: project_id={self.project_id}")

        preference = None

        # 检查是否已有系统数据
        if self.systems and len(self.systems) > 0:
            preference, ok = get_regenerate_preference(
                self,
                title="重新生成系统划分",
                message=f"当前已有 {len(self.systems)} 个系统划分。\n\n"
                        "重新生成将覆盖现有的系统和模块数据。",
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
        self._register_worker(worker)
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

        # 检查该系统下是否已有模块
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
                        "重新生成将覆盖现有的模块数据。",
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
        self._register_worker(worker)
        worker.start()

    def _on_modules_generated(self, result):
        """模块生成完成"""
        self.loadingFinished.emit()
        logger.info(f"模块生成完成: {len(result)} 个模块")
        MessageService.show_success(self, f"成功生成 {len(result)} 个模块")
        self.refreshRequested.emit()

    def _on_generate_error(self, error_msg: str):
        """生成失败处理"""
        self.loadingFinished.emit()
        logger.error(f"生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败：{error_msg}")

    def updateData(
        self,
        systems: List[Dict] = None,
        modules: List[Dict] = None
    ):
        """更新数据"""
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
        self._cleanup_workers()


__all__ = ["SystemsSection"]
