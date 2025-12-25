"""
组件样式 Mixin

提供卡片、输入框、标签页、滚动条等通用组件的样式方法。
根据主题模式提供差异化的组件风格：
- 深色主题 (Academia): 边框定位、微圆角、木纹边框
- 浅色主题 (Organic): 阴影定位、大圆角、柔和边框
"""

from ..modern_effects import ModernEffects


class ComponentStylesMixin:
    """组件样式方法 Mixin"""

    def _get_card_radius(self) -> str:
        """获取卡片圆角 - 根据主题差异化"""
        if self.is_dark_mode():
            # Academia: 传统微圆角
            return self.RADIUS_SM  # 4px
        else:
            # Organic: 较大圆角
            return self.RADIUS_LG  # 8px

    def card_style(self, elevated: bool = False) -> str:
        """卡片样式 - 支持普通和浮起效果

        深色主题 (Academia): 边框定位，木纹边框，hover时黄铜边框
        浅色主题 (Organic): 阴影定位，柔和边框，hover时阴影增强

        注意：Qt StyleSheet 不支持 box-shadow。
        阴影效果应通过 QGraphicsDropShadowEffect 实现。
        """
        radius = self._get_card_radius()

        if self.is_dark_mode():
            # Academia: 边框为主，无阴影
            if elevated:
                return f"""
                    background-color: {self.BG_CARD};
                    border-radius: {radius};
                    border: 1px solid {self.BORDER_DEFAULT};
                """
            else:
                return f"""
                    background-color: {self.BG_CARD};
                    border: 1px solid {self.BORDER_LIGHT};
                    border-radius: {radius};
                """
        else:
            # Organic: 更柔和的边框
            if elevated:
                return f"""
                    background-color: {self.BG_CARD};
                    border-radius: {self.RADIUS_LG};
                    border: 1px solid {self.BORDER_LIGHT};
                """
            else:
                return f"""
                    background-color: {self.BG_CARD};
                    border: 1px solid {self.BORDER_LIGHT};
                    border-radius: {radius};
                """

    def glass_card_style(self) -> str:
        """玻璃卡片样式

        注意：Qt StyleSheet 不支持 box-shadow。
        阴影效果应通过 QGraphicsDropShadowEffect 实现。
        """
        return f"""
            {ModernEffects.glassmorphism_card(self.is_dark_mode())}
            border-radius: {self.RADIUS_LG};
        """

    def _get_input_radius(self) -> str:
        """获取输入框圆角 - 根据主题差异化"""
        if self.is_dark_mode():
            # Academia: 传统微圆角
            return self.RADIUS_SM  # 4px
        else:
            # Organic: 中等圆角
            return self.RADIUS_MD  # 6px

    def input_style(self) -> str:
        """输入框样式 - 现代化设计

        深色主题 (Academia): 微圆角，黄铜focus边框，木纹默认边框
        浅色主题 (Organic): 中等圆角，苔藓绿focus边框，柔和边框

        注意：Qt StyleSheet 不支持 box-shadow（glow_effect）。
        发光效果应通过 QGraphicsDropShadowEffect 实现。
        """
        radius = self._get_input_radius()
        ui_font = self.ui_font()

        if self.is_dark_mode():
            # Academia: 古老橡木背景，木纹边框
            return f"""
                QLineEdit, QTextEdit {{
                    background-color: {self.BG_SECONDARY};
                    border: 1px solid {self.BORDER_DEFAULT};
                    border-radius: {radius};
                    padding: 10px 12px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_BASE};
                    color: {self.TEXT_PRIMARY};
                }}
                QLineEdit:focus, QTextEdit:focus {{
                    border-color: {self.PRIMARY};
                    border-width: 2px;
                    background-color: {self.BG_SECONDARY};
                }}
                QLineEdit:hover, QTextEdit:hover {{
                    border-color: {self.BORDER_DARK};
                }}
                QLineEdit:disabled, QTextEdit:disabled {{
                    background-color: {self.BG_TERTIARY};
                    color: {self.TEXT_DISABLED};
                    border-color: {self.BORDER_LIGHT};
                }}
                QLineEdit::placeholder, QTextEdit::placeholder {{
                    color: {self.TEXT_PLACEHOLDER};
                    font-style: italic;
                }}
            """
        else:
            # Organic: 米白纸张背景，柔和边框
            return f"""
                QLineEdit, QTextEdit {{
                    background-color: {self.BG_SECONDARY};
                    border: 1px solid {self.BORDER_DEFAULT};
                    border-radius: {radius};
                    padding: 10px 12px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_BASE};
                    color: {self.TEXT_PRIMARY};
                }}
                QLineEdit:focus, QTextEdit:focus {{
                    border-color: {self.PRIMARY};
                    border-width: 2px;
                    background-color: {self.BG_SECONDARY};
                }}
                QLineEdit:hover, QTextEdit:hover {{
                    border-color: {self.PRIMARY_LIGHT};
                }}
                QLineEdit:disabled, QTextEdit:disabled {{
                    background-color: {self.BG_TERTIARY};
                    color: {self.TEXT_DISABLED};
                    border-color: {self.BORDER_LIGHT};
                }}
                QLineEdit::placeholder, QTextEdit::placeholder {{
                    color: {self.TEXT_PLACEHOLDER};
                }}
            """

    def gradient_background(self, colors: list = None) -> str:
        """渐变背景样式"""
        if colors is None:
            colors = getattr(self._current_theme, 'BG_GRADIENT', [self.BG_PRIMARY, self.BG_SECONDARY])
        return ModernEffects.linear_gradient(colors, 180)

    def aurora_background(self) -> str:
        """极光背景效果"""
        return ModernEffects.aurora_bg(self.is_dark_mode())

    def loading_style(self) -> str:
        """加载动画样式"""
        # 注意：Qt StyleSheet 对 CSS animations 支持有限
        return """
            QLabel {
                color: palette(text);
            }
        """

    def hover_lift_effect(self) -> str:
        """悬停上浮效果

        注意：Qt StyleSheet 不支持 transform 和 box-shadow。
        实际的悬停效果应通过 QPropertyAnimation 实现。
        这里返回空字符串，仅作为占位。
        """
        return ""

    def theme_transition(self, duration: str = "0.3s") -> str:
        """主题切换过渡动画

        注意：Qt StyleSheet 对 transition 的支持有限，
        仅支持部分属性。box-shadow 不被支持。

        Args:
            duration: 过渡时长，默认0.3秒

        Returns:
            CSS过渡样式字符串（仅包含Qt支持的属性）
        """
        return f"""
            transition: background-color {duration} ease,
                        color {duration} ease,
                        border-color {duration} ease;
        """

    def tabs(self):
        """标签页样式 - 支持主题切换

        深色主题 (Academia): 微圆角，木纹边框，黄铜选中状态
        浅色主题 (Organic): 中等圆角，柔和边框，苔藓绿选中状态
        """
        ui_font = self.ui_font()

        if self.is_dark_mode():
            # Academia: 传统风格
            return f"""
                QTabWidget::pane {{
                    border: 1px solid {self.BORDER_DEFAULT};
                    border-radius: {self.RADIUS_SM};
                    background-color: {self.BG_CARD};
                    top: -1px;
                }}
                QTabBar::tab {{
                    padding: 10px 24px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_BASE};
                    font-weight: {self.FONT_WEIGHT_NORMAL};
                    color: {self.TEXT_SECONDARY};
                    background-color: transparent;
                    border: none;
                    border-bottom: 2px solid transparent;
                    margin-right: 4px;
                }}
                QTabBar::tab:selected {{
                    color: {self.PRIMARY};
                    border-bottom: 2px solid {self.PRIMARY};
                    font-weight: {self.FONT_WEIGHT_MEDIUM};
                }}
                QTabBar::tab:hover:!selected {{
                    color: {self.TEXT_PRIMARY};
                    background-color: {self.BG_TERTIARY};
                }}
                QTabBar::tab:focus {{
                    outline: 2px solid {self.PRIMARY};
                    outline-offset: -2px;
                }}
            """
        else:
            # Organic: 自然柔和风格
            return f"""
                QTabWidget::pane {{
                    border: 1px solid {self.BORDER_LIGHT};
                    border-radius: {self.RADIUS_MD};
                    background-color: {self.BG_CARD};
                    top: -1px;
                }}
                QTabBar::tab {{
                    padding: 10px 24px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_BASE};
                    font-weight: {self.FONT_WEIGHT_NORMAL};
                    color: {self.TEXT_SECONDARY};
                    background-color: transparent;
                    border: none;
                    border-bottom: 2px solid transparent;
                    margin-right: 4px;
                }}
                QTabBar::tab:selected {{
                    color: {self.PRIMARY};
                    border-bottom: 2px solid {self.PRIMARY};
                    font-weight: {self.FONT_WEIGHT_MEDIUM};
                }}
                QTabBar::tab:hover:!selected {{
                    color: {self.TEXT_PRIMARY};
                    background-color: {self.PRIMARY_PALE};
                }}
                QTabBar::tab:focus {{
                    outline: 2px solid {self.PRIMARY};
                    outline-offset: -2px;
                }}
            """

    def scrollbar(self):
        """返回滚动条样式 - 极简设计

        深色主题 (Academia): 木纹色调，深沉典雅
        浅色主题 (Organic): 自然色调，柔和有机
        """
        if self.is_dark_mode():
            # Academia: 木纹滚动条
            handle_color = self.BORDER_DEFAULT
            handle_hover = self.TEXT_TERTIARY
        else:
            # Organic: 柔和滚动条
            handle_color = self.BORDER_DEFAULT
            handle_hover = self.PRIMARY_LIGHT

        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {handle_color};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: transparent;
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {handle_color};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {handle_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    def combobox_style(self):
        """下拉框样式

        深色主题 (Academia): 微圆角，木纹边框
        浅色主题 (Organic): 中等圆角，柔和边框
        """
        radius = self._get_input_radius()
        ui_font = self.ui_font()

        return f"""
            QComboBox {{
                background-color: {self.BG_SECONDARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {radius};
                padding: 8px 12px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {self.PRIMARY_LIGHT};
            }}
            QComboBox:focus {{
                border-color: {self.PRIMARY};
                border-width: 2px;
            }}
            QComboBox:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.BG_CARD};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {radius};
                padding: 4px;
                selection-background-color: {self.PRIMARY_PALE};
                selection-color: {self.PRIMARY};
            }}
        """

    def checkbox_style(self):
        """复选框样式

        深色主题 (Academia): 微圆角，黄铜选中色
        浅色主题 (Organic): 中等圆角，苔藓绿选中色
        """
        if self.is_dark_mode():
            check_radius = self.RADIUS_XS
        else:
            check_radius = self.RADIUS_SM

        ui_font = self.ui_font()

        return f"""
            QCheckBox {{
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self.BORDER_DEFAULT};
                border-radius: {check_radius};
                background-color: {self.BG_SECONDARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.PRIMARY};
                border-color: {self.PRIMARY};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {self.BG_TERTIARY};
                border-color: {self.BORDER_LIGHT};
            }}
            QCheckBox:disabled {{
                color: {self.TEXT_DISABLED};
            }}
        """

    def radio_button_style(self):
        """单选按钮样式"""
        ui_font = self.ui_font()

        return f"""
            QRadioButton {{
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self.BORDER_DEFAULT};
                border-radius: 9px;
                background-color: {self.BG_SECONDARY};
            }}
            QRadioButton::indicator:hover {{
                border-color: {self.PRIMARY};
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.PRIMARY};
                border-color: {self.PRIMARY};
            }}
            QRadioButton::indicator:disabled {{
                background-color: {self.BG_TERTIARY};
                border-color: {self.BORDER_LIGHT};
            }}
            QRadioButton:disabled {{
                color: {self.TEXT_DISABLED};
            }}
        """

    def slider_style(self):
        """滑块样式

        深色主题 (Academia): 黄铜色滑块
        浅色主题 (Organic): 苔藓绿滑块
        """
        return f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background-color: {self.BG_TERTIARY};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background-color: {self.PRIMARY};
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {self.PRIMARY_LIGHT};
            }}
            QSlider::sub-page:horizontal {{
                background-color: {self.PRIMARY};
                border-radius: 2px;
            }}
            QSlider::add-page:horizontal {{
                background-color: {self.BG_TERTIARY};
                border-radius: 2px;
            }}
        """

    def progress_bar_style(self):
        """进度条样式

        深色主题 (Academia): 黄铜色进度
        浅色主题 (Organic): 苔藓绿进度
        """
        if self.is_dark_mode():
            radius = self.RADIUS_XS
        else:
            radius = self.RADIUS_SM

        return f"""
            QProgressBar {{
                border: none;
                border-radius: {radius};
                background-color: {self.BG_TERTIARY};
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.PRIMARY};
                border-radius: {radius};
            }}
        """

    def tooltip_style(self):
        """工具提示样式"""
        ui_font = self.ui_font()

        return f"""
            QToolTip {{
                background-color: {self.BG_CARD};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_SM};
                padding: 6px 10px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
            }}
        """

    def menu_style(self):
        """菜单样式"""
        ui_font = self.ui_font()
        radius = self._get_card_radius()

        return f"""
            QMenu {{
                background-color: {self.BG_CARD};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {radius};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
                border-radius: {self.RADIUS_XS};
            }}
            QMenu::item:selected {{
                background-color: {self.PRIMARY_PALE};
                color: {self.PRIMARY};
            }}
            QMenu::item:disabled {{
                color: {self.TEXT_DISABLED};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self.BORDER_LIGHT};
                margin: 4px 8px;
            }}
        """
