"""
编程项目创作模式选择对话框

允许用户在创建编程项目时选择创作模式：
- AI辅助需求分析：通过需求对话让AI帮你分析项目架构
- 空项目：跳过AI对话，直接手动填写所有内容
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from ..base import BaseDialog
from ..styles import DialogStyles


class CodingModeDialog(BaseDialog):
    """编程项目创作模式选择对话框

    使用方式：
        dialog = CodingModeDialog(parent=self)
        result = dialog.exec()

        if result == CodingModeDialog.MODE_AI:
            # 用户选择AI辅助需求分析
            pass
        elif result == CodingModeDialog.MODE_EMPTY:
            # 用户选择空项目
            pass
        else:
            # 用户取消
            pass
    """

    # 返回值常量
    MODE_AI = 1      # AI辅助需求分析
    MODE_EMPTY = 2   # 空项目

    def __init__(self, parent=None):
        # UI组件引用
        self.container = None
        self.title_label = None
        self.ai_card = None
        self.empty_card = None
        self.cancel_btn = None
        self._selected_mode = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("dialog_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(20))

        # 标题
        self.title_label = QLabel("选择创建模式")
        self.title_label.setObjectName("dialog_title")
        container_layout.addWidget(self.title_label)

        # 选项卡片区域
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(dp(12))

        # AI辅助需求分析卡片
        self.ai_card = self._create_mode_card(
            title="AI辅助需求分析",
            description="通过需求对话，让AI帮你分析项目架构、模块设计和功能规划",
            icon_text="AI",
            is_recommended=True
        )
        self.ai_card.mousePressEvent = lambda e: self._on_card_clicked(self.MODE_AI)
        cards_layout.addWidget(self.ai_card)

        # 空项目卡片
        self.empty_card = self._create_mode_card(
            title="空项目",
            description="跳过AI对话，直接手动填写架构设计、模块、功能大纲等所有内容",
            icon_text="NEW",
            is_recommended=False
        )
        self.empty_card.mousePressEvent = lambda e: self._on_card_clicked(self.MODE_EMPTY)
        cards_layout.addWidget(self.empty_card)

        container_layout.addLayout(cards_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(420))

    def _create_mode_card(
        self,
        title: str,
        description: str,
        icon_text: str,
        is_recommended: bool = False
    ) -> QFrame:
        """创建模式选择卡片"""
        card = QFrame()
        card.setObjectName("mode_card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("recommended", is_recommended)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        card_layout.setSpacing(dp(16))

        # 图标区域
        icon_container = QFrame()
        icon_container.setObjectName("icon_container")
        icon_container.setFixedSize(dp(48), dp(48))
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(icon_text)
        icon_label.setObjectName("card_icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        card_layout.addWidget(icon_container)

        # 文字区域
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(dp(4))

        # 标题行（含推荐标签）
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        title_row.addWidget(title_label)

        if is_recommended:
            recommend_label = QLabel("推荐")
            recommend_label.setObjectName("recommend_badge")
            title_row.addWidget(recommend_label)

        title_row.addStretch()
        text_layout.addLayout(title_row)

        # 描述
        desc_label = QLabel(description)
        desc_label.setObjectName("card_desc")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        card_layout.addWidget(text_container, stretch=1)

        return card

    def _on_card_clicked(self, mode: int):
        """卡片点击处理"""
        self._selected_mode = mode
        self.done(mode)

    def _apply_theme(self):
        """应用主题样式"""
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(DialogStyles.container("dialog_container"))

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #dialog_title {{
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                padding-bottom: {dp(4)}px;
            }}
        """)

        # 卡片样式
        card_style = f"""
            #mode_card {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
            }}
            #mode_card:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.PRIMARY};
            }}
            #mode_card[recommended="true"] {{
                border-color: {theme_manager.PRIMARY};
            }}
            #icon_container {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-radius: {dp(10)}px;
            }}
            #card_icon {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 700;
                color: {theme_manager.PRIMARY};
            }}
            #card_title {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #card_desc {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.4;
            }}
            #recommend_badge {{
                font-family: {ui_font};
                font-size: {sp(11)}px;
                font-weight: 600;
                color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY_PALE};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
            }}
        """
        self.ai_card.setStyleSheet(card_style)
        self.empty_card.setStyleSheet(card_style)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("cancel_btn"))
