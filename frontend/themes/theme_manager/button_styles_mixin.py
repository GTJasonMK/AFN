"""
按钮样式 Mixin

提供各种按钮样式的工厂方法。
"""

from ..modern_effects import ModernEffects


class ButtonStylesMixin:
    """按钮样式方法 Mixin"""

    def _solid_button_style(
        self,
        bg_color: str,
        bg_hover: str,
        bg_pressed: str,
        text_color: str = None,
        border: str = "none",
        padding: str = "8px 24px",
        min_height: str = "36px"
    ) -> str:
        """实心按钮样式工厂方法

        Args:
            bg_color: 背景颜色
            bg_hover: 悬停时背景颜色
            bg_pressed: 按下时背景颜色
            text_color: 文字颜色（默认为 BUTTON_TEXT）
            border: 边框样式（默认为 none）
            padding: 内边距（符合8pt网格：8px 24px）
            min_height: 最小高度

        Returns:
            QPushButton 样式表字符串
        """
        ui_font = self.ui_font()
        text = text_color or self.BUTTON_TEXT
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text};
                border: {border};
                border-radius: {self.RADIUS_SM};
                padding: {padding};
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: {min_height};
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {bg_pressed};
            }}
            QPushButton:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.PRIMARY};
                outline: none;
            }}
        """

    def button_primary(self):
        """主要按钮样式 - 渐变背景"""
        gradient_colors = self.PRIMARY_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 135)
        hover_gradient = ModernEffects.linear_gradient([self.PRIMARY_LIGHT, self.PRIMARY], 135)
        ui_font = self.ui_font()

        # 注意：Qt StyleSheet 不支持 box-shadow、transform 等 CSS3 属性
        # 渐变按钮需要特殊处理，不能使用工厂方法
        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {hover_gradient};
            }}
            QPushButton:pressed {{
                background: {self.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.PRIMARY_LIGHT};
                outline: none;
            }}
        """

    def button_secondary(self):
        """次要按钮样式 - 玻璃态效果"""
        glass_style = ModernEffects.glassmorphism_card(self.is_dark_mode())
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                {glass_style}
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_SM};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.PRIMARY_PALE};
                border-color: {self.PRIMARY};
                color: {self.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
                background: transparent;
            }}
            QPushButton:focus {{
                border: 2px solid {self.PRIMARY};
                outline: none;
            }}
        """

    def button_accent(self):
        """强调按钮样式 - 活力渐变"""
        gradient_colors = self.ACCENT_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 135)
        hover_gradient = ModernEffects.linear_gradient([self.ACCENT_LIGHT, self.ACCENT], 135)
        accent_dark = self.ACCENT_DARK if hasattr(self, 'ACCENT_DARK') else self.ACCENT
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {hover_gradient};
            }}
            QPushButton:pressed {{
                background: {accent_dark};
            }}
            QPushButton:disabled {{
                background: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.ACCENT_LIGHT};
                outline: none;
            }}
        """

    def button_text(self):
        """文本按钮样式 - 纯文本无边框"""
        ui_font = self.ui_font()
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 8px 16px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_MEDIUM};
                min-height: 32px;
            }}
            QPushButton:hover {{
                background-color: {self.BG_TERTIARY};
                color: {self.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_danger(self):
        """危险按钮样式 - 红色警告"""
        return self._solid_button_style(
            bg_color=self.ERROR,
            bg_hover=self.ERROR_DARK,
            bg_pressed=self.ERROR_DARK
        )

    def button_warning(self):
        """警告按钮样式 - 橙色提醒"""
        return self._solid_button_style(
            bg_color=self.WARNING,
            bg_hover=self.WARNING_DARK,
            bg_pressed=self.WARNING_DARK
        )

    def button_success(self):
        """成功按钮样式 - 绿色确认"""
        return self._solid_button_style(
            bg_color=self.SUCCESS,
            bg_hover=self.SUCCESS_DARK,
            bg_pressed=self.SUCCESS_DARK
        )
