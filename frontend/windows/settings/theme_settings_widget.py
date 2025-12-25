"""
主题配置设置Widget

提供用户自定义主题的完整编辑界面。
"""

import json
import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QScrollArea,
    QTabWidget, QLineEdit, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from utils.message_service import MessageService
from api.manager import APIClientManager
from components.inputs import ColorPickerWidget, SizeInputWidget, FontFamilySelector
from components.dialogs import InputDialog

logger = logging.getLogger(__name__)


# 配置组定义：每个组包含的常量及其类型
CONFIG_GROUPS = {
    "primary_colors": {
        "label": "主色调",
        "fields": {
            "PRIMARY": ("color", "主色"),
            "PRIMARY_LIGHT": ("color", "浅主色"),
            "PRIMARY_DARK": ("color", "深主色"),
            "PRIMARY_PALE": ("color", "极浅主色"),
        }
    },
    "accent_colors": {
        "label": "强调色",
        "fields": {
            "ACCENT": ("color", "强调色"),
            "ACCENT_LIGHT": ("color", "浅强调色"),
            "ACCENT_DARK": ("color", "深强调色"),
            "ACCENT_PALE": ("color", "极浅强调色"),
        }
    },
    "text_colors": {
        "label": "文字色",
        "fields": {
            "TEXT_PRIMARY": ("color", "主文字色"),
            "TEXT_SECONDARY": ("color", "次文字色"),
            "TEXT_TERTIARY": ("color", "三级文字色"),
            "TEXT_PLACEHOLDER": ("color", "占位符色"),
            "TEXT_DISABLED": ("color", "禁用文字色"),
        }
    },
    "background_colors": {
        "label": "背景色",
        "fields": {
            "BG_PRIMARY": ("color", "主背景色"),
            "BG_SECONDARY": ("color", "次背景色"),
            "BG_TERTIARY": ("color", "三级背景色"),
            "BG_CARD": ("color", "卡片背景"),
            "BG_CARD_HOVER": ("color", "卡片悬浮背景"),
            "BG_MUTED": ("color", "柔和背景"),
            "BG_ACCENT": ("color", "强调背景"),
            "GLASS_BG": ("color", "玻璃态背景"),
        }
    },
    "semantic_colors": {
        "label": "语义色",
        "fields": {
            "SUCCESS": ("color", "成功色"),
            "SUCCESS_LIGHT": ("color", "浅成功色"),
            "SUCCESS_DARK": ("color", "深成功色"),
            "SUCCESS_BG": ("color", "成功背景"),
            "ERROR": ("color", "错误色"),
            "ERROR_LIGHT": ("color", "浅错误色"),
            "ERROR_DARK": ("color", "深错误色"),
            "ERROR_BG": ("color", "错误背景"),
            "WARNING": ("color", "警告色"),
            "WARNING_LIGHT": ("color", "浅警告色"),
            "WARNING_DARK": ("color", "深警告色"),
            "WARNING_BG": ("color", "警告背景"),
            "INFO": ("color", "信息色"),
            "INFO_LIGHT": ("color", "浅信息色"),
            "INFO_DARK": ("color", "深信息色"),
            "INFO_BG": ("color", "信息背景"),
        }
    },
    "border_effects": {
        "label": "边框与阴影",
        "fields": {
            "BORDER_DEFAULT": ("color", "默认边框"),
            "BORDER_LIGHT": ("color", "浅边框"),
            "BORDER_DARK": ("color", "深边框"),
            "SHADOW_COLOR": ("text", "阴影颜色"),
            "OVERLAY_COLOR": ("text", "遮罩颜色"),
            "SHADOW_CARD": ("text", "卡片阴影"),
            "SHADOW_CARD_HOVER": ("text", "卡片悬浮阴影"),
            "SHADOW_SIENNA": ("text", "书香阴影"),
            "SHADOW_SIENNA_HOVER": ("text", "书香悬浮阴影"),
        }
    },
    "button_colors": {
        "label": "按钮文字",
        "fields": {
            "BUTTON_TEXT": ("color", "按钮主文字"),
            "BUTTON_TEXT_SECONDARY": ("color", "按钮次文字"),
        }
    },
    "typography": {
        "label": "字体配置",
        "fields": {
            "FONT_HEADING": ("font", "标题字体"),
            "FONT_BODY": ("font", "正文字体"),
            "FONT_DISPLAY": ("font", "展示字体"),
            "FONT_UI": ("font", "UI字体"),
            "FONT_SIZE_XS": ("size", "超小字号"),
            "FONT_SIZE_SM": ("size", "小字号"),
            "FONT_SIZE_BASE": ("size", "基础字号"),
            "FONT_SIZE_MD": ("size", "中等字号"),
            "FONT_SIZE_LG": ("size", "大字号"),
            "FONT_SIZE_XL": ("size", "超大字号"),
            "FONT_SIZE_2XL": ("size", "特大字号"),
            "FONT_SIZE_3XL": ("size", "超特大字号"),
            "FONT_WEIGHT_NORMAL": ("text", "正常粗细"),
            "FONT_WEIGHT_MEDIUM": ("text", "中等粗细"),
            "FONT_WEIGHT_SEMIBOLD": ("text", "半粗"),
            "FONT_WEIGHT_BOLD": ("text", "粗体"),
            "LINE_HEIGHT_TIGHT": ("text", "紧凑行高"),
            "LINE_HEIGHT_NORMAL": ("text", "正常行高"),
            "LINE_HEIGHT_RELAXED": ("text", "宽松行高"),
            "LINE_HEIGHT_LOOSE": ("text", "超宽松行高"),
        }
    },
    "border_radius": {
        "label": "圆角配置",
        "fields": {
            "RADIUS_XS": ("size", "超小圆角"),
            "RADIUS_SM": ("size", "小圆角"),
            "RADIUS_MD": ("size", "中等圆角"),
            "RADIUS_LG": ("size", "大圆角"),
            "RADIUS_XL": ("size", "超大圆角"),
            "RADIUS_2XL": ("size", "特大圆角"),
            "RADIUS_3XL": ("size", "超特大圆角"),
            "RADIUS_ROUND": ("text", "圆形"),
            "RADIUS_PILL": ("text", "药丸形"),
        }
    },
    "spacing": {
        "label": "间距配置",
        "fields": {
            "SPACING_XS": ("size", "超小间距"),
            "SPACING_SM": ("size", "小间距"),
            "SPACING_MD": ("size", "中等间距"),
            "SPACING_LG": ("size", "大间距"),
            "SPACING_XL": ("size", "超大间距"),
            "SPACING_XXL": ("size", "特大间距"),
        }
    },
    "animation": {
        "label": "动画配置",
        "fields": {
            "TRANSITION_FAST": ("size", "快速过渡"),
            "TRANSITION_BASE": ("size", "标准过渡"),
            "TRANSITION_SLOW": ("size", "缓慢过渡"),
            "TRANSITION_DRAMATIC": ("size", "戏剧性过渡"),
            "EASING_DEFAULT": ("text", "默认缓动"),
        }
    },
    "button_sizes": {
        "label": "按钮尺寸",
        "fields": {
            "BUTTON_HEIGHT_SM": ("size", "小按钮高度"),
            "BUTTON_HEIGHT_DEFAULT": ("size", "默认按钮高度"),
            "BUTTON_HEIGHT_LG": ("size", "大按钮高度"),
            "BUTTON_PADDING_SM": ("size", "小按钮内边距"),
            "BUTTON_PADDING_DEFAULT": ("size", "默认按钮内边距"),
            "BUTTON_PADDING_LG": ("size", "大按钮内边距"),
        }
    },
}


