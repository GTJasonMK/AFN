"""
Section 共享样式工具

提取 CharactersSection 和 RelationshipsSection 等组件的通用样式，
减少重复代码，确保样式一致性。
"""

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class SectionStyles:
    """Section 组件的共享样式生成器"""

    @staticmethod
    def list_section_stylesheet() -> str:
        """生成列表型 Section 的通用样式表

        适用于 CharactersSection, RelationshipsSection 等组件。
        包含：标题、数量标签、编辑按钮、空状态样式。

        Returns:
            Qt stylesheet 字符串
        """
        ui_font = theme_manager.ui_font()

        return f"""
            #section_title {{
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #count_label {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(4)}px {dp(12)}px;
                border-radius: {dp(12)}px;
            }}
            #edit_btn {{
                font-family: {ui_font};
                background: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #edit_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            #empty_state {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 2px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
                padding: {dp(40)}px;
            }}
            #empty_text {{
                font-family: {ui_font};
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #empty_hint {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_TERTIARY};
            }}
        """

    @staticmethod
    def scroll_area_stylesheet() -> str:
        """生成滚动区域的通用样式

        Returns:
            Qt stylesheet 字符串
        """
        return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """

    @staticmethod
    def transparent_background() -> str:
        """透明背景样式

        Returns:
            Qt stylesheet 字符串
        """
        return "background: transparent;"
