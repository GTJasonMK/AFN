"""
按钮样式 Mixin

提供各种按钮样式的工厂方法。
根据主题模式提供差异化的按钮风格：
- 深色主题 (Academia): 黄铜渐变、浮雕效果、微圆角
- 浅色主题 (Organic): 苔藓绿、柔和阴影、药丸形圆角
"""

from ..modern_effects import ModernEffects


class ButtonStylesMixin:
    """按钮样式方法 Mixin"""

    def _get_button_radius(self) -> str:
        """获取按钮圆角 - 根据主题差异化"""
        if self.is_dark_mode():
            # Academia: 传统微圆角
            return self.RADIUS_SM  # 4px
        else:
            # Organic: 药丸形
            return self.RADIUS_2XL  # 24px

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
        radius = self._get_button_radius()

        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text};
                border: {border};
                border-radius: {radius};
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
        """主要按钮样式

        深色主题 (Academia): 黄铜渐变 + 深色文字
        浅色主题 (Organic): 苔藓绿渐变 + 浅色文字
        """
        gradient_colors = self.PRIMARY_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 180)
        hover_gradient = ModernEffects.linear_gradient([self.PRIMARY_LIGHT, self.PRIMARY], 180)
        ui_font = self.ui_font()
        radius = self._get_button_radius()

        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {radius};
                padding: 10px 32px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 40px;
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
        """次要按钮样式

        深色主题 (Academia): 透明 + 黄铜边框，hover变深红
        浅色主题 (Organic): 透明 + 陶土色边框
        """
        ui_font = self.ui_font()
        radius = self._get_button_radius()

        if self.is_dark_mode():
            # Academia: 黄铜边框，hover变深红
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.PRIMARY};
                    border: 2px solid {self.PRIMARY};
                    border-radius: {radius};
                    padding: 8px 32px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_SM};
                    font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                    min-height: 40px;
                }}
                QPushButton:hover {{
                    background-color: {self.ACCENT};
                    border-color: {self.ACCENT};
                    color: {self.TEXT_PRIMARY};
                }}
                QPushButton:pressed {{
                    background-color: {self.ACCENT_DARK};
                    border-color: {self.ACCENT_DARK};
                }}
                QPushButton:disabled {{
                    color: {self.TEXT_DISABLED};
                    border-color: {self.BORDER_LIGHT};
                    background: transparent;
                }}
                QPushButton:focus {{
                    border: 2px solid {self.PRIMARY_LIGHT};
                    outline: none;
                }}
            """
        else:
            # Organic: 陶土色边框
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.ACCENT};
                    border: 2px solid {self.ACCENT};
                    border-radius: {radius};
                    padding: 8px 32px;
                    font-family: {ui_font};
                    font-size: {self.FONT_SIZE_SM};
                    font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                    min-height: 40px;
                }}
                QPushButton:hover {{
                    background-color: {self.ACCENT};
                    color: {self.BUTTON_TEXT};
                }}
                QPushButton:pressed {{
                    background-color: {self.ACCENT_DARK};
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
        """强调按钮样式

        深色主题 (Academia): 深红渐变
        浅色主题 (Organic): 陶土色渐变
        """
        gradient_colors = self.ACCENT_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 180)
        hover_gradient = ModernEffects.linear_gradient([self.ACCENT_LIGHT, self.ACCENT], 180)
        accent_dark = self.ACCENT_DARK if hasattr(self, 'ACCENT_DARK') else self.ACCENT
        ui_font = self.ui_font()
        radius = self._get_button_radius()

        # 深色主题使用羊皮纸色文字，浅色主题使用白色
        text_color = self.TEXT_PRIMARY if self.is_dark_mode() else self.BUTTON_TEXT

        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {text_color};
                border: none;
                border-radius: {radius};
                padding: 10px 32px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 40px;
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
        """文本按钮样式 - 纯文本无边框

        深色主题 (Academia): 黄铜色文字，hover下划线
        浅色主题 (Organic): 苔藓绿文字
        """
        ui_font = self.ui_font()
        text_color = self.PRIMARY

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 8px 16px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_MEDIUM};
                min-height: 32px;
            }}
            QPushButton:hover {{
                background-color: {self.PRIMARY_PALE};
                color: {self.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_ghost(self):
        """幽灵按钮样式 - 最小化视觉重量

        适用于次要操作、取消按钮等
        """
        ui_font = self.ui_font()
        radius = self._get_button_radius()

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {radius};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.BG_TERTIARY};
                border-color: {self.BORDER_DARK};
                color: {self.TEXT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
            }}
        """

    def button_danger(self):
        """危险按钮样式 - 红色警告"""
        radius = self._get_button_radius()
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background-color: {self.ERROR};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {radius};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.ERROR_DARK};
            }}
            QPushButton:pressed {{
                background-color: {self.ERROR_DARK};
            }}
            QPushButton:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.ERROR_LIGHT};
                outline: none;
            }}
        """

    def button_warning(self):
        """警告按钮样式 - 橙色提醒"""
        radius = self._get_button_radius()
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background-color: {self.WARNING};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {radius};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.WARNING_DARK};
            }}
            QPushButton:pressed {{
                background-color: {self.WARNING_DARK};
            }}
            QPushButton:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.WARNING_LIGHT};
                outline: none;
            }}
        """

    def button_success(self):
        """成功按钮样式 - 绿色确认"""
        radius = self._get_button_radius()
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background-color: {self.SUCCESS};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {radius};
                padding: 8px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.SUCCESS_DARK};
            }}
            QPushButton:pressed {{
                background-color: {self.SUCCESS_DARK};
            }}
            QPushButton:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
            QPushButton:focus {{
                border: 2px solid {self.SUCCESS_LIGHT};
                outline: none;
            }}
        """

    def button_icon(self, size: str = "36px"):
        """图标按钮样式 - 圆形/方形图标按钮

        Args:
            size: 按钮尺寸（宽高相等）
        """
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_MD};
                padding: 0;
                min-width: {size};
                max-width: {size};
                min-height: {size};
                max-height: {size};
                font-family: {ui_font};
            }}
            QPushButton:hover {{
                background-color: {self.PRIMARY_PALE};
                border-color: {self.PRIMARY};
                color: {self.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_TERTIARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
            }}
        """
