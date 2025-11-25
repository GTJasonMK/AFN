"""
组件样式模块 - Claude晨曦风格

提供常用UI组件的预设样式，减少重复代码
支持主题切换

组件类型：
- 卡片（Card）
- 输入框（Input）
- 标签（Label）
- 标签页（Tab）
- 滚动条（Scrollbar）
- 徽章（Badge）
- 分隔线（Divider）
"""

from .theme_manager import theme_manager
from .modern_effects import ModernEffects
from utils.dpi_utils import dp, sp


class CardStyles:
    """卡片样式"""

    @staticmethod
    def default() -> str:
        """默认卡片样式"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_MD};
            }}
        """

    @staticmethod
    def elevated() -> str:
        """浮起卡片样式（更大圆角）"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_LG};
            }}
        """

    @staticmethod
    def glass() -> str:
        """玻璃态卡片"""
        glass_bg = ModernEffects.glassmorphism_card(theme_manager.is_dark_mode())
        return f"""
            QFrame {{
                {glass_bg}
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_LG};
            }}
        """

    @staticmethod
    def interactive() -> str:
        """可交互卡片（带hover效果）"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_MD};
            }}
            QFrame:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
                border-color: {theme_manager.PRIMARY};
            }}
        """

    @staticmethod
    def outlined() -> str:
        """轮廓卡片（无背景）"""
        return f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_MD};
            }}
        """

    @staticmethod
    def section() -> str:
        """区块卡片（用于页面分区）"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BG_SECONDARY};
                border: none;
                border-radius: {theme_manager.RADIUS_LG};
                padding: {dp(20)}px;
            }}
        """


class InputStyles:
    """输入框样式"""

    @staticmethod
    def default() -> str:
        """默认输入框样式"""
        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {theme_manager.BG_CARD};
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(10)}px {dp(12)}px;
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                selection-background-color: {theme_manager.PRIMARY_PALE};
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_CARD};
            }}
            QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
                border-color: {theme_manager.PRIMARY_LIGHT};
            }}
            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
                border-color: {theme_manager.BORDER_LIGHT};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: {theme_manager.TEXT_PLACEHOLDER};
            }}
        """

    @staticmethod
    def search() -> str:
        """搜索框样式（带圆角）"""
        return f"""
            QLineEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(18)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_CARD};
            }}
            QLineEdit::placeholder {{
                color: {theme_manager.TEXT_PLACEHOLDER};
            }}
        """

    @staticmethod
    def minimal() -> str:
        """极简输入框（无边框）"""
        return f"""
            QLineEdit, QTextEdit {{
                background-color: transparent;
                border: none;
                border-bottom: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: 0px;
                padding: {dp(8)}px {dp(4)}px;
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-bottom-color: {theme_manager.PRIMARY};
            }}
        """

    @staticmethod
    def textarea() -> str:
        """多行文本框样式"""
        return f"""
            QTextEdit, QPlainTextEdit {{
                background-color: {theme_manager.BG_CARD};
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_MD};
                padding: {dp(12)}px {dp(14)}px;
                font-size: {sp(14)}px;
                line-height: 1.6;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
        """


class LabelStyles:
    """标签样式"""

    @staticmethod
    def title() -> str:
        """大标题样式"""
        return f"""
            QLabel {{
                font-size: {sp(24)}px;
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
                background: transparent;
            }}
        """

    @staticmethod
    def subtitle() -> str:
        """副标题样式"""
        return f"""
            QLabel {{
                font-size: {sp(18)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                color: {theme_manager.TEXT_PRIMARY};
                background: transparent;
            }}
        """

    @staticmethod
    def heading() -> str:
        """小标题样式"""
        return f"""
            QLabel {{
                font-size: {sp(16)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                color: {theme_manager.TEXT_PRIMARY};
                background: transparent;
            }}
        """

    @staticmethod
    def body() -> str:
        """正文样式"""
        return f"""
            QLabel {{
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
                color: {theme_manager.TEXT_PRIMARY};
                background: transparent;
            }}
        """

    @staticmethod
    def caption() -> str:
        """说明文字样式"""
        return f"""
            QLabel {{
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
                color: {theme_manager.TEXT_SECONDARY};
                background: transparent;
            }}
        """

    @staticmethod
    def muted() -> str:
        """弱化文字样式"""
        return f"""
            QLabel {{
                font-size: {sp(13)}px;
                font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
                color: {theme_manager.TEXT_TERTIARY};
                background: transparent;
            }}
        """

    @staticmethod
    def link() -> str:
        """链接样式"""
        return f"""
            QLabel {{
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {theme_manager.PRIMARY};
                background: transparent;
            }}
            QLabel:hover {{
                color: {theme_manager.PRIMARY_LIGHT};
                text-decoration: underline;
            }}
        """


class BadgeStyles:
    """徽章/标签样式"""

    @staticmethod
    def default() -> str:
        """默认徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_SECONDARY};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
        """

    @staticmethod
    def primary() -> str:
        """主色徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
        """

    @staticmethod
    def success() -> str:
        """成功徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.SUCCESS};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
        """

    @staticmethod
    def warning() -> str:
        """警告徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.WARNING};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
        """

    @staticmethod
    def error() -> str:
        """错误徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
        """

    @staticmethod
    def info() -> str:
        """信息徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.INFO};
                color: {theme_manager.BUTTON_TEXT};
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            }}
        """

    @staticmethod
    def outline() -> str:
        """轮廓徽章"""
        return f"""
            QLabel {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                padding: {dp(3)}px {dp(9)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
        """

    @staticmethod
    def pill() -> str:
        """药丸形徽章"""
        return f"""
            QLabel {{
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
                padding: {dp(4)}px {dp(12)}px;
                border-radius: {dp(12)}px;
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
        """


class TabStyles:
    """标签页样式"""

    @staticmethod
    def default() -> str:
        """默认标签页样式"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
                background-color: {theme_manager.BG_CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                padding: {dp(10)}px {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: {dp(4)}px;
            }}
            QTabBar::tab:selected {{
                color: {theme_manager.PRIMARY};
                border-bottom: 2px solid {theme_manager.PRIMARY};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
            QTabBar::tab:hover:!selected {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_SECONDARY};
            }}
        """

    @staticmethod
    def pills() -> str:
        """药丸形标签页"""
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                border-radius: {dp(16)}px;
                margin-right: {dp(8)}px;
            }}
            QTabBar::tab:selected {{
                color: {theme_manager.BUTTON_TEXT};
                background-color: {theme_manager.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_TERTIARY};
            }}
        """

    @staticmethod
    def segment() -> str:
        """分段控制器样式"""
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {theme_manager.RADIUS_SM};
                padding: {dp(2)}px;
            }}
            QTabBar::tab {{
                padding: {dp(8)}px {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                border-radius: {dp(6)}px;
            }}
            QTabBar::tab:selected {{
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_CARD};
            }}
        """


class ScrollbarStyles:
    """滚动条样式"""

    @staticmethod
    def default() -> str:
        """默认滚动条（细线）"""
        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(8)}px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: transparent;
                height: {dp(8)}px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                min-width: {dp(30)}px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    @staticmethod
    def thin() -> str:
        """超细滚动条"""
        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(4)}px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme_manager.BORDER_DARK};
                border-radius: {dp(2)}px;
                min-height: {dp(20)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: transparent;
                height: {dp(4)}px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {theme_manager.BORDER_DARK};
                border-radius: {dp(2)}px;
                min-width: {dp(20)}px;
            }}
        """

    @staticmethod
    def hidden() -> str:
        """隐藏滚动条（但保留滚动功能）"""
        return """
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px;
                height: 0px;
            }
        """


class DividerStyles:
    """分隔线样式"""

    @staticmethod
    def horizontal() -> str:
        """水平分隔线"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BORDER_LIGHT};
                border: none;
                max-height: 1px;
                min-height: 1px;
            }}
        """

    @staticmethod
    def vertical() -> str:
        """垂直分隔线"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BORDER_LIGHT};
                border: none;
                max-width: 1px;
                min-width: 1px;
            }}
        """

    @staticmethod
    def thick() -> str:
        """粗分隔线"""
        return f"""
            QFrame {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border: none;
                max-height: 2px;
                min-height: 2px;
            }}
        """


class ProgressStyles:
    """进度条样式"""

    @staticmethod
    def default() -> str:
        """默认进度条"""
        return f"""
            QProgressBar {{
                background-color: {theme_manager.BG_TERTIARY};
                border: none;
                border-radius: {dp(4)}px;
                height: {dp(8)}px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
            }}
        """

    @staticmethod
    def success() -> str:
        """成功进度条"""
        return f"""
            QProgressBar {{
                background-color: {theme_manager.BG_TERTIARY};
                border: none;
                border-radius: {dp(4)}px;
                height: {dp(8)}px;
            }}
            QProgressBar::chunk {{
                background-color: {theme_manager.SUCCESS};
                border-radius: {dp(4)}px;
            }}
        """

    @staticmethod
    def thin() -> str:
        """细进度条"""
        return f"""
            QProgressBar {{
                background-color: {theme_manager.BG_TERTIARY};
                border: none;
                border-radius: {dp(2)}px;
                height: {dp(4)}px;
            }}
            QProgressBar::chunk {{
                background-color: {theme_manager.PRIMARY};
                border-radius: {dp(2)}px;
            }}
        """


class ComponentStyles:
    """组件样式统一入口

    使用方式：
        label.setStyleSheet(ComponentStyles.label.title())
        card.setStyleSheet(ComponentStyles.card.glass())
        input.setStyleSheet(ComponentStyles.input.default())
    """

    card = CardStyles
    input = InputStyles
    label = LabelStyles
    badge = BadgeStyles
    tab = TabStyles
    scrollbar = ScrollbarStyles
    divider = DividerStyles
    progress = ProgressStyles
