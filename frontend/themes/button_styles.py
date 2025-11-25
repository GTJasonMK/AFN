"""
统一按钮样式模块

提供可复用的按钮样式，减少代码重复
"""

from .theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ButtonStyles:
    """统一按钮样式类"""

    @staticmethod
    def primary(font_size='MD'):
        """主按钮样式 - 渐变背景"""
        from .modern_effects import ModernEffects

        gradient_style = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)

        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background: {ModernEffects.linear_gradient([theme_manager.PRIMARY_LIGHT, theme_manager.PRIMARY], 135)};
            }}
            QPushButton:pressed {{
                background: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def secondary(font_size='MD'):
        """次要按钮样式 - 浅色背景"""
        return f"""
            QPushButton {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(8)}px {dp(20)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def glass(font_size='MD'):
        """玻璃态按钮 - 浅色背景"""
        return f"""
            QPushButton {{
                background-color: {theme_manager.BG_CARD};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ACCENT_PALE};
                border-color: {theme_manager.ACCENT_PRIMARY};
                color: {theme_manager.ACCENT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QPushButton:disabled {{
                background-color: transparent;
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def danger(font_size='MD'):
        """危险操作按钮 - 红色"""
        return f"""
            QPushButton {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.ERROR_DARK};
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def outline_danger(font_size='MD'):
        """危险操作轮廓按钮 - 红色边框"""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.ERROR};
                border: 1px solid {theme_manager.ERROR};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.ERROR_DARK};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:disabled {{
                background-color: transparent;
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def success(font_size='MD'):
        """成功按钮 - 绿色"""
        return f"""
            QPushButton {{
                background-color: {theme_manager.SUCCESS};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS_DARK if hasattr(theme_manager, 'SUCCESS_DARK') else theme_manager.SUCCESS};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def link(font_size='MD'):
        """链接按钮 - 无背景"""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: none;
                padding: {dp(4)}px {dp(8)}px;
                font-size: {sp(14) if font_size == 'MD' else sp(16) if font_size == 'LG' else sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {theme_manager.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def icon_only(size='MD'):
        """图标按钮 - 正方形"""
        button_size = dp(40) if size == 'MD' else dp(48) if size == 'LG' else dp(32)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 0px;
                min-width: {button_size}px;
                max-width: {button_size}px;
                min-height: {button_size}px;
                max-height: {button_size}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """
