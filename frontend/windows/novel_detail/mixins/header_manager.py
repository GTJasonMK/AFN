"""
Header管理Mixin

负责Header的创建、样式应用和状态更新。
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtSvgWidgets import QSvgWidget

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

if TYPE_CHECKING:
    from ..main import NovelDetail


class HeaderManagerMixin:
    """
    Header管理Mixin

    负责：
    - 创建顶部Header（项目信息 + 操作按钮）
    - 应用Header样式
    - 更新保存按钮样式
    - 更新状态标签样式
    """

    def createHeader(self: "NovelDetail"):
        """创建顶部Header - 书香风格"""
        self.header = QFrame()
        self.header.setObjectName("detail_header")
        self.header.setFixedHeight(dp(100))

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        header_layout.setSpacing(dp(16))

        # 左侧：项目图标 + 信息
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(dp(16))

        # 项目图标（支持SVG头像或默认占位符）
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(dp(64), dp(64))
        self.icon_container.setObjectName("project_icon")
        self.icon_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_container.setToolTip("点击生成小说头像")
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG头像显示组件
        self.avatar_svg_widget = QSvgWidget()
        self.avatar_svg_widget.setFixedSize(dp(60), dp(60))
        self.avatar_svg_widget.setVisible(False)
        icon_layout.addWidget(self.avatar_svg_widget)

        # 默认占位符（字母B）
        self.icon_placeholder = QLabel("B")
        self.icon_placeholder.setStyleSheet(f"font-size: {sp(28)}px; font-weight: bold;")
        self.icon_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_placeholder)

        # 为icon_container添加点击事件
        self.icon_container.mousePressEvent = self._onIconClicked

        left_layout.addWidget(self.icon_container)

        # 项目信息
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        self.project_title = QLabel("加载中...")
        self.project_title.setObjectName("project_title")
        title_row.addWidget(self.project_title)

        # 编辑标题按钮
        edit_title_btn = QPushButton("编辑")
        edit_title_btn.setObjectName("edit_title_btn")
        edit_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_title_btn.setFixedHeight(dp(32))
        edit_title_btn.clicked.connect(self.editProjectTitle)
        title_row.addWidget(edit_title_btn)
        title_row.addStretch()

        info_layout.addLayout(title_row)

        # 元信息行（类型 + 状态标签）
        meta_row = QHBoxLayout()
        meta_row.setSpacing(dp(8))

        self.genre_tag = QLabel("")
        self.genre_tag.setObjectName("genre_tag")
        meta_row.addWidget(self.genre_tag)

        self.status_tag = QLabel("")
        self.status_tag.setObjectName("status_tag")
        meta_row.addWidget(self.status_tag)

        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        left_layout.addWidget(info_container, stretch=1)

        header_layout.addWidget(left_container, stretch=1)

        # 右侧：操作按钮
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(12))

        # 保存按钮（初始禁用）
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.onSaveAll)
        btn_layout.addWidget(self.save_btn)

        # 返回按钮 - 返回写作台
        self.back_btn = QPushButton("返回写作台")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.openWritingDesk)
        btn_layout.addWidget(self.back_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(lambda: self.exportNovel('txt'))
        btn_layout.addWidget(self.export_btn)

        # RAG同步按钮
        self.rag_sync_btn = QPushButton("RAG同步")
        self.rag_sync_btn.setObjectName("rag_sync_btn")
        self.rag_sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rag_sync_btn.setToolTip("检查并同步RAG向量数据库，确保章节生成时能检索到最新内容")
        self.rag_sync_btn.clicked.connect(self.onSyncRAG)
        btn_layout.addWidget(self.rag_sync_btn)

        # 优化蓝图按钮
        self.refine_btn = QPushButton("优化蓝图")
        self.refine_btn.setObjectName("refine_btn")
        self.refine_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refine_btn.clicked.connect(self.onRefineBlueprint)
        btn_layout.addWidget(self.refine_btn)

        # 开始分析按钮（仅导入项目显示）
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.onStartAnalysis)
        self.analyze_btn.setVisible(False)
        btn_layout.addWidget(self.analyze_btn)

        # 开始创作按钮（主按钮）
        self.create_btn = QPushButton("开始创作")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.clicked.connect(self.openWritingDesk)
        btn_layout.addWidget(self.create_btn)

        header_layout.addWidget(btn_container)

        # 应用Header样式
        self._applyHeaderStyle()

    def _applyHeaderStyle(self: "NovelDetail"):
        """应用Header样式 - 书香风格 + 透明效果支持"""
        from themes.modern_effects import ModernEffects

        header_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        icon_color = theme_manager.book_accent_color()
        tag_bg = "transparent"

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        system_blur_enabled = transparency_config.get("system_blur", False)

        # 根据透明效果配置决定背景颜色
        if transparency_enabled:
            # 使用get_component_opacity获取透明度，自动应用主控透明度系数
            opacity = theme_manager.get_component_opacity("header")
            header_bg_style = ModernEffects.hex_to_rgba(header_bg, opacity)
            border_style = ModernEffects.hex_to_rgba(border_color, 0.5)
            # 只有系统级模糊启用时才设置WA_TranslucentBackground
            if system_blur_enabled:
                self.header.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            header_bg_style = header_bg
            border_style = border_color

        # 设置header容器和子组件样式
        self.header.setStyleSheet(f"""
            QFrame#detail_header {{
                background-color: {header_bg_style};
                border-bottom: 1px solid {border_style};
            }}
            QFrame#project_icon {{
                background: transparent;
                border: 2px solid {icon_color};
                border-radius: {dp(4)}px;
            }}
            QLabel#project_title {{
                font-family: {serif_font};
                font-size: {sp(28)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            }}
            QPushButton#edit_title_btn {{
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                text-decoration: underline;
            }}
            QPushButton#edit_title_btn:hover {{
                color: {icon_color};
            }}
            QLabel#genre_tag {{
                background-color: {tag_bg};
                color: {text_secondary};
                border: 1px solid {border_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(2)}px;
                font-family: {ui_font};
                font-size: {sp(12)}px;
            }}
            QLabel#status_tag {{
                background-color: {tag_bg};
                color: {text_secondary};
                border: 1px solid {border_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(2)}px;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-style: italic;
            }}
        """)

        # 操作按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                color: {icon_color};
                border-color: {icon_color};
                background-color: rgba(0,0,0,0.05);
            }}
        """

        primary_btn_style = f"""
            QPushButton {{
                background-color: {icon_color};
                color: {theme_manager.BUTTON_TEXT};
                border: 1px solid {icon_color};
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                padding: {dp(6)}px {dp(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
                border-color: {text_primary};
            }}
        """

        if hasattr(self, 'back_btn') and self.back_btn:
            self.back_btn.setStyleSheet(btn_style)
        if hasattr(self, 'export_btn') and self.export_btn:
            self.export_btn.setStyleSheet(btn_style)
        if hasattr(self, 'refine_btn') and self.refine_btn:
            self.refine_btn.setStyleSheet(btn_style)
        if hasattr(self, 'rag_sync_btn') and self.rag_sync_btn:
            self.rag_sync_btn.setStyleSheet(btn_style)
        if hasattr(self, 'analyze_btn') and self.analyze_btn:
            # 分析按钮使用高亮样式
            self.analyze_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.INFO};
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid {theme_manager.INFO};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)
        if hasattr(self, 'create_btn') and self.create_btn:
            self.create_btn.setStyleSheet(primary_btn_style)

        # 保存按钮样式（特殊处理，有修改时高亮）
        if hasattr(self, 'save_btn') and self.save_btn:
            self._updateSaveButtonStyle()

    def _updateSaveButtonStyle(self: "NovelDetail"):
        """更新保存按钮样式和状态"""
        if not hasattr(self, 'save_btn') or not self.save_btn:
            return

        ui_font = theme_manager.ui_font()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        is_dirty = self.dirty_tracker.is_dirty()
        self.save_btn.setEnabled(is_dirty)

        if is_dirty:
            # 有修改时，高亮显示
            self.save_btn.setText("保存*")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent_color};
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid {accent_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)
        else:
            # 无修改时，普通样式
            self.save_btn.setText("保存")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    color: {accent_color};
                    border-color: {accent_color};
                    background-color: rgba(0,0,0,0.05);
                }}
                QPushButton:disabled {{
                    color: {border_color};
                    border-color: {border_color};
                    background-color: transparent;
                }}
            """)

    def _updateStatusTagStyle(self: "NovelDetail", status):
        """根据状态更新状态标签样式"""
        if status == 'completed':
            bg_color = theme_manager.SUCCESS_BG
            text_color = theme_manager.SUCCESS
        elif status == 'writing':
            bg_color = theme_manager.INFO_BG
            text_color = theme_manager.INFO
        elif status in ['blueprint_ready', 'chapter_outlines_ready', 'part_outlines_ready']:
            bg_color = theme_manager.WARNING_BG
            text_color = theme_manager.WARNING
        else:
            bg_color = theme_manager.BG_TERTIARY
            text_color = theme_manager.TEXT_SECONDARY

        self.status_tag.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: {dp(4)}px {dp(12)}px;
            border-radius: {dp(4)}px;
            font-size: {sp(12)}px;
            font-weight: 500;
        """)


__all__ = [
    "HeaderManagerMixin",
]
