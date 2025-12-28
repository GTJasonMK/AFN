"""
灵感选项卡片组件

显示AI提供的创意方向选项，支持点击选择。
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCursor

from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens


class InspiredOptionCard(TransparencyAwareMixin, ThemeAwareWidget):
    """
    灵感选项卡片

    显示一个可选择的创意方向选项，包含：
    - 编号标识
    - 标题
    - 详细描述
    - 关键要素标签列表

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符
    _transparency_component_id = "card"

    clicked = pyqtSignal(str, str)  # (option_id, label)

    def __init__(self, option_data: dict, parent=None):
        """
        初始化选项卡片

        Args:
            option_data: 选项数据，包含 id, label, description, key_elements
            parent: 父组件
        """
        self.option_data = option_data
        self.is_selected = False
        self.is_disabled = False  # 禁用状态
        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
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
        """更新主题样式 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        # 使用 theme_manager 的书香风格便捷方法
        ui_font = theme_manager.ui_font()
        bg_primary = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()
        is_dark = theme_manager.is_dark_mode()

        # 卡片基础样式
        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 使用objectName选择器来支持hover伪类
        self.setObjectName("inspiredOptionCard")

        if self.is_disabled:
            # 禁用状态 - 使用 theme_manager 的颜色，避免硬编码
            disabled_bg = theme_manager.BG_TERTIARY

            if self._transparency_enabled:
                bg_rgba = self._hex_to_rgba(disabled_bg, self._current_opacity * 0.7)
                border_rgba = self._hex_to_rgba(border_color, OpacityTokens.BORDER_LIGHT)
                self.setStyleSheet(f"""
                    QWidget#inspiredOptionCard {{
                        background: {bg_rgba};
                        border: 1px solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: 0;
                    }}
                """)
                self._make_widget_transparent(self)
            else:
                self.setStyleSheet(f"""
                    QWidget#inspiredOptionCard {{
                        background: {disabled_bg};
                        border: 1px solid {border_color};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: 0;
                    }}
                """)
            # 禁用时移除手型光标
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            selected_border = accent_color if self.is_selected else border_color
            border_width = "2px" if self.is_selected else "1px"

            if self._transparency_enabled:
                bg_rgba = self._hex_to_rgba(bg_secondary, self._current_opacity)
                bg_hover_rgba = self._hex_to_rgba(bg_primary, self._current_opacity)
                border_rgba = self._hex_to_rgba(selected_border, OpacityTokens.BORDER_STRONG if self.is_selected else OpacityTokens.BORDER_DEFAULT)

                self.setStyleSheet(f"""
                    QWidget#inspiredOptionCard {{
                        background: {bg_rgba};
                        border: {border_width} solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: 0;
                    }}

                    QWidget#inspiredOptionCard:hover {{
                        background: {bg_hover_rgba};
                        border-color: {accent_color};
                        border-width: 2px;
                    }}
                """)
                self._make_widget_transparent(self)
            else:
                self.setStyleSheet(f"""
                    QWidget#inspiredOptionCard {{
                        background: {bg_secondary};
                        border: {border_width} solid {selected_border};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: 0;
                    }}

                    QWidget#inspiredOptionCard:hover {{
                        background: {bg_primary};
                        border-color: {accent_color};
                        border-width: 2px;
                    }}
                """)
            # 启用时恢复手型光标
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 编号标签样式 - 书香风格
        self.number_label.setStyleSheet(f"""
            QLabel#numberLabel {{
                background: {accent_color};
                color: {theme_manager.BUTTON_TEXT};
                border-radius: 12px;
                font-family: {ui_font};
                font-weight: 600;
                font-size: 14px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            QLabel#titleLabel {{
                color: {text_primary};
                font-family: {ui_font};
                font-weight: 600;
                font-size: 15px;
            }}
        """)

        # 描述样式
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"""
                QLabel#descLabel {{
                    color: {text_secondary};
                    font-family: {ui_font};
                    font-size: 13px;
                    line-height: 1.5;
                }}
            """)

        # 标签样式 - 书香风格（使用 theme_manager 颜色）
        tag_labels = self.findChildren(QLabel, "tagLabel")
        if is_dark:
            # 深色主题：金色文字 + 深色暖色背景
            tag_text_color = accent_color
            tag_bg_color = f"{accent_color}25"  # 约15%透明度
        else:
            # 浅色主题：使用 theme_manager 颜色，避免硬编码
            tag_text_color = theme_manager.book_text_secondary()
            tag_bg_color = theme_manager.BG_TERTIARY

        for tag in tag_labels:
            tag.setStyleSheet(f"""
                QLabel#tagLabel {{
                    color: {tag_text_color};
                    background: {tag_bg_color};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: {ui_font};
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

        # 取消其他卡片的选中状态（检查对象有效性）
        for card in self.cards:
            try:
                if card.option_data.get('id') != option_id:
                    card.set_selected(False)
            except RuntimeError:
                # C++对象已被删除，跳过
                pass

        # 发射选择信号
        self.option_selected.emit(option_id, label)

    def lock(self):
        """锁定选项容器，禁止再次选择"""
        self.is_locked = True
        # 禁用所有卡片（检查对象是否仍有效）
        for card in self.cards:
            try:
                # 检查C++对象是否仍有效
                card.isVisible()  # 如果对象已删除，这会抛出RuntimeError
                card.set_disabled(True)
            except RuntimeError:
                # C++对象已被删除，跳过
                pass

    def unlock(self):
        """解锁选项容器，允许再次选择（用于错误恢复）"""
        self.is_locked = False
        # 启用所有卡片（检查对象是否仍有效）
        for card in self.cards:
            try:
                card.isVisible()
                card.set_disabled(False)
            except RuntimeError:
                pass

    def add_option(self, option_data: dict):
        """
        动态添加单个选项卡片（用于流式逐个显示）

        Args:
            option_data: 选项数据字典
        """
        if not option_data:
            return

        # 创建新卡片
        card = InspiredOptionCard(option_data)
        card.clicked.connect(self.on_card_clicked)
        self.cards.append(card)

        # 添加到布局
        self.layout().addWidget(card)

        # 更新选项数据
        self.options_data.append(option_data)

    def _apply_theme(self):
        """更新主题样式"""
        # 容器本身不需要特殊样式，由子卡片处理
        pass