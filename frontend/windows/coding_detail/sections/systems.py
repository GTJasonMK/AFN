"""
三层结构Section - 系统/模块/功能层级展示

提供编程项目的系统->模块->功能三层可折叠树形结构展示。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class FeatureItem(QFrame):
    """功能项组件 - 带描述展示"""

    clicked = pyqtSignal(dict)
    generateClicked = pyqtSignal(dict)

    def __init__(self, feature_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.feature_data = feature_data
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("feature_item")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
        main_layout.setSpacing(dp(4))

        # 第一行：编号、名称、优先级、按钮
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(8))

        # 功能编号
        feature_num = self.feature_data.get('feature_number', 0)
        num_label = QLabel(f"F{feature_num}")
        num_label.setObjectName("feature_num")
        num_label.setFixedWidth(dp(36))
        header_layout.addWidget(num_label)

        # 功能名称
        name = self.feature_data.get('name', '未命名功能')
        name_label = QLabel(name)
        name_label.setObjectName("feature_name")
        header_layout.addWidget(name_label, 1)

        # 优先级标签
        priority = self.feature_data.get('priority', 'medium')
        priority_label = QLabel(self._get_priority_text(priority))
        priority_label.setObjectName(f"priority_{priority}")
        header_layout.addWidget(priority_label)

        # 生成按钮
        gen_btn = QPushButton("生成")
        gen_btn.setObjectName("gen_btn")
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.clicked.connect(lambda: self.generateClicked.emit(self.feature_data))
        header_layout.addWidget(gen_btn)

        main_layout.addWidget(header_row)

        # 第二行：描述信息
        description = self.feature_data.get('description', '')
        if description:
            desc_label = QLabel(description[:120] + '...' if len(description) > 120 else description)
            desc_label.setObjectName("feature_desc")
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)

        # 第三行：输入/输出（如果有）
        inputs = self.feature_data.get('inputs', '')
        outputs = self.feature_data.get('outputs', '')
        if inputs or outputs:
            io_row = QWidget()
            io_layout = QHBoxLayout(io_row)
            io_layout.setContentsMargins(dp(36), 0, 0, 0)  # 对齐编号
            io_layout.setSpacing(dp(16))

            if inputs:
                inputs_label = QLabel(f"输入: {inputs[:50]}..." if len(inputs) > 50 else f"输入: {inputs}")
                inputs_label.setObjectName("feature_io")
                io_layout.addWidget(inputs_label)

            if outputs:
                outputs_label = QLabel(f"输出: {outputs[:50]}..." if len(outputs) > 50 else f"输出: {outputs}")
                outputs_label.setObjectName("feature_io")
                io_layout.addWidget(outputs_label)

            io_layout.addStretch()
            main_layout.addWidget(io_row)

        self._apply_style()

    def _get_priority_text(self, priority: str) -> str:
        """获取优先级显示文本"""
        mapping = {'high': '高', 'medium': '中', 'low': '低'}
        return mapping.get(priority, priority)

    def _apply_style(self):
        """应用样式"""
        priority = self.feature_data.get('priority', 'medium')
        priority_colors = {
            'high': theme_manager.ERROR,
            'medium': theme_manager.WARNING,
            'low': theme_manager.TEXT_TERTIARY,
        }
        priority_color = priority_colors.get(priority, theme_manager.TEXT_TERTIARY)

        self.setStyleSheet(f"""
            QFrame#feature_item {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
            }}
            QFrame#feature_item:hover {{
                border-color: {theme_manager.PRIMARY};
            }}
            QLabel#feature_num {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#feature_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
            }}
            QLabel#feature_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                padding-left: {dp(36)}px;
            }}
            QLabel#feature_io {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#priority_high, QLabel#priority_medium, QLabel#priority_low {{
                color: {priority_color};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(6)}px;
                background-color: {priority_color}15;
                border-radius: {dp(3)}px;
            }}
            QPushButton#gen_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(3)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#gen_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.feature_data)
        super().mousePressEvent(event)


