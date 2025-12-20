"""
组件样式 Mixin

提供卡片、输入框、标签页、滚动条等通用组件的样式方法。
"""

from ..modern_effects import ModernEffects


class ComponentStylesMixin:
    """组件样式方法 Mixin"""

    def card_style(self, elevated: bool = False) -> str:
        """卡片样式 - 支持普通和浮起效果

        注意：Qt StyleSheet 不支持 box-shadow。
        阴影效果应通过 QGraphicsDropShadowEffect 实现。
        """
        if elevated:
            # 浮起卡片 - 新拟态效果（移除不支持的shadow transition）
            return f"""
                background-color: {self.BG_CARD};
                border-radius: {self.RADIUS_LG};
                border: 1px solid {self.BORDER_LIGHT};
            """
        else:
            # 普通卡片
            return f"""
                background-color: {self.BG_CARD};
                border: 1px solid {self.BORDER_LIGHT};
                border-radius: {self.RADIUS_MD};
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

    def input_style(self) -> str:
        """输入框样式 - 现代化设计

        注意：Qt StyleSheet 不支持 box-shadow（glow_effect）。
        发光效果应通过 QGraphicsDropShadowEffect 实现。
        """
        return f"""
            QLineEdit, QTextEdit {{
                background-color: {self.BG_CARD};
                border: 2px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_SM};
                padding: 10px 12px;
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {self.PRIMARY};
                background-color: {self.BG_CARD};
            }}
            QLineEdit:hover, QTextEdit:hover {{
                border-color: {self.PRIMARY_LIGHT};
            }}
            QLineEdit:disabled, QTextEdit:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
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
        """标签页样式 - 支持主题切换"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {self.BORDER_LIGHT};
                border-radius: {self.RADIUS_SM};
                background-color: {self.BG_CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                padding: 8px 24px;
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
                background-color: {self.BG_SECONDARY};
            }}
            QTabBar::tab:focus {{
                outline: 2px solid {self.PRIMARY};
                outline-offset: -2px;
            }}
        """

    def scrollbar(self):
        """返回滚动条样式 - 极简设计，符合中国风美学"""
        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.BORDER_DEFAULT};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.TEXT_TERTIARY};
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
                background-color: {self.BORDER_DEFAULT};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """
