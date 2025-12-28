"""
主角档案查看对话框

显示主角的三类属性（显性、隐性、社会）和行为记录。
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QTabWidget, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap

from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class AttributeCard(ThemeAwareWidget):
    """属性卡片组件"""

    def __init__(self, key: str, value: Any, parent=None):
        self.key = key
        self.value = value
        self.key_label = None
        self.value_label = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        layout.setSpacing(dp(8))

        self.key_label = QLabel(self.key)
        self.key_label.setObjectName("attr_key")
        layout.addWidget(self.key_label)

        layout.addStretch()

        # 值可能是各种类型，转换为字符串显示
        value_text = self._format_value(self.value)
        self.value_label = QLabel(value_text)
        self.value_label.setObjectName("attr_value")
        self.value_label.setWordWrap(True)
        self.value_label.setMaximumWidth(dp(200))
        layout.addWidget(self.value_label)

    def _format_value(self, value: Any) -> str:
        """格式化值为字符串"""
        if isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value)

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()

        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        self.setStyleSheet(f"""
            background-color: {theme_manager.BG_CARD};
            border: 1px solid {theme_manager.BORDER_LIGHT};
            border-radius: {theme_manager.RADIUS_SM};
        """)

        if self.key_label:
            self.key_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {theme_manager.TEXT_SECONDARY};
            """)

        if self.value_label:
            self.value_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_PRIMARY};
            """)


class AttributeCategoryPanel(ThemeAwareWidget):
    """属性类别面板"""

    def __init__(self, title: str, icon: str, attributes: Dict[str, Any], parent=None):
        self.title = title
        self.icon = icon
        self.attributes = attributes or {}
        self.title_label = None
        self.cards_container = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon_label = QLabel(self.icon)
        icon_label.setObjectName("category_icon")
        header.addWidget(icon_label)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("category_title")
        header.addWidget(self.title_label)

        count_label = QLabel(f"({len(self.attributes)})")
        count_label.setObjectName("category_count")
        header.addWidget(count_label)

        header.addStretch()
        layout.addLayout(header)

        # 属性卡片容器
        self.cards_container = QWidget()
        cards_layout = QVBoxLayout(self.cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(dp(8))

        if self.attributes:
            for key, value in self.attributes.items():
                card = AttributeCard(key, value)
                cards_layout.addWidget(card)
        else:
            empty_label = QLabel("暂无属性")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cards_layout.addWidget(empty_label)

        layout.addWidget(self.cards_container)

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()

        if icon_label := self.findChild(QLabel, "category_icon"):
            icon_label.setStyleSheet(f"""
                font-size: {sp(20)}px;
                color: {theme_manager.PRIMARY};
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if count_label := self.findChild(QLabel, "category_count"):
            count_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_TERTIARY};
            """)

        if empty_label := self.findChild(QLabel, "empty_label"):
            empty_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_TERTIARY};
                padding: {dp(20)}px;
            """)