class ModuleNode(QFrame):
    """模块节点组件 - 可折叠展示功能列表，带描述和依赖展示"""

    clicked = pyqtSignal(dict)
    generateFeaturesClicked = pyqtSignal(int, int)  # system_number, module_number
    featureGenerateClicked = pyqtSignal(dict)

    def __init__(self, module_data: Dict[str, Any], features: List[Dict] = None, parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self.features = features or []
        self._expanded = False
        self._feature_items = []
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("module_node")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 模块头部容器（包含标题行和描述行）
        self.header = QFrame()
        self.header.setObjectName("module_header")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_main_layout = QVBoxLayout(self.header)
        header_main_layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        header_main_layout.setSpacing(dp(6))

        # 第一行：基本信息
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(8))

        # 展开/折叠图标
        self.expand_icon = QLabel("+")
        self.expand_icon.setObjectName("expand_icon")
        self.expand_icon.setFixedWidth(dp(16))
        title_layout.addWidget(self.expand_icon)

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

        # 功能数量
        feature_count = len(self.features)
        count_label = QLabel(f"{feature_count} 功能")
        count_label.setObjectName("feature_count")
        title_layout.addWidget(count_label)

        # 生成功能按钮
        gen_btn = QPushButton("生成功能")
        gen_btn.setObjectName("gen_features_btn")
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.clicked.connect(self._on_generate_features)
        title_layout.addWidget(gen_btn)

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
            meta_layout.setContentsMargins(dp(24), 0, 0, 0)
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

        # 功能列表容器（默认隐藏）
        self.features_container = QWidget()
        self.features_container.setObjectName("features_container")
        features_layout = QVBoxLayout(self.features_container)
        features_layout.setContentsMargins(dp(40), dp(4), dp(8), dp(8))
        features_layout.setSpacing(dp(4))

        self._populate_features(features_layout)
        self.features_container.setVisible(False)
        layout.addWidget(self.features_container)

        # 绑定点击事件
        self.header.mousePressEvent = self._on_header_click

        self._apply_style()

    def _populate_features(self, layout):
        """填充功能列表"""
        for item in self._feature_items:
            item.deleteLater()
        self._feature_items.clear()

        if not self.features:
            empty_label = QLabel("暂无功能，点击「生成功能」添加")
            empty_label.setObjectName("empty_hint")
            layout.addWidget(empty_label)
            self._feature_items.append(empty_label)
            return

        for feature in self.features:
            item = FeatureItem(feature)
            item.clicked.connect(lambda f: self.clicked.emit(f))
            item.generateClicked.connect(self.featureGenerateClicked.emit)
            layout.addWidget(item)
            self._feature_items.append(item)

    def _on_header_click(self, event):
        """头部点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()

    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self._expanded = not self._expanded
        self.features_container.setVisible(self._expanded)
        self.expand_icon.setText("-" if self._expanded else "+")

    def _on_generate_features(self):
        """生成功能按钮点击"""
        system_num = self.module_data.get('system_number', 1)
        module_num = self.module_data.get('module_number', 1)
        self.generateFeaturesClicked.emit(system_num, module_num)

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
            QLabel#expand_icon {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(14)}px;
                font-weight: bold;
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
                padding-left: {dp(24)}px;
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
            QLabel#feature_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
            }}
            QPushButton#gen_features_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#gen_features_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QWidget#features_container {{
                background-color: transparent;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
                font-style: italic;
            }}
        """)


