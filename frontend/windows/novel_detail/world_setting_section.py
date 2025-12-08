"""
世界设定 Section - 现代化设计

展示世界观的核心规则、关键地点和主要阵营
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QPushButton,
    QWidget, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class WorldSettingSection(ThemeAwareWidget):
    """世界设定组件 - 现代化卡片设计"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, parent=None):
        self.data = data or {}
        self.editable = editable

        # 保存组件引用
        self.rules_card = None
        self.rules_content = None
        self.grid_widget = None
        self.locations_card = None
        self.factions_card = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(20))

        # 核心规则卡片（突出显示，带左边框）
        self.rules_card = self._createRulesCard()
        layout.addWidget(self.rules_card)

        # 关键地点和主要阵营（二列网格）
        self.grid_widget = QWidget()
        grid_layout = QGridLayout(self.grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(dp(16))

        # 关键地点 - 确保是列表类型
        key_locations = self.data.get('key_locations', [])
        if not isinstance(key_locations, list):
            key_locations = []
        self.locations_card = self._createListCard(
            '*',  # 地点图标
            '关键地点',
            key_locations,
            'world_setting.key_locations'
        )
        grid_layout.addWidget(self.locations_card, 0, 0)

        # 主要阵营 - 确保是列表类型
        factions = self.data.get('factions', [])
        if not isinstance(factions, list):
            factions = []
        self.factions_card = self._createListCard(
            '*',  # 剑图标
            '主要阵营',
            factions,
            'world_setting.factions'
        )
        grid_layout.addWidget(self.factions_card, 0, 1)

        layout.addWidget(self.grid_widget)
        layout.addStretch()

    def _createRulesCard(self):
        """创建核心规则卡片 - 带渐变左边框"""
        card = QFrame()
        card.setObjectName("rules_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(24), dp(20), dp(24), dp(20))
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        # 图标
        icon = QLabel("*")  # 地球图标
        icon.setStyleSheet(f"font-size: {sp(18)}px;")
        header.addWidget(icon)

        title = QLabel("核心规则")
        title.setObjectName("rules_title")
        header.addWidget(title)

        header.addStretch()

        if self.editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.editRequested.emit(
                'world_setting.core_rules', '核心规则', self.data.get('core_rules')
            ))
            header.addWidget(edit_btn)

        layout.addLayout(header)

        # 规则内容
        self.rules_content = QLabel(self.data.get('core_rules') or '暂无核心规则，点击编辑添加')
        self.rules_content.setObjectName("rules_content")
        self.rules_content.setWordWrap(True)
        layout.addWidget(self.rules_content)

        return card

    def _createListCard(self, icon_text, title, items, field):
        """创建列表卡片"""
        card = QFrame()
        card.setObjectName("list_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))
        card_layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon = QLabel(icon_text)
        icon.setStyleSheet(f"font-size: {sp(16)}px;")
        header.addWidget(icon)

        title_label = QLabel(title)
        title_label.setObjectName("list_title")
        header.addWidget(title_label)

        header.addStretch()

        if self.editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("list_edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setFixedSize(dp(48), dp(24))
            edit_btn.clicked.connect(lambda: self.editRequested.emit(field, title, items))
            header.addWidget(edit_btn)

        card_layout.addLayout(header)

        # 列表内容容器
        list_container = QWidget()
        list_container.setObjectName("list_container")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(dp(8))

        if not items:
            no_data = QLabel("暂无")
            no_data.setObjectName("no_data")
            list_layout.addWidget(no_data)
        else:
            for item in items:
                if isinstance(item, dict):
                    item_title = item.get('title', item.get('name', ''))
                    item_desc = item.get('description', '')
                elif isinstance(item, str):
                    item_title = item
                    item_desc = ''
                else:
                    continue

                item_widget = self._createListItem(item_title, item_desc)
                list_layout.addWidget(item_widget)

        card_layout.addWidget(list_container)

        # 存储引用以便更新
        card.list_container = list_container
        card.list_layout = list_layout

        return card

    def _createListItem(self, title, description=''):
        """创建列表项"""
        item = QFrame()
        item.setObjectName("list_item")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        layout.setSpacing(dp(4))

        if title:
            title_label = QLabel(f"\u2022 {title}")
            title_label.setObjectName("item_title")
            layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("item_desc")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        return item

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # 核心规则卡片 - 带渐变左边框
        if self.rules_card:
            self.rules_card.setStyleSheet(f"""
                #rules_card {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-left: 4px solid {theme_manager.PRIMARY};
                    border-radius: {dp(12)}px;
                }}
                #rules_title {{
                    font-family: {ui_font};
                    font-size: {sp(16)}px;
                    font-weight: 600;
                    color: {theme_manager.PRIMARY};
                }}
                #rules_content {{
                    font-family: {serif_font};
                    font-size: {sp(14)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                    line-height: 1.7;
                }}
                #edit_btn {{
                    background: transparent;
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: {dp(4)}px {dp(12)}px;
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
                #edit_btn:hover {{
                    background-color: {theme_manager.PRIMARY_PALE};
                    border-color: {theme_manager.PRIMARY};
                    color: {theme_manager.PRIMARY};
                }}
            """)

        # 列表卡片样式
        list_card_style = f"""
            #list_card {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
            }}
            #list_title {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #list_edit_btn {{
                background: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                font-size: {sp(11)}px;
                color: {theme_manager.TEXT_TERTIARY};
            }}
            #list_edit_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            #list_item {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {dp(8)}px;
            }}
            #item_title {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 500;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #item_desc {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(16)}px;
            }}
            #no_data {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_TERTIARY};
                padding: {dp(12)}px 0;
            }}
        """

        if self.locations_card:
            self.locations_card.setStyleSheet(list_card_style)
        if self.factions_card:
            self.factions_card.setStyleSheet(list_card_style)

    def updateData(self, new_data):
        """更新数据并刷新显示（避免重建组件）"""
        self.data = new_data

        # 更新核心规则文本
        if self.rules_content:
            rules = new_data.get('core_rules') or '暂无核心规则，点击编辑添加'
            self.rules_content.setText(rules)

        # 更新地点列表
        if self.locations_card and hasattr(self.locations_card, 'list_layout'):
            self._updateListCard(
                self.locations_card,
                new_data.get('key_locations', [])
            )

        # 更新阵营列表
        if self.factions_card and hasattr(self.factions_card, 'list_layout'):
            self._updateListCard(
                self.factions_card,
                new_data.get('factions', [])
            )

    def _updateListCard(self, card, items):
        """更新列表卡片内容"""
        list_layout = card.list_layout

        # 清空现有内容
        while list_layout.count():
            item = list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新内容
        if not items:
            no_data = QLabel("暂无")
            no_data.setObjectName("no_data")
            no_data.setStyleSheet(f"font-size: {sp(14)}px; color: {theme_manager.TEXT_TERTIARY}; padding: {dp(12)}px 0;")
            list_layout.addWidget(no_data)
        else:
            for item in items:
                if isinstance(item, dict):
                    item_title = item.get('title', item.get('name', ''))
                    item_desc = item.get('description', '')
                elif isinstance(item, str):
                    item_title = item
                    item_desc = ''
                else:
                    continue

                item_widget = self._createListItem(item_title, item_desc)
                # 需要重新应用样式
                item_widget.setStyleSheet(f"""
                    #list_item {{
                        background-color: {theme_manager.BG_TERTIARY};
                        border-radius: {dp(8)}px;
                    }}
                    #item_title {{
                        font-size: {sp(14)}px;
                        font-weight: 500;
                        color: {theme_manager.TEXT_PRIMARY};
                    }}
                    #item_desc {{
                        font-size: {sp(13)}px;
                        color: {theme_manager.TEXT_SECONDARY};
                        padding-left: {dp(16)}px;
                    }}
                """)
                list_layout.addWidget(item_widget)
