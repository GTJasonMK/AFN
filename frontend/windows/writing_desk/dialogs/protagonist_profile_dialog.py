"""
主角档案查看对话框

显示主角的三类属性（显性、隐性、社会）和行为记录。
支持创建档案和章节同步功能。
采用现代卡片式设计。
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect,
    QMessageBox, QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QFont, QPainter, QBrush, QPen

from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class AttributeCard(ThemeAwareWidget):
    """属性卡片组件 - 现代卡片设计"""

    clicked = pyqtSignal(str, str, object)

    def __init__(self, category: str, key: str, value: Any, parent=None):
        self.category = category
        self.key = key
        self.value = value
        self.key_label = None
        self.value_label = None
        self.evidence_btn = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(6))

        # 顶部：属性名和溯源按钮
        top_row = QHBoxLayout()
        top_row.setSpacing(dp(8))

        self.key_label = QLabel(self.key)
        self.key_label.setObjectName("attr_key")
        top_row.addWidget(self.key_label)

        top_row.addStretch()

        self.evidence_btn = QPushButton("溯源")
        self.evidence_btn.setObjectName("evidence_btn")
        self.evidence_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.evidence_btn.clicked.connect(self._on_evidence_clicked)
        top_row.addWidget(self.evidence_btn)

        layout.addLayout(top_row)

        # 底部：属性值
        value_text = self._format_value(self.value)
        self.value_label = QLabel(value_text)
        self.value_label.setObjectName("attr_value")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)

    def _on_evidence_clicked(self):
        self.clicked.emit(self.category, self.key, self.value)

    def _format_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value) if value else "-"

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()
        is_light = theme_manager.is_light_mode()

        # 卡片背景和边框
        if is_light:
            card_bg = "#FFFFFF"
            card_border = "#E8E0D5"
            key_color = "#8D6E63"
            value_color = "#3E2723"
            btn_color = "#A1887F"
            btn_hover_bg = "#EFEBE9"
        else:
            card_bg = "#3D3530"
            card_border = "#4A423C"
            key_color = "#BCAAA4"
            value_color = "#EFEBE9"
            btn_color = "#A1887F"
            btn_hover_bg = "#4A423C"

        accent = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {dp(10)}px;
        """)

        if self.key_label:
            self.key_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {key_color};
                letter-spacing: 0.5px;
            """)

        if self.value_label:
            self.value_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {value_color};
                line-height: 1.4;
            """)

        if self.evidence_btn:
            self.evidence_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {btn_color};
                    padding: {dp(4)}px {dp(10)}px;
                    border-radius: {dp(4)}px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover_bg};
                    color: {accent};
                }}
            """)


class AttributeCategoryPanel(ThemeAwareWidget):
    """属性类别面板 - 现代设计"""

    attributeClicked = pyqtSignal(str, str, object)

    def __init__(self, category: str, title: str, icon: str, description: str, attributes: Dict[str, Any], parent=None):
        self.category = category
        self.title = title
        self.icon = icon
        self.description = description
        self.attributes = attributes or {}
        self.title_label = None
        self.desc_label = None
        self.cards_container = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(16))

        # 标题区域
        header = QVBoxLayout()
        header.setSpacing(dp(4))

        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(10))

        icon_label = QLabel(self.icon)
        icon_label.setObjectName("category_icon")
        title_row.addWidget(icon_label)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("category_title")
        title_row.addWidget(self.title_label)

        count_badge = QLabel(str(len(self.attributes)))
        count_badge.setObjectName("count_badge")
        count_badge.setFixedSize(dp(24), dp(24))
        count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(count_badge)

        title_row.addStretch()
        header.addLayout(title_row)

        # 描述
        self.desc_label = QLabel(self.description)
        self.desc_label.setObjectName("category_desc")
        header.addWidget(self.desc_label)

        layout.addLayout(header)

        # 属性卡片网格
        self.cards_container = QWidget()
        cards_layout = QVBoxLayout(self.cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(dp(10))

        if self.attributes:
            for key, value in self.attributes.items():
                card = AttributeCard(self.category, key, value)
                card.clicked.connect(self._on_card_clicked)
                cards_layout.addWidget(card)
        else:
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setContentsMargins(dp(20), dp(40), dp(20), dp(40))

            empty_icon = QLabel("( )")
            empty_icon.setObjectName("empty_icon")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_icon)

            empty_label = QLabel("暂无属性记录")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_label)

            cards_layout.addWidget(empty_widget)

        layout.addWidget(self.cards_container)
        layout.addStretch()

    def _on_card_clicked(self, category: str, key: str, value: Any):
        self.attributeClicked.emit(category, key, value)

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()
        is_light = theme_manager.is_light_mode()
        accent = theme_manager.book_accent_color()

        if is_light:
            title_color = "#4E342E"
            desc_color = "#8D6E63"
            badge_bg = accent
            badge_color = "#FFFFFF"
            empty_color = "#BCAAA4"
        else:
            title_color = "#EFEBE9"
            desc_color = "#A1887F"
            badge_bg = accent
            badge_color = "#FFFFFF"
            empty_color = "#6D5D54"

        if icon_label := self.findChild(QLabel, "category_icon"):
            icon_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-size: {sp(22)}px;
                color: {accent};
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {title_color};
            """)

        if count_badge := self.findChild(QLabel, "count_badge"):
            count_badge.setStyleSheet(f"""
                background-color: {badge_bg};
                border: none;
                border-radius: {dp(12)}px;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {badge_color};
            """)

        if self.desc_label:
            self.desc_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {desc_color};
            """)

        if empty_icon := self.findChild(QLabel, "empty_icon"):
            empty_icon.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-size: {sp(32)}px;
                color: {empty_color};
            """)

        if empty_label := self.findChild(QLabel, "empty_label"):
            empty_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {empty_color};
            """)


class CategoryTabButton(QPushButton):
    """分类标签按钮"""

    def __init__(self, text: str, icon: str, parent=None):
        super().__init__(parent)
        self.icon_text = icon
        self.label_text = text
        self._selected = False
        self.setText(f"{icon}  {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)

    def setSelected(self, selected: bool):
        self._selected = selected
        self.setChecked(selected)


class ProtagonistProfileDialog(QDialog):
    """主角档案查看对话框 - 现代设计"""

    profileUpdated = pyqtSignal()

    def __init__(
        self,
        project_id: str,
        protagonist_name: str = None,
        blueprint_characters: List[Dict] = None,
        total_chapters: int = 0,
        parent=None
    ):
        super().__init__(parent)
        self.project_id = project_id
        self.protagonist_name = protagonist_name
        self.blueprint_characters = blueprint_characters or []
        self.total_chapters = total_chapters
        self.api_client = APIClientManager.get_client()
        self._portrait_worker = None
        self._sync_worker = None

        self.profile_data = None
        self.has_profile = False

        # UI组件
        self.portrait_label = None
        self.name_label = None
        self.sync_status_label = None
        self.stacked_widget = None
        self.tab_buttons = []
        self.create_btn = None
        self.sync_btn = None
        self.chapter_spin = None
        self.sync_widget = None

        self.setWindowTitle("主角档案")
        self.setMinimumSize(dp(600), dp(700))
        self.setModal(True)

        self._setup_ui()
        self._apply_theme()
        self._load_profile()

        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        self._apply_theme()
        self._update_tab_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部区域（带背景）
        header_container = QFrame()
        header_container.setObjectName("header_container")
        header_container.setFixedHeight(dp(160))
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(dp(24), dp(24), dp(24), dp(20))
        header_layout.setSpacing(dp(12))

        # 头部内容
        header_content = QHBoxLayout()
        header_content.setSpacing(dp(20))

        # 立绘/头像
        self.portrait_label = QLabel()
        self.portrait_label.setObjectName("portrait_label")
        self.portrait_label.setFixedSize(dp(80), dp(80))
        self.portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_label.setText("?")
        header_content.addWidget(self.portrait_label)

        # 信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(dp(6))

        self.name_label = QLabel("加载中...")
        self.name_label.setObjectName("profile_name")
        info_layout.addWidget(self.name_label)

        self.sync_status_label = QLabel("同步状态: -")
        self.sync_status_label.setObjectName("sync_status")
        info_layout.addWidget(self.sync_status_label)

        info_layout.addStretch()
        header_content.addLayout(info_layout, stretch=1)

        header_layout.addLayout(header_content)

        # 操作按钮区
        action_layout = QHBoxLayout()
        action_layout.setSpacing(dp(12))

        # 创建按钮
        self.create_btn = QPushButton("+ 创建档案")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.clicked.connect(self._on_create_profile)
        self.create_btn.setVisible(False)
        action_layout.addWidget(self.create_btn)

        # 同步区域
        self.sync_widget = QWidget()
        sync_layout = QHBoxLayout(self.sync_widget)
        sync_layout.setContentsMargins(0, 0, 0, 0)
        sync_layout.setSpacing(dp(8))

        sync_label = QLabel("同步章节")
        sync_label.setObjectName("sync_label")
        sync_layout.addWidget(sync_label)

        self.chapter_spin = QSpinBox()
        self.chapter_spin.setObjectName("chapter_spin")
        self.chapter_spin.setMinimum(1)
        self.chapter_spin.setMaximum(max(1, self.total_chapters))
        self.chapter_spin.setValue(1)
        self.chapter_spin.setFixedWidth(dp(70))
        sync_layout.addWidget(self.chapter_spin)

        self.sync_btn = QPushButton("同步")
        self.sync_btn.setObjectName("sync_btn")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(self._on_sync_chapter)
        sync_layout.addWidget(self.sync_btn)

        self.sync_widget.setVisible(False)
        action_layout.addWidget(self.sync_widget)

        action_layout.addStretch()
        header_layout.addLayout(action_layout)

        layout.addWidget(header_container)

        # 内容区域
        content_container = QFrame()
        content_container.setObjectName("content_container")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(dp(24), dp(20), dp(24), dp(24))
        content_layout.setSpacing(dp(16))

        # 分类标签栏
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(dp(8))

        self.tab_buttons = []
        tab_data = [
            ("显性属性", "外"),
            ("隐性属性", "内"),
            ("社会属性", "社"),
        ]
        for i, (text, icon) in enumerate(tab_data):
            btn = CategoryTabButton(text, icon)
            btn.setObjectName(f"tab_btn_{i}")
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_clicked(idx))
            tabs_layout.addWidget(btn)
            self.tab_buttons.append(btn)

        tabs_layout.addStretch()
        content_layout.addLayout(tabs_layout)

        # 内容切换区
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stacked_content")
        content_layout.addWidget(self.stacked_widget, stretch=1)

        layout.addWidget(content_container, stretch=1)

        # 底部按钮
        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        footer_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("close_btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        layout.addWidget(footer)

    def _on_tab_clicked(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setSelected(i == index)
        self._update_tab_styles()

    def _update_tab_styles(self):
        ui_font = theme_manager.ui_font()
        is_light = theme_manager.is_light_mode()
        accent = theme_manager.book_accent_color()

        if is_light:
            normal_bg = "#F5F0EB"
            normal_color = "#6D5D54"
            selected_bg = accent
            selected_color = "#FFFFFF"
        else:
            normal_bg = "#3D3530"
            normal_color = "#A1887F"
            selected_bg = accent
            selected_color = "#FFFFFF"

        for btn in self.tab_buttons:
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {selected_bg};
                        border: none;
                        border-radius: {dp(8)}px;
                        font-family: {ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {selected_color};
                        padding: {dp(10)}px {dp(16)}px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {normal_bg};
                        border: none;
                        border-radius: {dp(8)}px;
                        font-family: {ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 500;
                        color: {normal_color};
                        padding: {dp(10)}px {dp(16)}px;
                    }}
                    QPushButton:hover {{
                        background-color: {accent}30;
                        color: {accent};
                    }}
                """)

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()
        is_light = theme_manager.is_light_mode()
        accent = theme_manager.book_accent_color()

        if is_light:
            dialog_bg = "#FAF8F5"
            header_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8D6E63, stop:1 #6D4C41)"
            header_text = "#FFFFFF"
            header_secondary = "rgba(255,255,255,0.8)"
            content_bg = "#FAF8F5"
            footer_bg = "#F5F0EB"
            portrait_bg = "rgba(255,255,255,0.2)"
            portrait_border = "rgba(255,255,255,0.4)"
            portrait_text = "#FFFFFF"
        else:
            dialog_bg = "#2D2520"
            header_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4E342E, stop:1 #3E2723)"
            header_text = "#EFEBE9"
            header_secondary = "rgba(239,235,233,0.7)"
            content_bg = "#2D2520"
            footer_bg = "#3D3530"
            portrait_bg = "rgba(0,0,0,0.2)"
            portrait_border = "rgba(255,255,255,0.2)"
            portrait_text = "#EFEBE9"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dialog_bg};
            }}
        """)

        # 头部
        if header := self.findChild(QFrame, "header_container"):
            header.setStyleSheet(f"""
                QFrame#header_container {{
                    background: {header_bg};
                    border: none;
                }}
            """)

        # 立绘
        if self.portrait_label:
            self.portrait_label.setStyleSheet(f"""
                QLabel#portrait_label {{
                    background-color: {portrait_bg};
                    border: 2px solid {portrait_border};
                    border-radius: {dp(40)}px;
                    font-family: {ui_font};
                    font-size: {sp(28)}px;
                    font-weight: 700;
                    color: {portrait_text};
                }}
            """)

        # 名称
        if self.name_label:
            self.name_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(22)}px;
                font-weight: 700;
                color: {header_text};
            """)

        # 同步状态
        if self.sync_status_label:
            self.sync_status_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {header_secondary};
            """)

        # 创建按钮
        if self.create_btn:
            self.create_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255,255,255,0.2);
                    border: 1px solid rgba(255,255,255,0.4);
                    border-radius: {dp(8)}px;
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    font-weight: 600;
                    color: {header_text};
                    padding: {dp(8)}px {dp(16)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255,255,255,0.3);
                }}
            """)

        # 同步区域 - 确保容器透明
        if self.sync_widget:
            self.sync_widget.setStyleSheet("background: transparent;")

        if sync_label := self.findChild(QLabel, "sync_label"):
            sync_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {header_secondary};
            """)

        if self.chapter_spin:
            self.chapter_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: rgba(255,255,255,0.15);
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: {dp(6)}px;
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {header_text};
                    padding: {dp(4)}px {dp(8)}px;
                    padding-right: {dp(20)}px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background: transparent;
                    border: none;
                    width: {dp(16)}px;
                }}
                QSpinBox::up-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-bottom: 5px solid {header_secondary};
                    width: 0; height: 0;
                }}
                QSpinBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {header_secondary};
                    width: 0; height: 0;
                }}
            """)

        if self.sync_btn:
            self.sync_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255,255,255,0.2);
                    border: 1px solid rgba(255,255,255,0.4);
                    border-radius: {dp(6)}px;
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    font-weight: 600;
                    color: {header_text};
                    padding: {dp(6)}px {dp(14)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255,255,255,0.3);
                }}
                QPushButton:disabled {{
                    background-color: rgba(255,255,255,0.1);
                    color: rgba(255,255,255,0.5);
                }}
            """)

        # 内容区
        if content := self.findChild(QFrame, "content_container"):
            content.setStyleSheet(f"""
                QFrame#content_container {{
                    background-color: {content_bg};
                    border: none;
                }}
            """)

        # 底部
        if footer := self.findChild(QFrame, "footer"):
            footer.setStyleSheet(f"""
                QFrame#footer {{
                    background-color: {footer_bg};
                    border-top: 1px solid {theme_manager.book_border_color()};
                }}
            """)

        if close_btn := self.findChild(QPushButton, "close_btn"):
            close_btn.setStyleSheet(ButtonStyles.secondary('MD'))

        self._update_tab_styles()

    def _load_profile(self):
        try:
            profiles = self.api_client.get_protagonist_profiles(self.project_id)

            if not profiles:
                self.has_profile = False
                self.name_label.setText("暂无主角档案")
                self.sync_status_label.setText("请先创建档案")
                self._add_empty_panels()
                self._update_action_buttons()
                return

            self.has_profile = True

            target_profile = None
            for profile in profiles:
                if self.protagonist_name and profile.get('character_name') == self.protagonist_name:
                    target_profile = profile
                    break

            if not target_profile:
                target_profile = profiles[0]

            character_name = target_profile.get('character_name')
            full_profile = self.api_client.get_protagonist_profile(
                self.project_id,
                character_name
            )

            self.profile_data = full_profile
            self._update_ui()
            self._update_action_buttons()

        except Exception as e:
            logger.error(f"加载主角档案失败: {e}")
            self.has_profile = False
            self.name_label.setText("加载失败")
            self._add_empty_panels()
            self._update_action_buttons()

    def _update_action_buttons(self):
        if self.has_profile:
            if self.create_btn:
                self.create_btn.setVisible(False)
            if self.sync_widget:
                self.sync_widget.setVisible(True)
            if self.chapter_spin and self.profile_data:
                last_synced = self.profile_data.get('last_synced_chapter', 0)
                next_chapter = min(last_synced + 1, self.total_chapters) if last_synced > 0 else 1
                self.chapter_spin.setValue(next_chapter)
        else:
            if self.create_btn:
                self.create_btn.setVisible(True)
            if self.sync_widget:
                self.sync_widget.setVisible(False)

    def _on_create_profile(self):
        from .protagonist_create_dialog import ProtagonistCreateDialog
        dialog = ProtagonistCreateDialog(
            project_id=self.project_id,
            blueprint_characters=self.blueprint_characters,
            parent=self
        )
        dialog.profileCreated.connect(self._on_profile_created)
        dialog.exec()

    def _on_profile_created(self, profile_data: dict):
        logger.info(f"档案创建成功: {profile_data.get('character_name')}")
        self._load_profile()
        self.profileUpdated.emit()

    def _on_sync_chapter(self):
        if not self.profile_data:
            return

        chapter_number = self.chapter_spin.value() if self.chapter_spin else 1
        character_name = self.profile_data.get('character_name')

        if not character_name:
            return

        if self.sync_btn:
            self.sync_btn.setEnabled(False)
            self.sync_btn.setText("...")

        def do_sync():
            return self.api_client.sync_protagonist_from_chapter(
                project_id=self.project_id,
                character_name=character_name,
                chapter_number=chapter_number
            )

        def on_success(result):
            changes = result.get('changes_applied', 0)
            behaviors = result.get('behaviors_recorded', 0)
            QMessageBox.information(
                self, "同步完成",
                f"第 {chapter_number} 章同步完成\n属性变更: {changes}\n行为记录: {behaviors}"
            )
            self._load_profile()
            self.profileUpdated.emit()
            if self.sync_btn:
                self.sync_btn.setEnabled(True)
                self.sync_btn.setText("同步")

        def on_error(error):
            logger.error(f"同步失败: {error}")
            QMessageBox.critical(self, "同步失败", f"同步失败:\n{error}")
            if self.sync_btn:
                self.sync_btn.setEnabled(True)
                self.sync_btn.setText("同步")

        self._sync_worker = AsyncWorker(do_sync)
        self._sync_worker.success.connect(on_success)
        self._sync_worker.error.connect(on_error)
        self._sync_worker.start()

    def _update_ui(self):
        if not self.profile_data:
            return

        name = self.profile_data.get('character_name', '未知')
        self.name_label.setText(name)

        # 更新头像文字
        if self.portrait_label and not self.portrait_label.pixmap():
            first_char = name[0] if name else "?"
            self.portrait_label.setText(first_char)

        sync_chapter = self.profile_data.get('last_synced_chapter', 0)
        if sync_chapter > 0:
            self.sync_status_label.setText(f"已同步至第 {sync_chapter} 章")
        else:
            self.sync_status_label.setText("尚未同步章节")

        self._load_portrait(name)

        # 清空并重建面板
        while self.stacked_widget.count():
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        explicit_attrs = self.profile_data.get('explicit_attributes', {})
        implicit_attrs = self.profile_data.get('implicit_attributes', {})
        social_attrs = self.profile_data.get('social_attributes', {})

        # 创建三个面板
        panels_data = [
            ("explicit", "显性属性", "外", "外在可见的特征：外貌、装备、技能等", explicit_attrs),
            ("implicit", "隐性属性", "内", "内在性格特质：性格、价值观、习惯等", implicit_attrs),
            ("social", "社会属性", "社", "社会关系和地位：身份、人际关系等", social_attrs),
        ]

        for category, title, icon, desc, attrs in panels_data:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet(theme_manager.scrollbar())

            panel = AttributeCategoryPanel(category, title, icon, desc, attrs)
            panel.attributeClicked.connect(self._on_attribute_clicked)
            scroll.setWidget(panel)
            self.stacked_widget.addWidget(scroll)

        # 更新标签按钮显示数量
        counts = [len(explicit_attrs), len(implicit_attrs), len(social_attrs)]
        tab_names = ["显性属性", "隐性属性", "社会属性"]
        tab_icons = ["外", "内", "社"]
        for i, btn in enumerate(self.tab_buttons):
            btn.setText(f"{tab_icons[i]}  {tab_names[i]} ({counts[i]})")

        # 默认选中第一个
        if self.tab_buttons:
            self.tab_buttons[0].setSelected(True)
            self._update_tab_styles()

    def _add_empty_panels(self):
        while self.stacked_widget.count():
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        panels_data = [
            ("explicit", "显性属性", "外", "外在可见的特征：外貌、装备、技能等", {}),
            ("implicit", "隐性属性", "内", "内在性格特质：性格、价值观、习惯等", {}),
            ("social", "社会属性", "社", "社会关系和地位：身份、人际关系等", {}),
        ]

        for category, title, icon, desc, attrs in panels_data:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet(theme_manager.scrollbar())

            panel = AttributeCategoryPanel(category, title, icon, desc, attrs)
            scroll.setWidget(panel)
            self.stacked_widget.addWidget(scroll)

        # 更新标签按钮
        tab_names = ["显性属性", "隐性属性", "社会属性"]
        tab_icons = ["外", "内", "社"]
        for i, btn in enumerate(self.tab_buttons):
            btn.setText(f"{tab_icons[i]}  {tab_names[i]} (0)")

        if self.tab_buttons:
            self.tab_buttons[0].setSelected(True)
            self._update_tab_styles()

    def _on_attribute_clicked(self, category: str, key: str, value: Any):
        if not self.profile_data:
            return

        character_name = self.profile_data.get('character_name')
        if not character_name:
            return

        from .attribute_evidence_dialog import AttributeEvidenceDialog
        dialog = AttributeEvidenceDialog(
            project_id=self.project_id,
            character_name=character_name,
            category=category,
            attribute_key=key,
            current_value=value,
            parent=self
        )
        dialog.exec()

    def _load_portrait(self, character_name: str):
        try:
            result = self.api_client.get_character_portraits(self.project_id, character_name)
            portraits = result.get('portraits', [])

            for portrait in portraits:
                if portrait.get('is_active'):
                    image_path = portrait.get('image_path')
                    if image_path:
                        image_url = self.api_client.get_portrait_image_url(image_path)
                        self._display_portrait(image_url)
                        return

            if portraits:
                image_path = portraits[0].get('image_path')
                if image_path:
                    image_url = self.api_client.get_portrait_image_url(image_path)
                    self._display_portrait(image_url)

        except Exception as e:
            logger.warning(f"加载角色立绘失败: {e}")

    def _display_portrait(self, image_url: str):
        def do_fetch():
            import requests
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                return response.content
            return None

        def on_success(image_data):
            if image_data:
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        dp(80), dp(80),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # 裁剪为圆形
                    size = dp(80)
                    rounded = QPixmap(size, size)
                    rounded.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(rounded)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setBrush(QBrush(scaled))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(0, 0, size, size)
                    painter.end()

                    self.portrait_label.setPixmap(rounded)
                    self.portrait_label.setText("")
                    self.portrait_label.setStyleSheet(f"""
                        QLabel#portrait_label {{
                            background-color: transparent;
                            border: 2px solid rgba(255,255,255,0.4);
                            border-radius: {dp(40)}px;
                        }}
                    """)

        def on_error(error):
            logger.warning(f"显示立绘失败: {error}")

        self._portrait_worker = AsyncWorker(do_fetch)
        self._portrait_worker.success.connect(on_success)
        self._portrait_worker.error.connect(on_error)
        self._portrait_worker.start()

    def __del__(self):
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
