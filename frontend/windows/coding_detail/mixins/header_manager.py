"""
Header管理Mixin

负责编程项目详情页Header的创建和样式管理。
增强版：64x64图标、项目统计、进度指示、更多操作按钮
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget,
    QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtSvgWidgets import QSvgWidget

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


class HeaderManagerMixin:
    """Header管理Mixin

    负责：
    - 创建Header布局（64x64图标、项目信息、统计、操作按钮）
    - 管理项目标题、类型、状态显示
    - 管理项目统计信息
    - 管理操作按钮
    """

    def createHeader(self: "CodingDetail"):
        """创建Header - 增强版"""
        self.header = QFrame()
        self.header.setObjectName("coding_detail_header")
        self.header.setFixedHeight(dp(110))

        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        layout.setSpacing(dp(16))

        # 左侧：项目图标（64x64）
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(dp(64), dp(64))
        self.icon_container.setObjectName("project_icon")
        self.icon_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_container.setToolTip("点击生成项目图标")
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG头像显示组件（预留）
        self.avatar_svg_widget = QSvgWidget()
        self.avatar_svg_widget.setFixedSize(dp(60), dp(60))
        self.avatar_svg_widget.setVisible(False)
        icon_layout.addWidget(self.avatar_svg_widget)

        # 默认占位符（显示C表示Coding）
        self.icon_placeholder = QLabel("C")
        self.icon_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_placeholder.setStyleSheet(f"""
            color: white;
            font-size: {sp(28)}px;
            font-weight: bold;
        """)
        icon_layout.addWidget(self.icon_placeholder)

        layout.addWidget(self.icon_container)

        # 中间：项目信息区域
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        self.project_title = QLabel("加载中...")
        self.project_title.setObjectName("project_title")
        self.project_title.setFont(QFont(theme_manager.ui_font(), sp(18), QFont.Weight.Bold))
        title_row.addWidget(self.project_title)

        title_row.addStretch()
        info_layout.addLayout(title_row)

        # 元信息行（类型 + 状态）
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

        # 统计信息行
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, dp(4), 0, 0)
        stats_layout.setSpacing(dp(16))

        # 统计标签
        self.systems_count_label = QLabel("0 系统")
        self.systems_count_label.setObjectName("stats_label")
        stats_layout.addWidget(self.systems_count_label)

        self.modules_count_label = QLabel("0 模块")
        self.modules_count_label.setObjectName("stats_label")
        stats_layout.addWidget(self.modules_count_label)

        self.features_count_label = QLabel("0 功能")
        self.features_count_label.setObjectName("stats_label")
        stats_layout.addWidget(self.features_count_label)

        self.files_count_label = QLabel("0 文件")
        self.files_count_label.setObjectName("stats_label")
        stats_layout.addWidget(self.files_count_label)

        stats_layout.addStretch()
        info_layout.addWidget(stats_widget)

        layout.addWidget(info_widget, stretch=1)

        # 右侧：操作按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(10))

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.onSaveAll)
        btn_layout.addWidget(self.save_btn)

        # 进入写作台按钮（主按钮）
        self.desk_btn = QPushButton("进入写作台")
        self.desk_btn.setObjectName("desk_btn")
        self.desk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.desk_btn.clicked.connect(self.openCodingDesk)
        btn_layout.addWidget(self.desk_btn)

        # 返回按钮
        self.back_btn = QPushButton("返回")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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

        ui_font = theme_manager.ui_font()
        text_primary = theme_manager.TEXT_PRIMARY
        text_secondary = theme_manager.TEXT_SECONDARY
        text_tertiary = theme_manager.TEXT_TERTIARY
        border_color = theme_manager.BORDER_DEFAULT
        accent_color = theme_manager.PRIMARY

        self.header.setStyleSheet(f"""
            QFrame#coding_detail_header {{
                background-color: {header_bg};
                border-bottom: 1px solid {border_color};
            }}
            QFrame#project_icon {{
                background-color: {accent_color};
                border-radius: {dp(8)}px;
            }}
            QLabel#project_title {{
                color: {text_primary};
                font-size: {sp(18)}px;
                font-weight: bold;
            }}
        """)

        # 图标占位符样式
        self.icon_placeholder.setStyleSheet(f"""
            color: white;
            font-size: {sp(28)}px;
            font-weight: bold;
            background: transparent;
        """)

        # 元信息标签样式
        tag_style = f"""
            QLabel {{
                color: {text_secondary};
                font-size: {sp(12)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {theme_manager.book_bg_secondary()};
                border-radius: {dp(4)}px;
            }}
        """
        self.type_tag.setStyleSheet(tag_style)
        self.status_tag.setStyleSheet(tag_style)

        # 统计标签样式
        stats_style = f"""
            QLabel#stats_label {{
                color: {text_tertiary};
                font-size: {sp(12)}px;
                font-family: {ui_font};
            }}
        """
        for label in [self.systems_count_label, self.modules_count_label,
                      self.features_count_label, self.files_count_label]:
            label.setStyleSheet(stats_style)

        # 普通按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: {theme_manager.book_bg_secondary()};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(14)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton:hover {{
                background-color: {accent_color}20;
                border-color: {accent_color};
            }}
            QPushButton:pressed {{
                background-color: {accent_color}40;
            }}
        """

        # 主按钮样式
        primary_btn_style = f"""
            QPushButton {{
                background-color: {accent_color};
                color: white;
                border: 1px solid {accent_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
                border-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
            }}
        """

        self.save_btn.setStyleSheet(btn_style)
        self.back_btn.setStyleSheet(btn_style)
        self.desk_btn.setStyleSheet(primary_btn_style)

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
                font-size: {sp(12)}px;
                padding: {dp(2)}px {dp(8)}px;
                background-color: {color}20;
                border-radius: {dp(4)}px;
            }}
        """)

    def updateProjectStats(self: "CodingDetail", systems: int = 0, modules: int = 0,
                           features: int = 0, files: int = 0):
        """更新项目统计信息

        Args:
            systems: 系统数量
            modules: 模块数量
            features: 功能数量
            files: 文件数量
        """
        if hasattr(self, 'systems_count_label'):
            self.systems_count_label.setText(f"{systems} 系统")
        if hasattr(self, 'modules_count_label'):
            self.modules_count_label.setText(f"{modules} 模块")
        if hasattr(self, 'features_count_label'):
            self.features_count_label.setText(f"{features} 功能")
        if hasattr(self, 'files_count_label'):
            self.files_count_label.setText(f"{files} 文件")


__all__ = ["HeaderManagerMixin"]