class SystemNode(QFrame):
    """系统节点组件 - 可折叠展示模块列表，带描述和职责展示"""

    clicked = pyqtSignal(dict)
    generateModulesClicked = pyqtSignal(int)  # system_number
    moduleGenerateFeaturesClicked = pyqtSignal(int, int)  # system_number, module_number
    featureGenerateClicked = pyqtSignal(dict)

    def __init__(
        self,
        system_data: Dict[str, Any],
        modules: List[Dict] = None,
        features: List[Dict] = None,
        parent=None
    ):
        super().__init__(parent)
        self.system_data = system_data
        self.modules = modules or []
        self.all_features = features or []
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

    def _populate_modules(self, layout):
        """填充模块列表"""
        for node in self._module_nodes:
            node.deleteLater()
        self._module_nodes.clear()

        if not self.modules:
            empty_label = QLabel("暂无模块，点击「生成模块」添加")
            empty_label.setObjectName("empty_hint")
            layout.addWidget(empty_label)
            self._module_nodes.append(empty_label)
            return

        system_num = self.system_data.get('system_number', 1)
        for module in self.modules:
            # 筛选该模块下的功能
            module_num = module.get('module_number', 0)
            module_features = [
                f for f in self.all_features
                if f.get('module_number') == module_num
            ]

            node = ModuleNode(module, module_features)
            node.clicked.connect(self.clicked.emit)
            node.generateFeaturesClicked.connect(self.moduleGenerateFeaturesClicked.emit)
            node.featureGenerateClicked.connect(self.featureGenerateClicked.emit)
            layout.addWidget(node)
            self._module_nodes.append(node)

    def _on_header_click(self, event):
        """头部点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()

    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self._expanded = not self._expanded
        self.modules_container.setVisible(self._expanded)
        self.expand_icon.setText("-" if self._expanded else "+")

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
    """三层结构Section

    展示：系统 -> 模块 -> 功能 的可折叠树形结构
    """

    navigateToDesk = pyqtSignal(int)  # feature_number
    refreshRequested = pyqtSignal()
    loadingRequested = pyqtSignal(str)  # 请求显示加载状态
    loadingFinished = pyqtSignal()  # 请求隐藏加载状态

    def __init__(
        self,
        systems: List[Dict] = None,
        modules: List[Dict] = None,
        features: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.systems = systems or []
        self.modules = modules or []
        self.features = features or []
        self._system_nodes = []
        self._workers = []
        self.api_client = APIClientManager.get_client()

        super().__init__([], editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("项目结构")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        # 统计信息
        stats_text = f"{len(self.systems)} 系统 / {len(self.modules)} 模块 / {len(self.features)} 功能"
        stats_label = QLabel(stats_text)
        stats_label.setObjectName("stats_label")
        header_layout.addWidget(stats_label)
        self.stats_label = stats_label

        header_layout.addStretch()

        # 生成系统按钮
        if self._editable:
            gen_systems_btn = QPushButton("生成系统划分")
            gen_systems_btn.setObjectName("gen_systems_btn")
            gen_systems_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_systems_btn.clicked.connect(self._on_generate_systems)
            header_layout.addWidget(gen_systems_btn)

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
        for node in self._system_nodes:
            node.deleteLater()
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

            node = SystemNode(system, system_modules, self.features)
            node.clicked.connect(self._on_item_clicked)
            node.generateModulesClicked.connect(self._on_generate_modules)
            node.moduleGenerateFeaturesClicked.connect(self._on_generate_features)
            node.featureGenerateClicked.connect(self._on_feature_generate)
            self.systems_layout.addWidget(node)
            self._system_nodes.append(node)

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

    def _on_generate_features(self, system_number: int, module_number: int):
        """生成功能"""
        from components.dialogs import get_regenerate_preference

        logger.info(f"生成功能: system={system_number}, module={module_number}")

        preference = None

        # 检查该模块下是否已有功能
        existing_features = [
            f for f in self.features
            if f.get('system_number') == system_number and f.get('module_number') == module_number
        ]
        if existing_features:
            module_name = next(
                (m.get('name', f'模块{module_number}') for m in self.modules if m.get('module_number') == module_number),
                f'模块{module_number}'
            )
            preference, ok = get_regenerate_preference(
                self,
                title=f"重新生成功能大纲 - {module_name}",
                message=f"模块 [{module_name}] 下已有 {len(existing_features)} 个功能大纲。\n\n"
                        "重新生成将覆盖现有的功能大纲数据。",
                placeholder="例如：细化某类功能、增加边界处理、增加异常处理等"
            )
            if not ok:
                return

        self.loadingRequested.emit("正在生成功能大纲，请稍候...")

        worker = AsyncAPIWorker(
            self.api_client.generate_coding_features,
            self.project_id,
            system_number,
            module_number,
            min_features=2,
            max_features=6,
            preference=preference
        )
        worker.success.connect(self._on_features_generated)
        worker.error.connect(self._on_generate_error)
        self._workers.append(worker)
        worker.start()

    def _on_features_generated(self, result):
        """功能生成完成"""
        self.loadingFinished.emit()
        logger.info(f"功能生成完成: {len(result)} 个功能")
        MessageService.show_success(self, f"成功生成 {len(result)} 个功能大纲")
        self.refreshRequested.emit()

    def _on_generate_error(self, error_msg: str):
        """生成失败处理"""
        self.loadingFinished.emit()
        logger.error(f"生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败：{error_msg}")

    def _on_feature_generate(self, feature_data: Dict):
        """单个功能生成内容"""
        feature_num = feature_data.get('feature_number', 0)
        logger.info(f"跳转到工作台生成功能: feature_number={feature_num}")
        self.navigateToDesk.emit(feature_num)  # 直接传递feature_number

    def updateData(
        self,
        systems: List[Dict] = None,
        modules: List[Dict] = None,
        features: List[Dict] = None
    ):
        """更新数据"""
        if systems is not None:
            self.systems = systems
        if modules is not None:
            self.modules = modules
        if features is not None:
            self.features = features

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            stats_text = f"{len(self.systems)} 系统 / {len(self.modules)} 模块 / {len(self.features)} 功能"
            self.stats_label.setText(stats_text)

        self._populate_systems()

    def cleanup(self):
        """清理资源"""
        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()


__all__ = ["SystemsSection"]
