"""
Tab管理Mixin

负责编程项目详情页Tab导航的创建和管理。
重构版：精简为4个Tab（概览、架构设计、目录结构、生成管理）
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


# 编程项目Tab配置 - 精简为4个
CODING_TABS = [
    {'id': 'overview', 'label': '概览'},
    {'id': 'architecture', 'label': '架构设计'},
    {'id': 'directory', 'label': '目录结构'},
    {'id': 'generation', 'label': '生成管理'},
]


class TabManagerMixin:
    """Tab管理Mixin

    负责：
    - 创建Tab导航栏
    - 管理Tab切换
    - 应用Tab样式
    """

    def createTabBar(self: "CodingDetail"):
        """创建Tab导航栏"""
        self.tab_bar = QFrame()
        self.tab_bar.setObjectName("coding_detail_tab_bar")
        self.tab_bar.setFixedHeight(dp(48))

        layout = QHBoxLayout(self.tab_bar)
        layout.setContentsMargins(dp(24), 0, dp(24), 0)
        layout.setSpacing(dp(4))

        self._tab_buttons = {}

        for tab in CODING_TABS:
            btn = QPushButton(tab['label'])
            btn.setObjectName(f"tab_btn_{tab['id']}")
            btn.setCheckable(True)
            btn.setProperty("tab_id", tab['id'])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, sid=tab['id']: self.switchSection(sid))

            self._tab_buttons[tab['id']] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # 设置默认选中
        if self._tab_buttons:
            first_btn = self._tab_buttons.get('overview')
            if first_btn:
                first_btn.setChecked(True)

        self._applyTabStyle()

    def switchSection(self: "CodingDetail", section_id: str):
        """切换Section"""
        if self.active_section == section_id:
            return

        logger.info(f"switchSection: {self.active_section} -> {section_id}")

        # 更新Tab按钮状态
        for tab_id, btn in self._tab_buttons.items():
            btn.setChecked(tab_id == section_id)

        self.active_section = section_id
        self.loadSection(section_id)

    def _applyTabStyle(self: "CodingDetail"):
        """应用Tab样式"""
        from themes.modern_effects import ModernEffects

        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        tab_opacity = theme_manager.get_component_opacity("tab")

        if transparency_enabled:
            tab_bg = ModernEffects.hex_to_rgba(
                theme_manager.book_bg_primary(),
                tab_opacity
            )
        else:
            tab_bg = theme_manager.book_bg_primary()

        self.tab_bar.setStyleSheet(f"""
            QFrame#coding_detail_tab_bar {{
                background-color: {tab_bg};
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
        """)

        # Tab按钮样式
        for btn in self._tab_buttons.values():
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: {dp(12)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {theme_manager.TEXT_PRIMARY};
                    background-color: {theme_manager.PRIMARY}10;
                }}
                QPushButton:checked {{
                    color: {theme_manager.PRIMARY};
                    border-bottom: 2px solid {theme_manager.PRIMARY};
                    font-weight: bold;
                }}
            """)


__all__ = ["TabManagerMixin"]
