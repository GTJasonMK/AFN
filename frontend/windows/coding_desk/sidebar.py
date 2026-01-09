"""
CodingDesk Sidebar组件

三级结构显示：系统 -> 模块 -> 功能
支持折叠、选择和生成操作。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class SidebarFeatureItem(ThemeAwareFrame):
    """侧边栏功能项（最底层，主题感知）"""

    clicked = pyqtSignal(int)  # feature_number
    generateClicked = pyqtSignal(int)  # feature_number

    def __init__(self, feature_data: Dict[str, Any], parent=None):
        self.feature_data = feature_data
        self.feature_number = feature_data.get('feature_number', 0)
        self._selected = False
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("sidebar_feature_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(dp(40))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(8), dp(4), dp(8), dp(4))
        layout.setSpacing(dp(6))

        # 功能编号
        num_label = QLabel(f"F{self.feature_number}")
        num_label.setObjectName("feature_num")
        num_label.setFixedWidth(dp(28))
        layout.addWidget(num_label)

        # 功能名称
        name = self.feature_data.get('name', f'功能{self.feature_number}')
        name_label = QLabel(name)
        name_label.setObjectName("feature_name")
        name_label.setWordWrap(False)
        layout.addWidget(name_label, 1)

        # 状态和生成按钮
        status = self.feature_data.get('status', 'pending')
        has_content = self.feature_data.get('has_content', False)

        # 判断是否已生成：优先使用 has_content 字段
        is_generated = has_content or status in ['generated', 'successful', 'reviewed']

        if status == 'generating':
            # 生成中：显示状态
            status_label = QLabel("...")
            status_label.setObjectName("status_generating")
            status_label.setFixedWidth(dp(20))
            layout.addWidget(status_label)
        elif is_generated:
            # 已生成：显示"重新生成"按钮
            regen_btn = QPushButton("重生成")
            regen_btn.setObjectName("regen_btn")
            regen_btn.setFixedSize(dp(50), dp(22))
            regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            regen_btn.clicked.connect(lambda: self.generateClicked.emit(self.feature_number))
            layout.addWidget(regen_btn)
        else:
            # 未生成：显示"生成"按钮
            gen_btn = QPushButton("生成")
            gen_btn.setObjectName("gen_btn")
            gen_btn.setFixedSize(dp(40), dp(22))
            gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_btn.clicked.connect(lambda: self.generateClicked.emit(self.feature_number))
            layout.addWidget(gen_btn)

    def _get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icons = {
            'generating': '...',
            'generated': '[ok]',
            'reviewed': '[ok]',
        }
        return icons.get(status, '')

    def setSelected(self, selected: bool):
        """设置选中状态"""
        self._selected = selected
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        border_color = theme_manager.PRIMARY if self._selected else "transparent"
        bg_color = f"{theme_manager.PRIMARY}15" if self._selected else "transparent"

        status = self.feature_data.get('status', 'pending')
        status_color = {
            'pending': theme_manager.TEXT_TERTIARY,
            'generating': theme_manager.WARNING,
            'generated': theme_manager.SUCCESS,
            'reviewed': theme_manager.SUCCESS,
        }.get(status, theme_manager.TEXT_TERTIARY)

        self.setStyleSheet(f"""
            QFrame#sidebar_feature_item {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
            }}
            QFrame#sidebar_feature_item:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QLabel#feature_num {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(10)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#feature_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(12)}px;
            }}
            QLabel#status_generated, QLabel#status_reviewed {{
                color: {theme_manager.SUCCESS};
                font-size: {dp(10)}px;
            }}
            QLabel#status_generating {{
                color: {theme_manager.WARNING};
                font-size: {dp(10)}px;
            }}
            QPushButton#gen_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(3)}px;
                font-size: {dp(10)}px;
            }}
            QPushButton#gen_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#regen_btn {{
                background-color: {theme_manager.TEXT_TERTIARY};
                color: white;
                border: none;
                border-radius: {dp(3)}px;
                font-size: {dp(10)}px;
            }}
            QPushButton#regen_btn:hover {{
                background-color: {theme_manager.PRIMARY};
            }}
        """)

    def mousePressEvent(self, event):
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.feature_number)
        super().mousePressEvent(event)


class SidebarModuleNode(ThemeAwareFrame):
    """侧边栏模块节点（中间层，主题感知）"""

    featureClicked = pyqtSignal(int)  # feature_number
    featureGenerateClicked = pyqtSignal(int)  # feature_number

    def __init__(self, module_data: Dict[str, Any], features: List[Dict] = None, parent=None):
        self.module_data = module_data
        self.module_number = module_data.get('module_number', 0)
        self.features = features or []
        self._expanded = False
        self._feature_items: List[SidebarFeatureItem] = []
        self.header = None
        self.expand_icon = None
        self.features_container = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("sidebar_module_node")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 模块头部
        self.header = QFrame()
        self.header.setObjectName("module_header")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setFixedHeight(dp(32))
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(dp(8), dp(4), dp(8), dp(4))
        header_layout.setSpacing(dp(6))

        # 展开图标
        self.expand_icon = QLabel("+")
        self.expand_icon.setObjectName("expand_icon")
        self.expand_icon.setFixedWidth(dp(12))
        header_layout.addWidget(self.expand_icon)

        # 模块编号
        num_label = QLabel(f"M{self.module_number}")
        num_label.setObjectName("module_num")
        num_label.setFixedWidth(dp(28))
        header_layout.addWidget(num_label)

        # 模块名称
        name = self.module_data.get('name', f'模块{self.module_number}')
        name_label = QLabel(name)
        name_label.setObjectName("module_name")
        header_layout.addWidget(name_label, 1)

        # 功能数量
        count_label = QLabel(f"{len(self.features)}")
        count_label.setObjectName("feature_count")
        header_layout.addWidget(count_label)

        layout.addWidget(self.header)

        # 功能列表容器
        self.features_container = QWidget()
        self.features_container.setObjectName("features_container")
        features_layout = QVBoxLayout(self.features_container)
        features_layout.setContentsMargins(dp(16), dp(2), 0, dp(2))
        features_layout.setSpacing(dp(2))

        self._populate_features(features_layout)
        self.features_container.setVisible(False)
        layout.addWidget(self.features_container)

        # 头部点击事件
        self.header.mousePressEvent = self._on_header_click

    def _populate_features(self, layout):
        """填充功能列表"""
        for item in self._feature_items:
            item.deleteLater()
        self._feature_items.clear()

        if not self.features:
            empty_label = QLabel("暂无功能")
            empty_label.setObjectName("empty_hint")
            layout.addWidget(empty_label)
            return

        for feature in self.features:
            item = SidebarFeatureItem(feature)
            item.clicked.connect(self.featureClicked.emit)
            item.generateClicked.connect(self.featureGenerateClicked.emit)
            layout.addWidget(item)
            self._feature_items.append(item)

    def _on_header_click(self, event):
        """头部点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()

    def _toggle_expand(self):
        """切换展开状态"""
        self._expanded = not self._expanded
        self.features_container.setVisible(self._expanded)
        self.expand_icon.setText("-" if self._expanded else "+")

    def setFeatureSelected(self, feature_number: int):
        """设置功能选中状态"""
        for item in self._feature_items:
            item.setSelected(item.feature_number == feature_number)

    def clearSelection(self):
        """清除选中"""
        for item in self._feature_items:
            item.setSelected(False)

    def expandIfContains(self, feature_number: int) -> bool:
        """如果包含指定功能则展开"""
        for item in self._feature_items:
            if item.feature_number == feature_number:
                if not self._expanded:
                    self._toggle_expand()
                return True
        return False

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#sidebar_module_node {{
                background-color: transparent;
                border: none;
            }}
            QFrame#module_header {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
            }}
            QFrame#module_header:hover {{
                border-color: {theme_manager.PRIMARY}60;
            }}
            QLabel#expand_icon {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-weight: bold;
            }}
            QLabel#module_num {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(10)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#module_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#feature_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(10)}px;
            }}
            QWidget#features_container {{
                background-color: transparent;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-style: italic;
            }}
        """)


class SidebarSystemNode(ThemeAwareFrame):
    """侧边栏系统节点（顶层，主题感知）"""

    featureClicked = pyqtSignal(int)  # feature_number
    featureGenerateClicked = pyqtSignal(int)  # feature_number

    def __init__(
        self,
        system_data: Dict[str, Any],
        modules: List[Dict] = None,
        features: List[Dict] = None,
        parent=None
    ):
        self.system_data = system_data
        self.system_number = system_data.get('system_number', 0)
        self.modules = modules or []
        self.all_features = features or []
        self._expanded = True  # 默认展开
        self._module_nodes: List[SidebarModuleNode] = []
        self.header = None
        self.expand_icon = None
        self.modules_container = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("sidebar_system_node")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 系统头部
        self.header = QFrame()
        self.header.setObjectName("system_header")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setFixedHeight(dp(36))
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(dp(8), dp(4), dp(8), dp(4))
        header_layout.setSpacing(dp(6))

        # 展开图标
        self.expand_icon = QLabel("-")
        self.expand_icon.setObjectName("expand_icon")
        self.expand_icon.setFixedWidth(dp(14))
        header_layout.addWidget(self.expand_icon)

        # 系统编号
        num_label = QLabel(f"S{self.system_number}")
        num_label.setObjectName("system_num")
        num_label.setFixedWidth(dp(28))
        header_layout.addWidget(num_label)

        # 系统名称
        name = self.system_data.get('name', f'系统{self.system_number}')
        name_label = QLabel(name)
        name_label.setObjectName("system_name")
        header_layout.addWidget(name_label, 1)

        # 模块数量
        count_label = QLabel(f"{len(self.modules)}")
        count_label.setObjectName("module_count")
        header_layout.addWidget(count_label)

        layout.addWidget(self.header)

        # 模块列表容器
        self.modules_container = QWidget()
        self.modules_container.setObjectName("modules_container")
        modules_layout = QVBoxLayout(self.modules_container)
        modules_layout.setContentsMargins(dp(12), dp(4), 0, dp(4))
        modules_layout.setSpacing(dp(4))

        self._populate_modules(modules_layout)
        layout.addWidget(self.modules_container)

        # 头部点击事件
        self.header.mousePressEvent = self._on_header_click

    def _populate_modules(self, layout):
        """填充模块列表"""
        for node in self._module_nodes:
            node.deleteLater()
        self._module_nodes.clear()

        if not self.modules:
            empty_label = QLabel("暂无模块")
            empty_label.setObjectName("empty_hint")
            layout.addWidget(empty_label)
            return

        for module in self.modules:
            module_num = module.get('module_number', 0)
            # 筛选该模块下的功能
            module_features = [
                f for f in self.all_features
                if f.get('module_number') == module_num
            ]

            node = SidebarModuleNode(module, module_features)
            node.featureClicked.connect(self.featureClicked.emit)
            node.featureGenerateClicked.connect(self.featureGenerateClicked.emit)
            layout.addWidget(node)
            self._module_nodes.append(node)

    def _on_header_click(self, event):
        """头部点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()

    def _toggle_expand(self):
        """切换展开状态"""
        self._expanded = not self._expanded
        self.modules_container.setVisible(self._expanded)
        self.expand_icon.setText("-" if self._expanded else "+")

    def setFeatureSelected(self, feature_number: int):
        """设置功能选中状态"""
        for node in self._module_nodes:
            node.clearSelection()
            if node.expandIfContains(feature_number):
                node.setFeatureSelected(feature_number)

    def clearSelection(self):
        """清除选中"""
        for node in self._module_nodes:
            node.clearSelection()

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame#sidebar_system_node {{
                background-color: transparent;
                border: none;
            }}
            QFrame#system_header {{
                background-color: {theme_manager.PRIMARY}08;
                border: 1px solid {theme_manager.PRIMARY}30;
                border-radius: {dp(6)}px;
            }}
            QFrame#system_header:hover {{
                border-color: {theme_manager.PRIMARY};
            }}
            QLabel#expand_icon {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(12)}px;
                font-weight: bold;
            }}
            QLabel#system_num {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(11)}px;
                font-weight: bold;
                font-family: Consolas, monospace;
            }}
            QLabel#system_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
                font-weight: 600;
            }}
            QLabel#module_count {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(11)}px;
            }}
            QWidget#modules_container {{
                background-color: transparent;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-style: italic;
            }}
        """)


class CDSidebar(ThemeAwareFrame):
    """CodingDesk侧边栏 - 三级结构（主题感知）"""

    featureSelected = pyqtSignal(int)  # feature_number (1-based)
    generateFeature = pyqtSignal(int)  # feature_number (1-based)

    def __init__(self, parent=None):
        self.project = None
        self._system_nodes: List[SidebarSystemNode] = []
        self._selected_feature_number: Optional[int] = None
        self.stats_label = None
        self.list_container = None
        self.list_layout = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("cd_sidebar")
        self.setFixedWidth(dp(280))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setObjectName("sidebar_header")
        header.setFixedHeight(dp(48))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(16), 0, dp(16), 0)

        title_label = QLabel("项目结构")
        title_label.setObjectName("sidebar_title")
        header_layout.addWidget(title_label)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("stats_label")
        header_layout.addWidget(self.stats_label)

        header_layout.addStretch()

        layout.addWidget(header)

        # 系统列表滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        self.list_layout.setSpacing(dp(8))
        self.list_layout.addStretch()

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll, 1)

    def setProject(self, project: Dict[str, Any]):
        """设置项目数据"""
        self.project = project
        self._populate_structure()

    def _populate_structure(self):
        """填充三级结构"""
        # 清除现有节点
        for node in self._system_nodes:
            node.deleteLater()
        self._system_nodes.clear()

        if not self.project:
            return

        # 从blueprint获取三层数据
        blueprint = self.project.get('blueprint') or {}
        systems = blueprint.get('systems', [])
        modules = blueprint.get('modules', [])
        features = blueprint.get('features', [])

        # features 现在直接包含 status 和 has_content 字段
        # 创建 feature_map 供后续使用
        feature_map = {f.get('feature_number'): f for f in features}

        # 为每个功能确保有状态字段（兼容旧数据）
        for feature in features:
            if 'status' not in feature:
                # 如果没有status字段，检查has_content
                if feature.get('has_content'):
                    feature['status'] = 'generated'
                else:
                    feature['status'] = 'pending'

        # 更新统计
        self.stats_label.setText(f"{len(systems)}S/{len(modules)}M/{len(features)}F")

        # 如果没有系统，显示空状态或使用旧的扁平模式
        if not systems:
            self._populate_flat_features(blueprint, feature_map)
            return

        # 按系统构建三级结构
        for system in systems:
            system_num = system.get('system_number', 0)
            # 筛选该系统下的模块
            system_modules = [
                m for m in modules
                if m.get('system_number') == system_num
            ]

            # 筛选该系统下的所有功能（通过模块编号）
            system_module_nums = {m.get('module_number') for m in system_modules}
            system_features = [
                f for f in features
                if f.get('module_number') in system_module_nums
            ]

            node = SidebarSystemNode(system, system_modules, system_features)
            node.featureClicked.connect(self._on_feature_clicked)
            node.featureGenerateClicked.connect(self.generateFeature.emit)
            self.list_layout.insertWidget(self.list_layout.count() - 1, node)
            self._system_nodes.append(node)

        # 如果有功能，默认选中第一个
        if features:
            first_feature_num = features[0].get('feature_number', 1)
            self._on_feature_clicked(first_feature_num)

    def _populate_flat_features(self, blueprint: Dict, feature_map: Dict):
        """兼容旧的扁平功能列表（当没有系统划分时）"""
        # 获取功能列表（可能是features或chapter_outline或modules）
        features = blueprint.get('features', [])
        if not features:
            features = blueprint.get('chapter_outline', [])
        if not features:
            features = blueprint.get('modules', [])

        if not features:
            # 显示空状态
            empty_label = QLabel("暂无项目结构\n\n请先在项目详情中\n生成系统划分")
            empty_label.setObjectName("empty_state")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet(f"""
                QLabel#empty_state {{
                    color: {theme_manager.TEXT_TERTIARY};
                    font-size: {dp(13)}px;
                    padding: {dp(20)}px;
                }}
            """)
            self.list_layout.insertWidget(0, empty_label)
            return

        # 为每个功能添加状态并转换为feature格式
        converted_features = []
        for idx, feature in enumerate(features):
            feature_num = feature.get('feature_number') or feature.get('chapter_number', idx + 1)
            existing_feature = feature_map.get(feature_num)

            converted = {
                'feature_number': feature_num,
                'name': feature.get('name') or feature.get('title', f'功能{feature_num}'),
                'module_number': feature.get('module_number', 1),
                'system_number': feature.get('system_number', 1),
                'status': 'pending',
            }
            # 使用已有的状态信息
            if existing_feature:
                if existing_feature.get('has_content'):
                    converted['status'] = 'generated'
                elif existing_feature.get('status'):
                    converted['status'] = existing_feature.get('status')

            converted_features.append(converted)

        # 创建一个虚拟系统节点
        virtual_system = {
            'system_number': 1,
            'name': '功能列表',
        }
        virtual_module = {
            'module_number': 1,
            'name': '全部功能',
        }
        for f in converted_features:
            f['module_number'] = 1

        node = SidebarSystemNode(virtual_system, [virtual_module], converted_features)
        node.featureClicked.connect(self._on_feature_clicked)
        node.featureGenerateClicked.connect(self.generateFeature.emit)
        self.list_layout.insertWidget(self.list_layout.count() - 1, node)
        self._system_nodes.append(node)

        # 默认选中第一个
        if converted_features:
            first_feature_num = converted_features[0].get('feature_number', 1)
            self._on_feature_clicked(first_feature_num)

    def _on_feature_clicked(self, feature_number: int):
        """功能被点击"""
        # 更新选中状态
        for node in self._system_nodes:
            node.clearSelection()
            node.setFeatureSelected(feature_number)

        self._selected_feature_number = feature_number
        self.featureSelected.emit(feature_number)

    def selectFeature(self, feature_number: int):
        """外部调用选中功能"""
        self._on_feature_clicked(feature_number)

    def _apply_theme(self):
        """应用主题样式"""
        from themes.modern_effects import ModernEffects

        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        sidebar_opacity = theme_manager.get_component_opacity("sidebar")

        if transparency_enabled:
            sidebar_bg = ModernEffects.hex_to_rgba(
                theme_manager.book_bg_secondary(),
                sidebar_opacity
            )
        else:
            sidebar_bg = theme_manager.book_bg_secondary()

        self.setStyleSheet(f"""
            QFrame#cd_sidebar {{
                background-color: {sidebar_bg};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
            }}
            QWidget#sidebar_header {{
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
            QLabel#sidebar_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#stats_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                margin-left: {dp(8)}px;
            }}
        """)


__all__ = ["CDSidebar"]
