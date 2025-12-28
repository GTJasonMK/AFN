"""
Tab导航管理Mixin

负责Tab导航栏的创建和样式管理。
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

if TYPE_CHECKING:
    from ..main import NovelDetail


class TabManagerMixin:
    """
    Tab导航管理Mixin

    负责：
    - 创建Tab导航栏
    - 应用Tab样式
    - 更新Tab按钮样式
    - 处理Tab切换
    """

    def createTabBar(self: "NovelDetail"):
        """创建Tab导航栏"""
        self.tab_bar = QFrame()
        self.tab_bar.setObjectName("tab_bar")
        self.tab_bar.setFixedHeight(dp(48))

        tab_layout = QHBoxLayout(self.tab_bar)
        tab_layout.setContentsMargins(dp(24), 0, dp(24), 0)
        tab_layout.setSpacing(dp(24))

        # Tab定义
        tabs = [
            ('overview', '概览'),
            ('world_setting', '世界观'),
            ('characters', '角色'),
            ('relationships', '关系'),
            ('chapter_outline', '章节大纲'),
            ('chapters', '已生成章节')
        ]

        self.tab_buttons = {}
        for tab_id, tab_name in tabs:
            btn = QPushButton(tab_name)
            btn.setObjectName(f"tab_{tab_id}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(dp(48))
            btn.clicked.connect(lambda checked, tid=tab_id: self.switchSection(tid))
            tab_layout.addWidget(btn)
            self.tab_buttons[tab_id] = btn

        tab_layout.addStretch()

        # 应用Tab样式
        self._applyTabStyle()

    def _applyTabStyle(self: "NovelDetail"):
        """应用Tab样式 - 书香风格 + 透明效果支持"""
        from themes.modern_effects import ModernEffects

        tab_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        system_blur_enabled = transparency_config.get("system_blur", False)

        if transparency_enabled:
            opacity = transparency_config.get("header_opacity", 0.90)
            tab_bg_style = ModernEffects.hex_to_rgba(tab_bg, opacity)
            border_style = ModernEffects.hex_to_rgba(border_color, 0.5)
            # 只有系统级模糊启用时才设置WA_TranslucentBackground
            if system_blur_enabled:
                self.tab_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            tab_bg_style = tab_bg
            border_style = border_color

        self.tab_bar.setStyleSheet(f"""
            QFrame#tab_bar {{
                background-color: {tab_bg_style};
                border-bottom: 1px solid {border_style};
            }}
        """)

        # 更新所有Tab按钮样式
        for tab_id, btn in self.tab_buttons.items():
            self._updateTabButtonStyle(btn, tab_id == self.active_section)

    def _updateTabButtonStyle(self: "NovelDetail", btn, is_active):
        """更新Tab按钮样式"""
        ui_font = theme_manager.ui_font()

        text_active = theme_manager.book_accent_color()
        text_normal = theme_manager.book_text_secondary()
        hover_color = theme_manager.book_text_primary()
        border_active = theme_manager.book_accent_color()

        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_active};
                    border: none;
                    border-bottom: 2px solid {border_active};
                    border-radius: 0;
                    padding: 0 {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_normal};
                    border: none;
                    border-bottom: 2px solid transparent;
                    border-radius: 0;
                    padding: 0 {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: normal;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                }}
            """)

    def switchSection(self: "NovelDetail", section_id):
        """切换到指定Section

        性能优化：只更新变化的两个Tab按钮样式，而非全部更新
        """
        old_section = self.active_section
        self.active_section = section_id

        # 增量更新：只更新变化的两个Tab（旧Tab取消激活，新Tab激活）
        if old_section != section_id:
            if old_section in self.tab_buttons:
                self._updateTabButtonStyle(self.tab_buttons[old_section], False)
            if section_id in self.tab_buttons:
                self._updateTabButtonStyle(self.tab_buttons[section_id], True)

        # 加载Section内容
        self.loadSection(section_id)


__all__ = [
    "TabManagerMixin",
]
