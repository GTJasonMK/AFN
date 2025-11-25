"""
灵感选项卡片组件

显示AI提供的创意方向选项，支持点击选择。
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCursor

from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager


class InspiredOptionCard(ThemeAwareWidget):
    """
    灵感选项卡片

    显示一个可选择的创意方向选项，包含：
    - 编号标识
    - 标题
    - 详细描述
    - 关键要素标签列表
    """

    clicked = pyqtSignal(str, str)  # (option_id, label)

    def __init__(self, option_data: dict, parent=None):
        """
        初始化选项卡片

        Args:
            option_data: 选项数据，包含 id, label, description, key_elements
            parent: 父组件
        """
        super().__init__(parent)
        self.option_data = option_data
        self.is_selected = False
        self.is_disabled = False  # 禁用状态
        self.setupUI()

        # 设置鼠标光标为手型
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _create_ui_structure(self):
        """初始化UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 标题行：编号 + 标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 提取编号（从id中提取数字，如 "opt_1" -> "1"）
        option_number = self.option_data.get('id', '').split('_')[-1]

        # 编号标签
        self.number_label = QLabel(option_number)
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label.setFixedSize(24, 24)
        self.number_label.setObjectName("numberLabel")
        title_layout.addWidget(self.number_label)

        # 标题标签
        self.title_label = QLabel(self.option_data.get('label', ''))
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label, 1)

        layout.addLayout(title_layout)

        # 描述文本
        description = self.option_data.get('description', '')
        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setWordWrap(True)
            self.desc_label.setObjectName("descLabel")
            layout.addWidget(self.desc_label)

        # 关键要素标签
        key_elements = self.option_data.get('key_elements', [])
        if key_elements:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(8)
            tags_layout.setContentsMargins(0, 4, 0, 0)

            for element in key_elements:
                tag = QLabel(f"#{element}")
                tag.setObjectName("tagLabel")
                tags_layout.addWidget(tag)

            tags_layout.addStretch()
            layout.addLayout(tags_layout)

    def _apply_theme(self):
        """更新主题样式"""
        is_dark = theme_manager.is_dark_mode()

        # 卡片基础样式
        if self.is_disabled:
            # 禁用状态 - 降低透明度，移除交互效果
            border_color = theme_manager.BORDER_LIGHT
            border_width = "1px"
            bg_color = theme_manager.BG_TERTIARY if is_dark else "#F3F4F6"
            opacity = "0.6"

            self.setStyleSheet(f"""
                InspiredOptionCard {{
                    background: {bg_color};
                    border: {border_width} solid {border_color};
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 0;
                }}
            """)
            # 禁用时移除手型光标
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            border_color = theme_manager.ACCENT_PRIMARY if self.is_selected else theme_manager.BORDER_LIGHT
            border_width = "2px" if self.is_selected else "1px"

            bg_color = theme_manager.BG_SECONDARY if is_dark else "#FFFFFF"
            hover_bg = theme_manager.BG_PRIMARY if is_dark else "#F9FAFB"

            self.setStyleSheet(f"""
                InspiredOptionCard {{
                    background: {bg_color};
                    border: {border_width} solid {border_color};
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 0;
                }}

                InspiredOptionCard:hover {{
                    background: {hover_bg};
                    border-color: {theme_manager.ACCENT_PRIMARY};
                    border-width: 2px;
                }}
            """)
            # 启用时恢复手型光标
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 编号标签样式
        self.number_label.setStyleSheet(f"""
            QLabel#numberLabel {{
                background: {theme_manager.ACCENT_PRIMARY};
                color: #FFFFFF;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            QLabel#titleLabel {{
                color: {theme_manager.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 15px;
            }}
        """)

        # 描述样式
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"""
                QLabel#descLabel {{
                    color: {theme_manager.TEXT_SECONDARY};
                    font-size: 13px;
                    line-height: 1.5;
                }}
            """)

        # 标签样式
        tag_labels = self.findChildren(QLabel, "tagLabel")
        for tag in tag_labels:
            tag.setStyleSheet(f"""
                QLabel#tagLabel {{
                    color: {theme_manager.ACCENT_PRIMARY};
                    background: {theme_manager.ACCENT_PRIMARY}22;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        # 禁用状态时忽略点击
        if self.is_disabled:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selected = True
            self.refresh_theme()
            self.clicked.emit(
                self.option_data.get('id', ''),
                self.option_data.get('label', '')
            )
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.refresh_theme()

    def set_disabled(self, disabled: bool):
        """设置禁用状态"""
        self.is_disabled = disabled
        self.refresh_theme()


class InspiredOptionsContainer(ThemeAwareWidget):
    """
    灵感选项容器

    包含多个选项卡片的容器，支持选择其中一个选项。
    """

    option_selected = pyqtSignal(str, str)  # (option_id, label)

    def __init__(self, options_data: list, parent=None):
        """
        初始化选项容器

        Args:
            options_data: 选项列表
            parent: 父组件
        """
        super().__init__(parent)
        self.options_data = options_data
        self.cards = []
        self.selected_card = None
        self.is_locked = False  # 锁定状态
        self.setupUI()

    def _create_ui_structure(self):
        """初始化UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 创建选项卡片
        for option_data in self.options_data:
            card = InspiredOptionCard(option_data)
            card.clicked.connect(self.on_card_clicked)
            self.cards.append(card)
            layout.addWidget(card)

    def on_card_clicked(self, option_id: str, label: str):
        """处理卡片点击事件"""
        # 如果已锁定，忽略点击
        if self.is_locked:
            return

        # 取消其他卡片的选中状态
        for card in self.cards:
            if card.option_data.get('id') != option_id:
                card.set_selected(False)

        # 发射选择信号
        self.option_selected.emit(option_id, label)

    def lock(self):
        """锁定选项容器，禁止再次选择"""
        self.is_locked = True
        # 禁用所有卡片
        for card in self.cards:
            card.set_disabled(True)

    def _apply_theme(self):
        """更新主题样式"""
        # 容器本身不需要特殊样式，由子卡片处理
        pass
