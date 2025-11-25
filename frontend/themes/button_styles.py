"""
统一按钮样式模块 - Claude晨曦风格

提供可复用的按钮样式，减少代码重复
支持多种尺寸和变体

设计规范：
- 尺寸：XS(24px) / SM(28px) / MD(36px) / LG(44px) / XL(52px)
- 变体：primary / secondary / glass / danger / success / warning / link / icon
- 状态：normal / hover / pressed / disabled
"""

from .theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ButtonSizes:
    """按钮尺寸常量"""

    # 高度
    HEIGHT_XS = dp(24)
    HEIGHT_SM = dp(28)
    HEIGHT_MD = dp(36)
    HEIGHT_LG = dp(44)
    HEIGHT_XL = dp(52)

    # 水平内边距
    PADDING_H_XS = dp(12)
    PADDING_H_SM = dp(16)
    PADDING_H_MD = dp(24)
    PADDING_H_LG = dp(32)
    PADDING_H_XL = dp(40)

    # 垂直内边距
    PADDING_V_XS = dp(4)
    PADDING_V_SM = dp(6)
    PADDING_V_MD = dp(10)
    PADDING_V_LG = dp(12)
    PADDING_V_XL = dp(14)

    # 字体大小
    FONT_XS = sp(11)
    FONT_SM = sp(12)
    FONT_MD = sp(14)
    FONT_LG = sp(16)
    FONT_XL = sp(18)

    # 图标按钮尺寸（正方形）
    ICON_XS = dp(24)
    ICON_SM = dp(32)
    ICON_MD = dp(40)
    ICON_LG = dp(48)
    ICON_XL = dp(56)

    @classmethod
    def get(cls, size: str = 'MD') -> dict:
        """获取指定尺寸的所有属性"""
        size = size.upper()
        return {
            'height': getattr(cls, f'HEIGHT_{size}', cls.HEIGHT_MD),
            'padding_h': getattr(cls, f'PADDING_H_{size}', cls.PADDING_H_MD),
            'padding_v': getattr(cls, f'PADDING_V_{size}', cls.PADDING_V_MD),
            'font': getattr(cls, f'FONT_{size}', cls.FONT_MD),
            'icon': getattr(cls, f'ICON_{size}', cls.ICON_MD),
        }


class ButtonStyles:
    """统一按钮样式类

    使用方式：
        button.setStyleSheet(ButtonStyles.primary())
        button.setStyleSheet(ButtonStyles.secondary('SM'))
        button.setStyleSheet(ButtonStyles.danger('LG'))

    支持尺寸：XS, SM, MD, LG, XL
    """

    @staticmethod
    def _get_size_props(size: str = 'MD') -> dict:
        """获取尺寸属性"""
        return ButtonSizes.get(size)

    @staticmethod
    def primary(size: str = 'MD') -> str:
        """主按钮样式 - 渐变背景（赭红色，Claude品牌色）"""
        from .modern_effects import ModernEffects

        props = ButtonStyles._get_size_props(size)
        gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)
        gradient_hover = ModernEffects.linear_gradient(
            [theme_manager.PRIMARY_LIGHT, theme_manager.PRIMARY], 135
        )

        return f"""
            QPushButton {{
                background: {gradient};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background: {gradient_hover};
            }}
            QPushButton:pressed {{
                background: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def secondary(size: str = 'MD') -> str:
        """次要按钮样式 - 浅色背景带边框"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                min-height: {props['height']}px;
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
    def glass(size: str = 'MD') -> str:
        """玻璃态按钮 - 半透明背景"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: {theme_manager.BG_CARD};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ACCENT_PALE};
                border-color: {theme_manager.ACCENT};
                color: {theme_manager.ACCENT};
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
    def danger(size: str = 'MD') -> str:
        """危险操作按钮 - 砖红色"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.ERROR_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def outline_danger(size: str = 'MD') -> str:
        """危险操作轮廓按钮 - 砖红色边框"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.ERROR};
                border: 1px solid {theme_manager.ERROR};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                min-height: {props['height']}px;
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
    def success(size: str = 'MD') -> str:
        """成功按钮 - 翠绿色"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: {theme_manager.SUCCESS};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.SUCCESS_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def outline_success(size: str = 'MD') -> str:
        """成功轮廓按钮 - 翠绿色边框"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.SUCCESS};
                border: 1px solid {theme_manager.SUCCESS};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.SUCCESS_DARK};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:disabled {{
                background-color: transparent;
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def warning(size: str = 'MD') -> str:
        """警告按钮 - 琥珀色"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: {theme_manager.WARNING};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.WARNING_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.WARNING_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def link(size: str = 'MD') -> str:
        """链接按钮 - 无背景，带下划线"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: none;
                padding: {dp(4)}px {dp(8)}px;
                font-size: {props['font']}px;
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
    def text(size: str = 'MD') -> str:
        """文本按钮 - 无背景无边框，纯文字"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def icon_only(size: str = 'MD') -> str:
        """图标按钮 - 正方形，无文字"""
        props = ButtonStyles._get_size_props(size)
        icon_size = props['icon']

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 0px;
                min-width: {icon_size}px;
                max-width: {icon_size}px;
                min-height: {icon_size}px;
                max-height: {icon_size}px;
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

    @staticmethod
    def icon_primary(size: str = 'MD') -> str:
        """主色图标按钮 - 正方形，主色背景"""
        from .modern_effects import ModernEffects

        props = ButtonStyles._get_size_props(size)
        icon_size = props['icon']
        gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)

        return f"""
            QPushButton {{
                background: {gradient};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: 0px;
                min-width: {icon_size}px;
                max-width: {icon_size}px;
                min-height: {icon_size}px;
                max-height: {icon_size}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def icon_circle(size: str = 'MD') -> str:
        """圆形图标按钮"""
        props = ButtonStyles._get_size_props(size)
        icon_size = props['icon']
        radius = icon_size // 2

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {radius}px;
                padding: 0px;
                min-width: {icon_size}px;
                max-width: {icon_size}px;
                min-height: {icon_size}px;
                max-height: {icon_size}px;
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
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def accent(size: str = 'MD') -> str:
        """强调按钮 - 鼠尾草绿渐变"""
        from .modern_effects import ModernEffects

        props = ButtonStyles._get_size_props(size)
        gradient = ModernEffects.linear_gradient(theme_manager.ACCENT_GRADIENT, 135)
        gradient_hover = ModernEffects.linear_gradient(
            [theme_manager.ACCENT_LIGHT, theme_manager.ACCENT], 135
        )

        return f"""
            QPushButton {{
                background: {gradient};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background: {gradient_hover};
            }}
            QPushButton:pressed {{
                background: {theme_manager.ACCENT_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def outline_primary(size: str = 'MD') -> str:
        """主色轮廓按钮 - 赭红色边框"""
        props = ButtonStyles._get_size_props(size)

        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {props['padding_v']}px {props['padding_h']}px;
                font-size: {props['font']}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                min-height: {props['height']}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton:disabled {{
                background-color: transparent;
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
        """
