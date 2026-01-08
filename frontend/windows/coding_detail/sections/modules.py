"""
模块列表Section

显示编程项目的模块信息。
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class ModuleCard(QFrame):
    """单个模块卡片"""

    clicked = pyqtSignal(dict)  # 点击信号，传递模块数据

    def __init__(self, module_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("module_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(8))

        # 标题行
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(8))

        # 模块名称
        name = self.module_data.get('name', '未命名模块')
        name_label = QLabel(name)
        name_label.setObjectName("module_name")
        title_layout.addWidget(name_label)

        # 模块类型标签
        module_type = self.module_data.get('type', '')
        if module_type:
            type_badge = QLabel(module_type)
            type_badge.setObjectName("module_type_badge")
            title_layout.addWidget(type_badge)

        title_layout.addStretch()
        layout.addWidget(title_row)

        # 描述
        description = self.module_data.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("module_desc")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(dp(60))
            layout.addWidget(desc_label)

        # 接口信息
        interface = self.module_data.get('interface', '')
        if interface:
            interface_row = QWidget()
            interface_layout = QHBoxLayout(interface_row)
            interface_layout.setContentsMargins(0, 0, 0, 0)
            interface_layout.setSpacing(dp(4))

            interface_icon = QLabel("API:")
            interface_icon.setObjectName("module_label")
            interface_layout.addWidget(interface_icon)

            interface_text = QLabel(interface)
            interface_text.setObjectName("module_interface")
            interface_text.setWordWrap(True)
            interface_layout.addWidget(interface_text, 1)

            layout.addWidget(interface_row)

        # 目标和能力
        goals = self.module_data.get('goals', [])
        abilities = self.module_data.get('abilities', [])

        if goals:
            goals_text = "、".join(goals[:3])
            if len(goals) > 3:
                goals_text += f" 等{len(goals)}项"
            goals_row = self._create_info_row("目标:", goals_text)
            layout.addWidget(goals_row)

        if abilities:
            abilities_text = "、".join(abilities[:3])
            if len(abilities) > 3:
                abilities_text += f" 等{len(abilities)}项"
            abilities_row = self._create_info_row("能力:", abilities_text)
            layout.addWidget(abilities_row)

        self._apply_style()

    def _create_info_row(self, label: str, value: str) -> QWidget:
        """创建信息行"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        label_widget = QLabel(label)
        label_widget.setObjectName("module_label")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("module_value")
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget, 1)

        return row

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame#module_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QFrame#module_card:hover {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY}08;
            }}
            QLabel#module_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#module_type_badge {{
                color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY}15;
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
            }}
            QLabel#module_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
                line-height: 1.4;
            }}
            QLabel#module_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
            }}
            QLabel#module_interface {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-family: Consolas, monospace;
            }}
            QLabel#module_value {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
        """)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.module_data)
        super().mousePressEvent(event)


class ModulesSection(BaseSection):
    """模块列表Section

    显示：
    - 模块卡片列表
    - 每个模块的名称、类型、描述、接口、目标、能力
    """

    def __init__(self, data: List[Dict] = None, editable: bool = True, project_id: str = None, parent=None):
        self.project_id = project_id
        self._module_cards = []
        super().__init__(data or [], editable, parent)
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

        title_label = QLabel("模块列表")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        # 模块数量
        count = len(self._data) if self._data else 0
        count_label = QLabel(f"共 {count} 个模块")
        count_label.setObjectName("module_count")
        header_layout.addWidget(count_label)
        self.count_label = count_label

        header_layout.addStretch()

        if self._editable:
            add_btn = QPushButton("添加模块")
            add_btn.setObjectName("add_module_btn")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._on_add_module)
            header_layout.addWidget(add_btn)

        layout.addWidget(header)

        # 模块列表容器
        self.modules_container = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_container)
        self.modules_layout.setContentsMargins(0, 0, 0, 0)
        self.modules_layout.setSpacing(dp(12))

        # 填充模块卡片
        self._populate_modules()

        layout.addWidget(self.modules_container)
        layout.addStretch()

        self._apply_header_style()

    def _populate_modules(self):
        """填充模块卡片"""
        # 清除现有卡片
        for card in self._module_cards:
            card.deleteLater()
        self._module_cards.clear()

        if not self._data:
            empty_label = QLabel("暂无模块数据")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                QLabel#empty_label {{
                    color: {theme_manager.TEXT_TERTIARY};
                    font-size: {dp(14)}px;
                    padding: {dp(40)}px;
                }}
            """)
            self.modules_layout.addWidget(empty_label)
            self._module_cards.append(empty_label)
            return

        for module_data in self._data:
            card = ModuleCard(module_data)
            card.clicked.connect(self._on_module_clicked)
            self.modules_layout.addWidget(card)
            self._module_cards.append(card)

    def _apply_header_style(self):
        """应用标题样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QLabel#module_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(8)}px;
            }}
            QPushButton#add_module_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#add_module_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_header_style()
        for card in self._module_cards:
            if isinstance(card, ModuleCard):
                card._apply_style()

    def _on_add_module(self):
        """添加模块"""
        self.requestEdit('modules.add', '添加模块', '')

    def _on_module_clicked(self, module_data: Dict):
        """模块点击处理"""
        module_name = module_data.get('name', '')
        self.requestEdit(f'modules.{module_name}', f'编辑模块: {module_name}', module_data)

    def updateData(self, data: List[Dict]):
        """更新数据"""
        self._data = data or []

        # 更新计数
        if hasattr(self, 'count_label') and self.count_label:
            count = len(self._data)
            self.count_label.setText(f"共 {count} 个模块")

        # 重新填充模块
        self._populate_modules()


__all__ = ["ModulesSection"]
