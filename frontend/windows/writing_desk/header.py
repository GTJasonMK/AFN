"""
写作台顶部导航栏 - 现代化设计

功能：返回按钮、项目信息、导出、查看详情
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QWidget, QMenu, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.formatters import count_chinese_characters, format_word_count


class WDHeader(TransparencyAwareMixin, ThemeAwareFrame):
    """写作台顶部导航栏 - 现代化设计

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符
    _transparency_component_id = "header"

    goBackClicked = pyqtSignal()
    viewDetailClicked = pyqtSignal()
    exportClicked = pyqtSignal(str)  # format: txt/markdown
    toggleAssistantClicked = pyqtSignal(bool)  # true=show, false=hide

    def __init__(self, project=None, parent=None):
        self.project = project

        # 保存组件引用
        self.container = None
        self.back_btn = None
        self.title_label = None
        self.meta_label = None
        self.stats_container = None
        self.export_btn = None
        self.detail_btn = None
        self.assistant_btn = None

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）- 现代化设计"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(dp(16), 0, dp(16), 0)
        main_layout.setSpacing(dp(12))

        self.setFixedHeight(dp(72))  # 增加高度确保内容完整显示

        # 玻璃拟态容器
        self.container = QFrame()
        self.container.setObjectName("header_container")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        container_layout.setSpacing(dp(12))

        # 左侧：返回按钮
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(dp(36), dp(36))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBackClicked.emit)
        container_layout.addWidget(self.back_btn)

        # 项目信息卡片 - 核心区域，优先展示
        info_card = QFrame()
        info_card.setObjectName("info_card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(dp(12), dp(6), dp(12), dp(6))
        info_layout.setSpacing(dp(2))

        self.title_label = QLabel("加载中...")
        self.title_label.setObjectName("title_label")
        self.title_label.setMinimumWidth(dp(150))
        # 防止文字被截断
        self.title_label.setWordWrap(False)
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(self.title_label)

        # 元信息（包含统计信息）
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("meta_label")
        info_layout.addWidget(self.meta_label)

        container_layout.addWidget(info_card, stretch=1)

        # 右侧：操作按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(dp(8))

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.showExportMenu)
        buttons_layout.addWidget(self.export_btn)

        # 项目详情按钮
        self.detail_btn = QPushButton("项目详情")
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(self.viewDetailClicked.emit)
        buttons_layout.addWidget(self.detail_btn)
        
        # RAG助手按钮
        self.assistant_btn = QPushButton("RAG助手")
        self.assistant_btn.setCheckable(True)
        self.assistant_btn.setChecked(False)
        self.assistant_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.assistant_btn.toggled.connect(self.toggleAssistantClicked.emit)
        self.assistant_btn.toggled.connect(self._update_assistant_btn_style)
        buttons_layout.addWidget(self.assistant_btn)

        container_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.container)

        # 保存stats_container引用（兼容旧代码，但不再使用）
        self.stats_container = None

        # 如果已有项目数据，设置
        if self.project:
            self.setProject(self.project)
            
    def _update_assistant_btn_style(self):
        """更新助手按钮样式"""
        if self.assistant_btn:
            style = ButtonStyles.primary('SM') if self.assistant_btn.isChecked() else ButtonStyles.secondary('SM')
            self.assistant_btn.setStyleSheet(style)

    def _apply_theme(self):
        """应用主题样式（可多次调用）- 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # Header背景 - 支持透明效果
        if self._transparency_enabled:
            # 使用Mixin提供的透明背景样式
            bg_style = self._get_transparent_bg(
                theme_manager.BG_SECONDARY,
                border_color=theme_manager.BORDER_LIGHT,
                border_opacity=OpacityTokens.BORDER_LIGHT
            )

            # 直接设置样式，不使用Python类名选择器
            self.setStyleSheet(f"""
                {bg_style}
                border-bottom: 1px solid {self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_LIGHT)};
            """)

            # 容器使用稍低透明度
            container_opacity = self._current_opacity * 0.7
            if self.container:
                container_rgba = self._hex_to_rgba(theme_manager.BG_TERTIARY, container_opacity)
                border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_LIGHT)
                self.container.setStyleSheet(f"""
                    QFrame#header_container {{
                        background-color: {container_rgba};
                        border: 1px solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_LG};
                    }}
                """)
                self._make_widget_transparent(self.container)

            # 项目信息卡片也使用半透明背景
            if info_card := self.findChild(QFrame, "info_card"):
                info_card_rgba = self._hex_to_rgba(theme_manager.BG_TERTIARY, container_opacity * 0.7)
                border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_LIGHT)
                info_card.setStyleSheet(f"""
                    QFrame#info_card {{
                        background-color: {info_card_rgba};
                        border: 1px solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)
                self._make_widget_transparent(info_card)
        else:
            # 非透明模式 - 使用正常背景色
            # 直接设置样式，不使用Python类名选择器
            self.setStyleSheet(f"""
                background-color: {theme_manager.BG_SECONDARY};
                border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
            """)

            # 玻璃拟态容器（非透明模式）
            if self.container:
                glassmorphism_style = ModernEffects.glassmorphism_card(
                    is_dark=theme_manager.is_dark_mode()
                )
                self.container.setStyleSheet(f"""
                    QFrame#header_container {{
                        {glassmorphism_style}
                        border-radius: {theme_manager.RADIUS_LG};
                    }}
                """)

            # 项目信息卡片（非透明模式）
            if info_card := self.findChild(QFrame, "info_card"):
                info_card.setStyleSheet(f"""
                    QFrame#info_card {{
                        background-color: {theme_manager.BG_TERTIARY};
                        border: 1px solid {theme_manager.BORDER_LIGHT};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)

        # 添加阴影（两种模式都需要）
        if self.container:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(dp(12))
            shadow.setColor(QColor(0, 0, 0, 25))
            shadow.setOffset(0, dp(2))
            self.container.setGraphicsEffect(shadow)

        # 返回按钮 - 圆形渐变按钮
        if self.back_btn:
            gradient = ModernEffects.linear_gradient(
                theme_manager.PRIMARY_GRADIENT,
                135
            )
            self.back_btn.setStyleSheet(f"""
                QPushButton {{
                    min-width: {dp(36)}px;
                    min-height: {dp(36)}px;
                    background: {gradient};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(18)}px;
                    font-family: {ui_font};
                    font-size: {sp(16)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 180)};
                }}
                QPushButton:pressed {{
                    padding-top: 1px;
                }}
            """)

        # 标题
        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        # 元信息
        if self.meta_label:
            self.meta_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        # 导出按钮
        if self.export_btn:
            self.export_btn.setStyleSheet(ButtonStyles.secondary('SM'))

        # 详情按钮
        if self.detail_btn:
            self.detail_btn.setStyleSheet(ButtonStyles.primary('SM'))

        # RAG助手按钮
        if self.assistant_btn:
            # 未选中是secondary，选中是primary
            style = ButtonStyles.primary('SM') if self.assistant_btn.isChecked() else ButtonStyles.secondary('SM')
            self.assistant_btn.setStyleSheet(style)

    def setProject(self, project):
        """设置项目数据 - 统计信息合并到元信息行"""
        self.project = project
        if not project or not self.title_label or not self.meta_label:
            return

        # 更新标题
        title = project.get('title', '未命名项目')
        self.title_label.setText(title)

        # 计算统计数据
        blueprint = project.get('blueprint', {})
        genre = blueprint.get('genre', '')
        chapters = project.get('chapters', [])
        completed_chapters = [ch for ch in chapters if ch.get('content')]

        # 判断是否为空白项目（无蓝图数据）
        is_empty_project = not blueprint or not blueprint.get('one_sentence_summary')

        # 总章节数：空白项目使用实际章节数，普通项目使用大纲章节数
        if is_empty_project:
            total_chapters = len(chapters)
        else:
            total_chapters = len(blueprint.get('chapter_outline', []))

        # 总字数
        total_words = sum(
            count_chinese_characters(ch.get('content', ''))
            for ch in completed_chapters
        )

        # 构建元信息文本（包含统计）
        meta_parts = []
        if genre:
            meta_parts.append(genre)
        elif is_empty_project:
            meta_parts.append("自由创作")
        meta_parts.append(f"{len(completed_chapters)}/{total_chapters}章")
        if total_words > 0:
            meta_parts.append(format_word_count(total_words))

        self.meta_label.setText(" · ".join(meta_parts))

    def showExportMenu(self):
        """显示导出格式菜单"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: {theme_manager.ACCENT_PALE};
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        txt_action = menu.addAction("导出为 TXT")
        txt_action.triggered.connect(lambda: self.exportClicked.emit('txt'))

        md_action = menu.addAction("导出为 Markdown")
        md_action.triggered.connect(lambda: self.exportClicked.emit('markdown'))

        # 显示菜单在按钮下方
        if self.export_btn:
            menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))