class ProtagonistProfileDialog(QDialog):
    """主角档案查看对话框"""

    def __init__(self, project_id: str, protagonist_name: str = None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.protagonist_name = protagonist_name
        self.api_client = APIClientManager.get_client()
        self._portrait_worker = None  # 异步加载立绘的worker

        self.profile_data = None
        self.portrait_label = None
        self.name_label = None
        self.tab_widget = None

        self.setWindowTitle("主角档案")
        self.setMinimumSize(dp(500), dp(600))
        self.setModal(True)

        self._setup_ui()
        self._apply_theme()
        self._load_profile()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 头部：立绘和基本信息
        header = QFrame()
        header.setObjectName("profile_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        header_layout.setSpacing(dp(16))

        # 立绘
        self.portrait_label = QLabel()
        self.portrait_label.setObjectName("portrait_label")
        self.portrait_label.setFixedSize(dp(100), dp(100))
        self.portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_label.setText("👤")
        header_layout.addWidget(self.portrait_label)

        # 基本信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(8))

        self.name_label = QLabel("加载中...")
        self.name_label.setObjectName("profile_name")
        info_layout.addWidget(self.name_label)

        self.sync_label = QLabel("同步章节: -")
        self.sync_label.setObjectName("sync_label")
        info_layout.addWidget(self.sync_label)

        info_layout.addStretch()
        header_layout.addWidget(info_widget, stretch=1)

        layout.addWidget(header)

        # 属性选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("profile_tabs")
        layout.addWidget(self.tab_widget, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        if header := self.findChild(QFrame, "profile_header"):
            header.setStyleSheet(f"""
                QFrame#profile_header {{
                    background-color: {theme_manager.BG_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_LG};
                }}
            """)

        if self.portrait_label:
            self.portrait_label.setStyleSheet(f"""
                QLabel#portrait_label {{
                    background-color: {theme_manager.BG_TERTIARY};
                    border: 2px dashed {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                    font-size: {sp(40)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                }}
            """)

        if self.name_label:
            self.name_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if self.sync_label:
            self.sync_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_SECONDARY};
            """)

        if self.tab_widget:
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                    background-color: {theme_manager.BG_SECONDARY};
                }}
                QTabBar::tab {{
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    padding: {dp(8)}px {dp(16)}px;
                    background-color: {theme_manager.BG_TERTIARY};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-bottom: none;
                    border-top-left-radius: {theme_manager.RADIUS_SM};
                    border-top-right-radius: {theme_manager.RADIUS_SM};
                    color: {theme_manager.TEXT_SECONDARY};
                }}
                QTabBar::tab:selected {{
                    background-color: {theme_manager.BG_SECONDARY};
                    color: {theme_manager.PRIMARY};
                    font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                }}
                QTabBar::tab:hover {{
                    background-color: {theme_manager.PRIMARY_PALE};
                }}
            """)

        if close_btn := self.findChild(QPushButton, "close_btn"):
            close_btn.setStyleSheet(ButtonStyles.secondary('MD'))

    def _load_profile(self):
        """加载主角档案"""
        try:
            # 获取项目下的主角档案列表
            profiles = self.api_client.get_protagonist_profiles(self.project_id)

            if not profiles:
                self.name_label.setText("暂无主角档案")
                self._add_empty_tabs()
                return

            # 找到指定的主角或使用第一个
            target_profile = None
            for profile in profiles:
                if self.protagonist_name and profile.get('character_name') == self.protagonist_name:
                    target_profile = profile
                    break

            if not target_profile:
                target_profile = profiles[0]

            # 获取完整档案
            character_name = target_profile.get('character_name')
            full_profile = self.api_client.get_protagonist_profile(
                self.project_id,
                character_name
            )

            self.profile_data = full_profile
            self._update_ui()

        except Exception as e:
            logger.error(f"加载主角档案失败: {e}")
            self.name_label.setText("加载失败")
            self._add_empty_tabs()

    def _update_ui(self):
        """根据档案数据更新UI"""
        if not self.profile_data:
            return

        # 更新名称
        name = self.profile_data.get('character_name', '未知')
        self.name_label.setText(name)

        # 更新同步章节
        sync_chapter = self.profile_data.get('last_synced_chapter', 0)
        self.sync_label.setText(f"同步至第 {sync_chapter} 章" if sync_chapter > 0 else "尚未同步")

        # 加载立绘
        self._load_portrait(name)

        # 清空现有选项卡
        self.tab_widget.clear()

        # 添加三类属性选项卡
        explicit_attrs = self.profile_data.get('explicit_attributes', {})
        implicit_attrs = self.profile_data.get('implicit_attributes', {})
        social_attrs = self.profile_data.get('social_attributes', {})

        # 显性属性
        explicit_panel = AttributeCategoryPanel("显性属性", "◉", explicit_attrs)
        explicit_scroll = self._wrap_in_scroll(explicit_panel)
        self.tab_widget.addTab(explicit_scroll, f"显性 ({len(explicit_attrs)})")

        # 隐性属性
        implicit_panel = AttributeCategoryPanel("隐性属性", "◎", implicit_attrs)
        implicit_scroll = self._wrap_in_scroll(implicit_panel)
        self.tab_widget.addTab(implicit_scroll, f"隐性 ({len(implicit_attrs)})")

        # 社会属性
        social_panel = AttributeCategoryPanel("社会属性", "◈", social_attrs)
        social_scroll = self._wrap_in_scroll(social_panel)
        self.tab_widget.addTab(social_scroll, f"社会 ({len(social_attrs)})")

    def _wrap_in_scroll(self, widget: QWidget) -> QScrollArea:
        """将组件包装在滚动区域中"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(theme_manager.scrollbar())
        scroll.setWidget(widget)
        return scroll

    def _add_empty_tabs(self):
        """添加空选项卡"""
        self.tab_widget.clear()

        for name in ["显性 (0)", "隐性 (0)", "社会 (0)"]:
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_label = QLabel("暂无数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {theme_manager.FONT_SIZE_MD};
                padding: {dp(40)}px;
            """)
            empty_layout.addWidget(empty_label)
            self.tab_widget.addTab(empty_widget, name)

    def _load_portrait(self, character_name: str):
        """加载角色立绘"""
        try:
            result = self.api_client.get_character_portraits(self.project_id, character_name)
            portraits = result.get('portraits', [])

            # 查找激活的立绘
            for portrait in portraits:
                if portrait.get('is_active'):
                    image_path = portrait.get('image_path')
                    if image_path:
                        image_url = self.api_client.get_portrait_image_url(image_path)
                        self._display_portrait(image_url)
                        return

            # 没有激活的立绘，使用第一个
            if portraits:
                image_path = portraits[0].get('image_path')
                if image_path:
                    image_url = self.api_client.get_portrait_image_url(image_path)
                    self._display_portrait(image_url)

        except Exception as e:
            logger.warning(f"加载角色立绘失败: {e}")

    def _display_portrait(self, image_url: str):
        """异步显示立绘图片"""
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
                        dp(100), dp(100),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.portrait_label.setPixmap(scaled)
                    self.portrait_label.setText("")
                    self.portrait_label.setStyleSheet(f"""
                        QLabel#portrait_label {{
                            background-color: transparent;
                            border: none;
                            border-radius: {theme_manager.RADIUS_MD};
                        }}
                    """)

        def on_error(error):
            logger.warning(f"显示立绘失败: {error}")

        self._portrait_worker = AsyncWorker(do_fetch)
        self._portrait_worker.success.connect(on_success)
        self._portrait_worker.error.connect(on_error)
        self._portrait_worker.start()