class ThemeSettingsWidget(QWidget):
    """主题配置设置Widget

    布局：
    ┌──────────────────────────────────────────────────────────────────┐
    │ [浅色主题] [深色主题]                              顶部Tab切换    │
    ├────────────────┬─────────────────────────────────────────────────┤
    │ 子主题列表     │ 配置编辑区（可滚动）                            │
    │ ┌────────────┐ │ ┌─────────────────────────────────────────────┐ │
    │ │ + 新建     │ │ │ ▼ 主色调                                    │ │
    │ ├────────────┤ │ │   PRIMARY        [#8B4513] [选择]           │ │
    │ │ 书香浅色 ★ │ │ │   ...                                       │ │
    │ │ 我的主题   │ │ └─────────────────────────────────────────────┘ │
    │ └────────────┘ │                                                 │
    ├────────────────┴─────────────────────────────────────────────────┤
    │ [重置为默认]                    [预览] [保存] [激活]             │
    └──────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()

        # 状态
        self._current_mode = "light"  # 当前选中的顶级主题模式
        self._current_config_id = None  # 当前选中的配置ID
        self._configs: List[Dict] = []  # 配置列表缓存
        self._field_widgets: Dict[str, Dict[str, QWidget]] = {}  # 字段编辑器映射
        self._is_modified = False  # 是否有未保存的修改
        self._worker = None  # AsyncWorker实例，防止垃圾回收

        self._create_ui()
        self._apply_theme()
        # 注意：_load_configs() 由 SettingsView._load_page_data() 通过 refresh() 延迟调用

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(dp(16))

        # 顶部Tab切换
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setObjectName("mode_tabs")
        self.mode_tabs.addTab(QWidget(), "浅色主题")
        self.mode_tabs.addTab(QWidget(), "深色主题")
        self.mode_tabs.currentChanged.connect(self._on_mode_changed)
        main_layout.addWidget(self.mode_tabs)

        # 内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(dp(16))

        # 左侧：子主题列表
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel)

        # 右侧：配置编辑区
        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)

        # 底部操作按钮
        bottom_bar = self._create_bottom_bar()
        main_layout.addWidget(bottom_bar)

    def _create_left_panel(self) -> QWidget:
        """创建左侧子主题列表面板"""
        panel = QFrame()
        panel.setObjectName("left_panel")
        panel.setFixedWidth(dp(200))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        layout.setSpacing(dp(8))

        # 新建按钮
        self.new_btn = QPushButton("+ 新建子主题")
        self.new_btn.setObjectName("new_theme_btn")
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.clicked.connect(self._create_new_config)
        layout.addWidget(self.new_btn)

        # 子主题列表
        self.config_list = QListWidget()
        self.config_list.setObjectName("config_list")
        self.config_list.setFrameShape(QFrame.Shape.NoFrame)
        self.config_list.currentRowChanged.connect(self._on_config_selected)
        layout.addWidget(self.config_list, stretch=1)

        # 列表操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(8))

        self.duplicate_btn = QPushButton("复制")
        self.duplicate_btn.setObjectName("list_action_btn")
        self.duplicate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.duplicate_btn.clicked.connect(self._duplicate_config)
        btn_layout.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("list_action_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._delete_config)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧配置编辑区"""
        panel = QFrame()
        panel.setObjectName("right_panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("config_scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 滚动内容
        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        self.config_layout = QVBoxLayout(scroll_content)
        self.config_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        self.config_layout.setSpacing(dp(16))

        # 配置名称编辑
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称：")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入配置名称")
        self.name_input.textChanged.connect(lambda: self._mark_modified())
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input, stretch=1)
        self.config_layout.addLayout(name_layout)

        # 创建各配置组
        self._create_config_groups()

        self.config_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        return panel

    def _create_config_groups(self):
        """创建配置分组"""
        for group_key, group_def in CONFIG_GROUPS.items():
            group_box = QGroupBox(group_def["label"])
            group_box.setObjectName(f"group_{group_key}")

            grid = QGridLayout(group_box)
            grid.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
            grid.setSpacing(dp(8))
            grid.setColumnStretch(1, 1)

            self._field_widgets[group_key] = {}

            row = 0
            for field_key, (field_type, field_label) in group_def["fields"].items():
                # 标签
                label = QLabel(f"{field_label}:")
                label.setObjectName("field_label")
                grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)

                # 输入组件
                if field_type == "color":
                    widget = ColorPickerWidget()
                    widget.color_changed.connect(lambda: self._mark_modified())
                elif field_type == "size":
                    widget = SizeInputWidget(allowed_units=["px", "em", "rem", "%", "ms"])
                    widget.value_changed.connect(lambda: self._mark_modified())
                elif field_type == "font":
                    widget = FontFamilySelector()
                    widget.value_changed.connect(lambda: self._mark_modified())
                else:  # text
                    widget = QLineEdit()
                    widget.setObjectName("text_field_input")
                    widget.textChanged.connect(lambda: self._mark_modified())

                grid.addWidget(widget, row, 1)
                self._field_widgets[group_key][field_key] = widget
                row += 1

            self.config_layout.addWidget(group_box)

    def _create_bottom_bar(self) -> QWidget:
        """创建底部操作栏"""
        bar = QFrame()
        bar.setObjectName("bottom_bar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 重置按钮
        self.reset_btn = QPushButton("重置为默认")
        self.reset_btn.setObjectName("reset_btn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset_config)
        layout.addWidget(self.reset_btn)

        # 导入按钮
        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("import_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_configs)
        layout.addWidget(self.import_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_configs)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_config)
        layout.addWidget(self.save_btn)

        # 激活按钮
        self.activate_btn = QPushButton("激活")
        self.activate_btn.setObjectName("activate_btn")
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.clicked.connect(self._activate_config)
        layout.addWidget(self.activate_btn)

        return bar

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # Tab样式
        self.mode_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: {dp(12)}px {dp(24)}px;
                margin-right: {dp(8)}px;
            }}
            QTabBar::tab:hover {{
                color: {palette.text_primary};
            }}
            QTabBar::tab:selected {{
                color: {palette.accent_color};
                border-bottom: 2px solid {palette.accent_color};
            }}
        """)

        # 左侧面板
        self.findChild(QFrame, "left_panel").setStyleSheet(f"""
            QFrame#left_panel {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

        # 新建按钮
        self.new_btn.setStyleSheet(f"""
            QPushButton#new_theme_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.accent_color};
                background-color: transparent;
                border: 1px dashed {palette.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(10)}px;
            }}
            QPushButton#new_theme_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """)

        # 配置列表
        self.config_list.setStyleSheet(f"""
            QListWidget#config_list {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#config_list::item {{
                color: {palette.text_secondary};
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(10)}px;
                margin: {dp(2)}px 0;
            }}
            QListWidget#config_list::item:hover {{
                color: {palette.text_primary};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            QListWidget#config_list::item:selected {{
                color: {palette.accent_color};
                background-color: {palette.bg_primary};
                font-weight: 500;
            }}
        """)

        # 列表操作按钮
        list_btn_style = f"""
            QPushButton#list_action_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton#list_action_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.duplicate_btn.setStyleSheet(list_btn_style)
        self.delete_btn.setStyleSheet(list_btn_style)

        # 右侧面板
        self.findChild(QFrame, "right_panel").setStyleSheet(f"""
            QFrame#right_panel {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

        # 滚动区域
        scroll = self.findChild(QScrollArea, "config_scroll")
        if scroll:
            scroll.setStyleSheet(f"""
                QScrollArea#config_scroll {{
                    background-color: transparent;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background-color: {palette.bg_primary};
                    width: {dp(8)}px;
                    border-radius: {dp(4)}px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {palette.border_color};
                    border-radius: {dp(4)}px;
                    min-height: {dp(30)}px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {palette.accent_color};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0;
                }}
            """)

        # 滚动内容区域背景
        scroll_content = self.findChild(QWidget, "scroll_content")
        if scroll_content:
            scroll_content.setStyleSheet(f"""
                QWidget#scroll_content {{
                    background-color: {palette.bg_secondary};
                }}
            """)

        # 配置名称标签
        name_label = self.config_layout.itemAt(0)
        if name_label and name_label.layout():
            label_widget = name_label.layout().itemAt(0)
            if label_widget and label_widget.widget():
                label_widget.widget().setStyleSheet(f"""
                    QLabel {{
                        font-family: {palette.ui_font};
                        font-size: {sp(14)}px;
                        color: {palette.text_primary};
                        background-color: transparent;
                    }}
                """)

        # 配置名称输入
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(12)}px;
            }}
            QLineEdit:focus {{
                border-color: {palette.accent_color};
            }}
        """)

        # 配置组样式
        group_style = f"""
            QGroupBox {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {palette.text_primary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                margin-top: {dp(12)}px;
                padding-top: {dp(8)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {dp(12)}px;
                padding: 0 {dp(8)}px;
                background-color: {palette.bg_secondary};
            }}
            QLabel#field_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
            }}
        """
        for group_key in CONFIG_GROUPS:
            group_box = self.findChild(QGroupBox, f"group_{group_key}")
            if group_box:
                group_box.setStyleSheet(group_style)

        # 文本类型输入框样式（阴影颜色、遮罩颜色等）
        text_input_style = f"""
            QLineEdit#text_field_input {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit#text_field_input:focus {{
                border-color: {palette.accent_color};
            }}
        """
        for text_input in self.findChildren(QLineEdit, "text_field_input"):
            text_input.setStyleSheet(text_input_style)

        # 底部操作栏
        self.findChild(QFrame, "bottom_bar").setStyleSheet(f"""
            QFrame#bottom_bar {{
                background-color: {palette.bg_primary};
                border-top: 1px solid {palette.border_color};
            }}
        """)

        # 重置按钮
        self.reset_btn.setStyleSheet(f"""
            QPushButton#reset_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton#reset_btn:hover {{
                color: {theme_manager.WARNING};
                border-color: {theme_manager.WARNING};
            }}
        """)

        # 导入导出按钮样式
        io_btn_style = f"""
            QPushButton {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.import_btn.setStyleSheet(io_btn_style)
        self.export_btn.setStyleSheet(io_btn_style)

        # 保存按钮
        self.save_btn.setStyleSheet(f"""
            QPushButton#save_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.accent_color};
                background-color: transparent;
                border: 1px solid {palette.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(20)}px;
            }}
            QPushButton#save_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """)

        # 激活按钮
        self.activate_btn.setStyleSheet(f"""
            QPushButton#activate_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.BUTTON_TEXT};
                background-color: {palette.accent_color};
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(20)}px;
            }}
            QPushButton#activate_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def _load_configs(self):
        """加载配置列表"""
        def do_load():
            return self.api_client.get_theme_configs()

        def on_success(configs):
            self._configs = configs
            self._update_config_list()

        def on_error(error):
            logger.error(f"加载主题配置失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _update_config_list(self):
        """更新配置列表显示"""
        self.config_list.clear()

        # 筛选当前模式的配置
        mode_configs = [c for c in self._configs if c.get("parent_mode") == self._current_mode]

        for config in mode_configs:
            item = QListWidgetItem()
            name = config.get("config_name", "未命名")
            if config.get("is_active"):
                name = f"{name} *"
            item.setText(name)
            item.setData(Qt.ItemDataRole.UserRole, config.get("id"))
            self.config_list.addItem(item)

        # 自动选中第一项
        if self.config_list.count() > 0:
            self.config_list.setCurrentRow(0)
        else:
            self._clear_editor()

    def _on_mode_changed(self, index: int):
        """模式切换处理"""
        self._current_mode = "light" if index == 0 else "dark"
        self._update_config_list()

    def _on_config_selected(self, row: int):
        """配置选中处理"""
        if row < 0:
            self._current_config_id = None
            self._clear_editor()
            return

        item = self.config_list.item(row)
        if item:
            config_id = item.data(Qt.ItemDataRole.UserRole)
            self._current_config_id = config_id
            self._load_config_detail(config_id)

    def _load_config_detail(self, config_id: int):
        """加载配置详情"""
        def do_load():
            return self.api_client.get_theme_config(config_id)

        def on_success(config):
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            logger.error(f"加载配置详情失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _populate_editor(self, config: Dict[str, Any]):
        """填充编辑器"""
        self.name_input.setText(config.get("config_name", ""))

        for group_key, group_data in CONFIG_GROUPS.items():
            config_values = config.get(group_key, {}) or {}
            for field_key in group_data["fields"]:
                widget = self._field_widgets.get(group_key, {}).get(field_key)
                value = config_values.get(field_key, "")
                if widget:
                    if isinstance(widget, ColorPickerWidget):
                        widget.set_color(value or "")
                    elif isinstance(widget, SizeInputWidget):
                        widget.set_value(value or "")
                    elif isinstance(widget, FontFamilySelector):
                        widget.set_value(value or "")
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(value) if value else "")

    def _clear_editor(self):
        """清空编辑器"""
        self.name_input.clear()
        for group_widgets in self._field_widgets.values():
            for widget in group_widgets.values():
                if isinstance(widget, ColorPickerWidget):
                    widget.set_color("")
                elif isinstance(widget, SizeInputWidget):
                    widget.set_value("")
                elif isinstance(widget, FontFamilySelector):
                    widget.set_value("")
                elif isinstance(widget, QLineEdit):
                    widget.clear()

    def _collect_config_data(self) -> Dict[str, Any]:
        """收集编辑器数据"""
        data = {
            "config_name": self.name_input.text().strip(),
            "parent_mode": self._current_mode,
        }

        for group_key, group_data in CONFIG_GROUPS.items():
            group_values = {}
            for field_key in group_data["fields"]:
                widget = self._field_widgets.get(group_key, {}).get(field_key)
                if widget:
                    if isinstance(widget, ColorPickerWidget):
                        value = widget.get_color()
                    elif isinstance(widget, SizeInputWidget):
                        value = widget.get_value()
                    elif isinstance(widget, FontFamilySelector):
                        value = widget.get_value()
                    elif isinstance(widget, QLineEdit):
                        value = widget.text().strip()
                    else:
                        value = ""
                    if value:
                        group_values[field_key] = value
            if group_values:
                data[group_key] = group_values

        return data

    def _mark_modified(self):
        """标记为已修改"""
        self._is_modified = True

    def _create_new_config(self):
        """创建新配置"""
        default_name = f"我的{'浅色' if self._current_mode == 'light' else '深色'}主题"
        name, ok = InputDialog.getTextStatic(
            parent=self,
            title="新建子主题",
            label="请输入子主题名称：",
            text=default_name
        )
        if not ok or not name.strip():
            return

        def do_create():
            return self.api_client.create_theme_config({
                "config_name": name.strip(),
                "parent_mode": self._current_mode
            })

        def on_success(config):
            MessageService.show_success(self, f"已创建子主题：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"创建失败：{error}")

        self._worker = AsyncWorker(do_create)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _duplicate_config(self):
        """复制当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_duplicate():
            return self.api_client.duplicate_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已复制为：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"复制失败：{error}")

        self._worker = AsyncWorker(do_duplicate)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _delete_config(self):
        """删除当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        if not MessageService.confirm(
            self,
            "确定要删除此配置吗？此操作不可恢复。",
            "确认删除",
            confirm_text="删除",
            cancel_text="取消"
        ):
            return

        def do_delete():
            return self.api_client.delete_theme_config(self._current_config_id)

        def on_success(result):
            MessageService.show_success(self, "配置已删除")
            self._current_config_id = None
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"删除失败：{error}")

        self._worker = AsyncWorker(do_delete)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _save_config(self):
        """保存当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        data = self._collect_config_data()

        def do_save():
            return self.api_client.update_theme_config(self._current_config_id, data)

        def on_success(config):
            MessageService.show_success(self, "配置已保存")
            self._is_modified = False
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"保存失败：{error}")

        self._worker = AsyncWorker(do_save)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _activate_config(self):
        """激活当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_activate():
            return self.api_client.activate_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已激活：{config.get('config_name')}")
            self._load_configs()
            # 通知主题管理器应用新配置
            self._apply_active_theme(config)

        def on_error(error):
            MessageService.show_error(self, f"激活失败：{error}")

        self._worker = AsyncWorker(do_activate)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _reset_config(self):
        """重置配置为默认值"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        if not MessageService.confirm(
            self,
            "确定要将此配置重置为默认值吗？",
            "确认重置",
            confirm_text="重置",
            cancel_text="取消"
        ):
            return

        def do_reset():
            return self.api_client.reset_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, "配置已重置为默认值")
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            MessageService.show_error(self, f"重置失败：{error}")

        self._worker = AsyncWorker(do_reset)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _apply_active_theme(self, config: Dict[str, Any]):
        """应用激活的主题配置到主题管理器"""
        # 合并所有配置组为平面字典
        flat_config = {}
        for group_key in CONFIG_GROUPS:
            group_values = config.get(group_key, {}) or {}
            flat_config.update(group_values)

        # 调用主题管理器应用自定义主题
        if hasattr(theme_manager, 'apply_custom_theme'):
            theme_manager.apply_custom_theme(flat_config)

    def _export_configs(self):
        """导出主题配置"""
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出主题配置",
            "theme_configs.json",
            "JSON文件 (*.json)"
        )
        if not file_path:
            return

        def do_export():
            return self.api_client.export_all_theme_configs()

        def on_success(export_data):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                MessageService.show_success(self, f"已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"保存文件失败：{e}")

        def on_error(error):
            MessageService.show_error(self, f"导出失败：{error}")

        self._worker = AsyncWorker(do_export)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _import_configs(self):
        """导入主题配置"""
        # 选择文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入主题配置",
            "",
            "JSON文件 (*.json)"
        )
        if not file_path:
            return

        # 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except json.JSONDecodeError as e:
            MessageService.show_error(self, f"JSON格式错误：{e}")
            return
        except Exception as e:
            MessageService.show_error(self, f"读取文件失败：{e}")
            return

        # 确认导入
        config_count = len(import_data.get('configs', []))
        if config_count == 0:
            MessageService.show_warning(self, "文件中没有可导入的配置")
            return

        if not MessageService.confirm(
            self,
            f"即将导入 {config_count} 个主题配置。\n\n"
            "同名配置将被跳过，是否继续？",
            "确认导入"
        ):
            return

        def do_import():
            return self.api_client.import_theme_configs(import_data)

        def on_success(result):
            imported = result.get('imported_count', 0)
            skipped = result.get('skipped_count', 0)
            msg = f"成功导入 {imported} 个配置"
            if skipped > 0:
                msg += f"，跳过 {skipped} 个同名配置"
            MessageService.show_success(self, msg)
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"导入失败：{error}")

        self._worker = AsyncWorker(do_import)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def refresh(self):
        """刷新配置列表"""
        self._load_configs()
