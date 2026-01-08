"""
Header管理Mixin

负责编程项目详情页Header的创建和样式管理。
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


class HeaderManagerMixin:
    """Header管理Mixin

    负责：
    - 创建Header布局
    - 管理项目标题、类型、状态显示
    - 管理操作按钮
    """

    def createHeader(self: "CodingDetail"):
        """创建Header"""
        self.header = QFrame()
        self.header.setObjectName("coding_detail_header")
        self.header.setFixedHeight(dp(80))

        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        layout.setSpacing(dp(16))

        # 左侧：项目图标占位
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(dp(48), dp(48))
        self.icon_container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.PRIMARY};
                border-radius: {dp(8)}px;
            }}
        """)

        # 图标占位符（显示首字母）
        self.icon_placeholder = QLabel("P")
        self.icon_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_placeholder.setStyleSheet(f"""
            color: white;
            font-size: {dp(20)}px;
            font-weight: bold;
        """)
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(self.icon_placeholder)

        layout.addWidget(self.icon_container)

        # 中间：项目信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题
        self.project_title = QLabel("加载中...")
        self.project_title.setFont(QFont(theme_manager.ui_font(), dp(16), QFont.Weight.Bold))
        info_layout.addWidget(self.project_title)

        # 元信息行
        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(dp(8))

        # 类型标签
        self.type_tag = QLabel("项目类型")
        self.type_tag.setObjectName("type_tag")
        meta_layout.addWidget(self.type_tag)

        # 分隔符
        separator = QLabel("|")
        separator.setStyleSheet(f"color: {theme_manager.TEXT_TERTIARY}; background-color: transparent;")
        meta_layout.addWidget(separator)

        # 状态标签
        self.status_tag = QLabel("状态")
        self.status_tag.setObjectName("status_tag")
        meta_layout.addWidget(self.status_tag)

        meta_layout.addStretch()
        info_layout.addWidget(meta_widget)

        layout.addWidget(info_widget, stretch=1)

        # 右侧：操作按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(12))

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.clicked.connect(self.onSaveAll)
        btn_layout.addWidget(self.save_btn)

        # 开始生成按钮
        self.generate_btn = QPushButton("开始生成")
        self.generate_btn.setObjectName("generate_btn")
        self.generate_btn.clicked.connect(self.openCodingDesk)
        btn_layout.addWidget(self.generate_btn)

        # 返回按钮
        self.back_btn = QPushButton("返回")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.clicked.connect(self.goBackToWorkspace)
        btn_layout.addWidget(self.back_btn)

        layout.addWidget(btn_widget)

        self._applyHeaderStyle()

    def _applyHeaderStyle(self: "CodingDetail"):
        """应用Header样式"""
        from themes.modern_effects import ModernEffects

        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        header_opacity = theme_manager.get_component_opacity("header")

        if transparency_enabled:
            header_bg = ModernEffects.hex_to_rgba(
                theme_manager.book_bg_secondary(),
                header_opacity
            )
        else:
            header_bg = theme_manager.book_bg_secondary()

        self.header.setStyleSheet(f"""
            QFrame#coding_detail_header {{
                background-color: {header_bg};
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
        """)

        # 标题样式
        self.project_title.setStyleSheet(f"""
            color: {theme_manager.TEXT_PRIMARY};
            font-size: {dp(16)}px;
            font-weight: bold;
        """)

        # 元信息标签样式
        tag_style = f"""
            QLabel {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {theme_manager.book_bg_secondary()};
                border-radius: {dp(4)}px;
            }}
        """
        self.type_tag.setStyleSheet(tag_style)
        self.status_tag.setStyleSheet(tag_style)

        # 按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: {theme_manager.book_bg_secondary()};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}20;
                border-color: {theme_manager.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY}40;
            }}
        """
        self.save_btn.setStyleSheet(btn_style)
        self.back_btn.setStyleSheet(btn_style)

        # 主要按钮样式
        primary_btn_style = f"""
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """
        self.generate_btn.setStyleSheet(primary_btn_style)

    def _updateStatusTagStyle(self: "CodingDetail", status: str):
        """根据状态更新状态标签样式"""
        status_colors = {
            'draft': theme_manager.TEXT_SECONDARY,
            'blueprint_ready': theme_manager.INFO,
            'chapter_outlines_ready': theme_manager.INFO,
            'writing': theme_manager.WARNING,
            'completed': theme_manager.SUCCESS,
        }
        color = status_colors.get(status, theme_manager.TEXT_SECONDARY)

        self.status_tag.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {dp(12)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {color}20;
                border-radius: {dp(4)}px;
            }}
        """)


__all__ = ["HeaderManagerMixin"]
