"""
V2 主题配置编辑器

面向组件的主题配置编辑界面，支持：
- 效果配置（透明、动画等）
- 组件配置（按钮、卡片、侧边栏等）
- 设计令牌（高级用户，默认折叠）

布局：
+------------------------------------------------------------------+
| [浅色主题] [深色主题]                              顶部Tab切换     |
+---------------+--------------------------------------------------+
| 子主题列表     | 配置编辑区（可滚动）                               |
| +------------+ | +----------------------------------------------+ |
| | + 新建     | | | > 效果配置                                  | |
| +------------+ | |   [x] 启用透明效果                          | |
| | 书香浅色 * | | |   [x] 系统级模糊 (Windows)                  | |
| | 我的主题   | | |   动画速度: [正常 v]                        | |
| +------------+ | +----------------------------------------------+ |
|               | | > 按钮                                       | |
|               | |   [主要] [次要] [幽灵] [危险]   <- 变体Tab   | |
|               | |   背景色: [#8B4513] [选择]                  | |
|               | |   悬浮背景: [#A0522D] [选择]                | |
|               | +----------------------------------------------+ |
|               | | > 侧边栏（含透明）                           | |
|               | |   背景色: [#F9F5F0]                         | |
|               | |   [x] 启用透明   透明度: [===●===] 85%      | |
|               | +----------------------------------------------+ |
|               | | v 设计令牌（高级）                           | |
|               | |   （折叠状态，点击展开）                      | |
|               | +----------------------------------------------+ |
+---------------+--------------------------------------------------+
| [重置为默认]                          [保存] [激活]              |
+------------------------------------------------------------------+
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QListWidget, QScrollArea, QTabWidget, QLineEdit,
    QGroupBox, QGridLayout, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.worker_manager import WorkerManager
from api.manager import APIClientManager
from components.inputs import (
    ColorPickerWidget, SizeInputWidget, FontFamilySelector,
    SliderInputWidget, SwitchWidget
)
from .v2_config_groups import (
    EFFECTS_CONFIG, COMPONENT_CONFIGS, TOKEN_CONFIGS,
    get_component_field_key, get_token_field_key, get_effect_field_key
)
from .v2_components import CollapsibleSection, VariantTabWidget, ComponentEditor
from .config_editor import ThemeEditorBaseMixin
from .styles import build_list_action_button_style

logger = logging.getLogger(__name__)


class EffectsEditor(QWidget):
    """效果配置编辑器

    V2组件模式的效果配置，包含基本效果开关。
    注意：透明度配置已移至V1经典模式(ThemeSettingsWidget)处理。
    """

    value_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._field_widgets: Dict[str, QWidget] = {}
        self._setup_ui()
        self._apply_theme()

        theme_manager.theme_changed.connect(self._apply_theme)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        import sys

        # 提示信息：透明度配置在经典模式
        hint_label = QLabel("提示：透明度配置请在「经典模式」中调整")
        hint_label.setObjectName("hint_label")
        layout.addWidget(hint_label)

        # 效果配置字段
        for field_key, field_info in EFFECTS_CONFIG["fields"].items():
            platform = field_info.get("platform")
            if platform and sys.platform != platform:
                continue

            field_type = field_info.get("type", "switch")
            field_label = field_info.get("label", field_key)
            description = field_info.get("description", "")

            if field_type == "switch":
                widget = SwitchWidget(
                    label=field_label,
                    default=field_info.get("default", False),
                    description=description
                )
                widget.toggled.connect(lambda: self.value_changed.emit())
                self._field_widgets[field_key] = widget
                layout.addWidget(widget)
            elif field_type == "select":
                container = QWidget()
                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)

                label = QLabel(f"{field_label}:")
                label.setObjectName("effect_label")
                h_layout.addWidget(label)

                combo = QComboBox()
                combo.setObjectName("effect_select")
                for opt_val, opt_label in field_info.get("options", []):
                    combo.addItem(opt_label, opt_val)
                default = field_info.get("default", "normal")
                index = combo.findData(default)
                if index >= 0:
                    combo.setCurrentIndex(index)
                combo.currentIndexChanged.connect(lambda: self.value_changed.emit())
                h_layout.addWidget(combo)
                h_layout.addStretch()

                self._field_widgets[field_key] = combo
                layout.addWidget(container)

        layout.addStretch()

    def get_values(self) -> Dict[str, Any]:
        """获取所有效果配置值"""
        result = {}
        for key, widget in self._field_widgets.items():
            if isinstance(widget, SwitchWidget):
                result[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentData()
        return result

    def set_values(self, values: Dict[str, Any]):
        """设置效果配置值"""
        for key, widget in self._field_widgets.items():
            if key not in values:
                continue
            value = values[key]
            if isinstance(widget, SwitchWidget):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

    def _apply_theme(self, theme_name: str = None):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 提示标签样式
        for label in self.findChildren(QLabel, "hint_label"):
            label.setStyleSheet(f"""
                QLabel#hint_label {{
                    font-family: {palette.ui_font};
                    font-size: {sp(12)}px;
                    color: {palette.text_tertiary};
                    padding: {dp(8)}px;
                    background-color: {theme_manager.BG_TERTIARY};
                    border-radius: {dp(4)}px;
                }}
            """)


class V2ThemeEditorWidget(ThemeEditorBaseMixin, QWidget):
    """V2 主题配置编辑器主界面"""

    _worker_key_prefix = "theme_v2_config"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()

        # 状态
        self._current_mode = "light"
        self._current_config_id = None
        self._configs: List[Dict] = []
        self._is_modified = False
        self._is_destroyed = False  # 标记widget是否已销毁
        self.worker_manager = WorkerManager(self)

        # 编辑器组件
        self._effects_editor: Optional[EffectsEditor] = None
        self._component_editors: Dict[str, ComponentEditor] = {}
        self._token_editors: Dict[str, ComponentEditor] = {}

        self._create_ui()
        self._apply_theme()

        theme_manager.theme_changed.connect(self._apply_theme)

    def _request_config_list(self):
        return self.api_client.get_theme_configs()

    def _request_config_detail(self, config_id: int):
        return self.api_client.get_unified_theme_config(config_id)

    def _request_create_config(self, payload: Dict[str, Any]):
        return self.api_client.create_theme_v2_config(payload)

    def _request_duplicate_config(self, config_id: int):
        return self.api_client.duplicate_theme_config(config_id)

    def _request_delete_config(self, config_id: int):
        return self.api_client.delete_theme_config(config_id)

    def _request_save_config(self, config_id: int, payload: Dict[str, Any]):
        return self.api_client.update_theme_v2_config(config_id, payload)

    def _request_activate_config(self, config_id: int):
        return self.api_client.activate_theme_config(config_id)

    def _request_reset_config(self, config_id: int):
        return self.api_client.reset_theme_v2_config(config_id)

    def _handle_save_without_config(self) -> bool:
        from utils.message_service import MessageService

        MessageService.show_warning(self, "请先选择一个配置")
        return True

    def closeEvent(self, event):
        """关闭事件：清理异步工作线程"""
        self._cleanup_worker()
        super().closeEvent(event)

    def _cleanup_worker(self):
        """清理异步工作线程"""
        self._is_destroyed = True
        if hasattr(self, 'worker_manager'):
            self.worker_manager.cleanup_all()

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
        self.name_input.textChanged.connect(self._mark_modified)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input, stretch=1)
        self.config_layout.addLayout(name_layout)

        # 效果配置区域
        effects_section = CollapsibleSection("效果配置")
        self._effects_editor = EffectsEditor()
        self._effects_editor.value_changed.connect(self._mark_modified)
        effects_section.add_widget(self._effects_editor)
        self.config_layout.addWidget(effects_section)

        # 组件配置区域
        for comp_key, comp_config in COMPONENT_CONFIGS.items():
            section = CollapsibleSection(comp_config.get("label", comp_key))
            if comp_config.get("description"):
                section.setToolTip(comp_config["description"])

            editor = ComponentEditor(comp_key, comp_config)
            editor.value_changed.connect(self._mark_modified)
            section.add_widget(editor)

            self._component_editors[comp_key] = editor
            self.config_layout.addWidget(section)

        # 设计令牌区域（默认折叠）
        tokens_section = CollapsibleSection("设计令牌（高级）", collapsed=True)
        for token_key, token_config in TOKEN_CONFIGS.items():
            token_section = CollapsibleSection(
                token_config.get("label", token_key),
                collapsed=token_config.get("collapsed", True)
            )
            # 简化：使用ComponentEditor的字段创建逻辑
            editor = ComponentEditor(token_key, {"fields": token_config.get("fields", {})})
            editor.value_changed.connect(self._mark_modified)
            token_section.add_widget(editor)
            tokens_section.add_widget(token_section)
            self._token_editors[token_key] = editor

        self.config_layout.addWidget(tokens_section)

        self.config_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        return panel

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

    def _populate_editor(self, config: Dict[str, Any]):
        """填充编辑器"""
        self.name_input.setText(config.get("config_name", ""))

        # 效果配置
        effects = config.get("effects", {})
        if effects and self._effects_editor:
            self._effects_editor.set_values(effects)

        # 组件配置
        for comp_key, editor in self._component_editors.items():
            comp_data = config.get(f"comp_{comp_key}", {})
            if comp_data:
                editor.set_values(comp_data)

        # 令牌配置
        for token_key, editor in self._token_editors.items():
            token_data = config.get(f"token_{token_key}", {})
            if token_data:
                editor.set_values(token_data)

    def _clear_editor(self):
        """清空编辑器"""
        self.name_input.clear()
        # 其他编辑器的清空由各自处理

    def _collect_config_data(self) -> Dict[str, Any]:
        """收集编辑器数据"""
        data = {
            "config_name": self.name_input.text().strip(),
            "parent_mode": self._current_mode,
        }

        # 效果配置
        if self._effects_editor:
            data["effects"] = self._effects_editor.get_values()

        # 组件配置
        for comp_key, editor in self._component_editors.items():
            comp_values = editor.get_values()
            if comp_values:
                data[f"comp_{comp_key}"] = comp_values

        # 令牌配置
        for token_key, editor in self._token_editors.items():
            token_values = editor.get_values()
            if token_values:
                data[f"token_{token_key}"] = token_values

        return data

    def _mark_modified(self):
        """标记为已修改"""
        self._is_modified = True

    def refresh(self):
        """刷新配置列表"""
        self._load_configs()

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 工具提示样式（全局）
        self.setStyleSheet(f"""
            QToolTip {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(10)}px;
            }}
        """)

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
        left_panel = self.findChild(QFrame, "left_panel")
        if left_panel:
            left_panel.setStyleSheet(f"""
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
        list_btn_style = build_list_action_button_style(palette)
        self.duplicate_btn.setStyleSheet(list_btn_style)
        self.delete_btn.setStyleSheet(list_btn_style)

        # 右侧面板
        right_panel = self.findChild(QFrame, "right_panel")
        if right_panel:
            right_panel.setStyleSheet(f"""
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

        # 可折叠区域样式
        collapsible_style = f"""
            QPushButton#collapsible_header {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {palette.text_primary};
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(12)}px {dp(16)}px;
                text-align: left;
            }}
            QPushButton#collapsible_header:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            QWidget#collapsible_content {{
                background-color: transparent;
            }}
        """
        for section in self.findChildren(CollapsibleSection):
            section.setStyleSheet(collapsible_style)

        # 变体Tab按钮样式
        variant_tab_style = f"""
            QPushButton#variant_tab {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton#variant_tab:hover {{
                color: {palette.text_primary};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            QPushButton#variant_tab:checked {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """
        for btn in self.findChildren(QPushButton, "variant_tab"):
            btn.setStyleSheet(variant_tab_style)

        # 字段标签样式
        field_label_style = f"""
            QLabel#field_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
            }}
        """
        for label in self.findChildren(QLabel, "field_label"):
            label.setStyleSheet(field_label_style)

        # 效果配置标签样式
        effect_label_style = f"""
            QLabel#effect_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
            }}
        """
        for label in self.findChildren(QLabel, "effect_label"):
            label.setStyleSheet(effect_label_style)

        # 下拉选择框样式
        select_style = f"""
            QComboBox#effect_select, QComboBox#select_field {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                min-width: {dp(120)}px;
            }}
            QComboBox#effect_select:hover, QComboBox#select_field:hover {{
                border-color: {palette.accent_color};
            }}
            QComboBox#effect_select::drop-down, QComboBox#select_field::drop-down {{
                border: none;
                width: {dp(20)}px;
            }}
            QComboBox#effect_select QAbstractItemView, QComboBox#select_field QAbstractItemView {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                selection-background-color: {theme_manager.PRIMARY_PALE};
                selection-color: {palette.accent_color};
            }}
        """
        for combo in self.findChildren(QComboBox):
            combo.setStyleSheet(select_style)

        # 文本输入框样式
        text_field_style = f"""
            QLineEdit#text_field {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit#text_field:focus {{
                border-color: {palette.accent_color};
            }}
        """
        for text_input in self.findChildren(QLineEdit, "text_field"):
            text_input.setStyleSheet(text_field_style)

        # 底部操作栏
        bottom_bar = self.findChild(QFrame, "bottom_bar")
        if bottom_bar:
            bottom_bar.setStyleSheet(f"""
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


__all__ = [
    "V2ThemeEditorWidget",
    "CollapsibleSection",
    "ComponentEditor",
    "EffectsEditor",
]
