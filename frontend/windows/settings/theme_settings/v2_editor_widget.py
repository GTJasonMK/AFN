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
    QListWidget, QListWidgetItem, QScrollArea, QTabWidget, QLineEdit,
    QGroupBox, QGridLayout, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from utils.message_service import MessageService
from api.manager import APIClientManager
from components.inputs import (
    ColorPickerWidget, SizeInputWidget, FontFamilySelector,
    SliderInputWidget, SwitchWidget
)
from components.dialogs import InputDialog

from .v2_config_groups import (
    EFFECTS_CONFIG, COMPONENT_CONFIGS, TOKEN_CONFIGS,
    get_component_field_key, get_token_field_key, get_effect_field_key
)

logger = logging.getLogger(__name__)


class CollapsibleSection(QWidget):
    """可折叠的配置区域"""

    def __init__(self, title: str, parent=None, collapsed: bool = False):
        super().__init__(parent)
        self._collapsed = collapsed
        self._title = title

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        self.header = QPushButton()
        self.header.setObjectName("collapsible_header")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self._toggle)
        self._update_header_text()
        layout.addWidget(self.header)

        # 内容区域
        self.content = QWidget()
        self.content.setObjectName("collapsible_content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(dp(16), dp(8), dp(16), dp(16))
        self.content_layout.setSpacing(dp(12))
        layout.addWidget(self.content)

        # 初始状态
        self.content.setVisible(not self._collapsed)

    def _update_header_text(self):
        arrow = ">" if self._collapsed else "v"
        self.header.setText(f"  {arrow}  {self._title}")

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        self._update_header_text()

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        self.content.setVisible(not self._collapsed)
        self._update_header_text()


class VariantTabWidget(QWidget):
    """变体选择Tab组件"""

    variant_changed = pyqtSignal(str)

    def __init__(self, variants: Dict[str, Dict], parent=None):
        super().__init__(parent)
        self._variants = variants
        self._current_variant = None
        self._buttons: Dict[str, QPushButton] = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, dp(8))
        layout.setSpacing(dp(8))

        for key, info in self._variants.items():
            btn = QPushButton(info.get("label", key))
            btn.setObjectName("variant_tab")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_variant_clicked(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addStretch()

        # 默认选中第一个
        if self._variants:
            first_key = list(self._variants.keys())[0]
            self._select_variant(first_key)

    def _on_variant_clicked(self, key: str):
        self._select_variant(key)
        self.variant_changed.emit(key)

    def _select_variant(self, key: str):
        self._current_variant = key
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)

    def current_variant(self) -> str:
        return self._current_variant


class ComponentEditor(QWidget):
    """单个组件的编辑器"""

    value_changed = pyqtSignal()

    def __init__(self, component_key: str, config: Dict, parent=None):
        super().__init__(parent)
        self._component_key = component_key
        self._config = config
        self._field_widgets: Dict[str, QWidget] = {}
        self._variant_widgets: Dict[str, Dict[str, QWidget]] = {}
        self._current_variant: Optional[str] = None
        self._variant_tab: Optional[VariantTabWidget] = None
        self._variant_container: Optional[QWidget] = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 检查是否有变体
        variants = self._config.get("variants")
        if variants:
            # 变体选择Tab
            self._variant_tab = VariantTabWidget(variants)
            self._variant_tab.variant_changed.connect(self._on_variant_changed)
            layout.addWidget(self._variant_tab)

            # 变体内容容器
            self._variant_container = QWidget()
            self._variant_layout = QVBoxLayout(self._variant_container)
            self._variant_layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self._variant_container)

            # 为每个变体创建字段
            for variant_key, variant_info in variants.items():
                self._create_variant_fields(variant_key, variant_info)

            # 显示第一个变体
            if variants:
                first_key = list(variants.keys())[0]
                self._show_variant(first_key)
        else:
            # 直接字段编辑
            fields = self._config.get("fields", {})
            self._create_fields(fields, layout)

        # 透明效果配置（如果有）
        transparency = self._config.get("transparency")
        if transparency:
            trans_section = CollapsibleSection(transparency.get("label", "透明效果"))
            trans_fields = transparency.get("fields", {})
            self._create_transparency_fields(trans_fields, trans_section)
            layout.addWidget(trans_section)

        # 尺寸配置（如果有）
        sizes = self._config.get("sizes")
        if sizes:
            sizes_section = CollapsibleSection("尺寸配置", collapsed=True)
            for size_key, size_info in sizes.items():
                size_label = QLabel(f"  {size_info.get('label', size_key)}:")
                size_label.setObjectName("size_label")
                sizes_section.add_widget(size_label)
                size_fields = size_info.get("fields", {})
                grid = QGridLayout()
                grid.setSpacing(dp(8))
                self._create_fields_grid(size_fields, grid, f"sizes.{size_key}")
                sizes_section.add_layout(grid)
            layout.addWidget(sizes_section)

    def _create_variant_fields(self, variant_key: str, variant_info: Dict):
        """创建变体字段组"""
        container = QWidget()
        container.setVisible(False)
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        fields = variant_info.get("fields", {})
        self._variant_widgets[variant_key] = {}

        row = 0
        for field_key, field_info in fields.items():
            field_type, field_label = field_info[0], field_info[1]

            label = QLabel(f"{field_label}:")
            label.setObjectName("field_label")
            layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)

            widget = self._create_field_widget(field_type, field_info)
            layout.addWidget(widget, row, 1)
            self._variant_widgets[variant_key][field_key] = widget
            row += 1

        self._variant_layout.addWidget(container)

    def _create_fields(self, fields: Dict, parent_layout):
        """创建直接字段"""
        grid = QGridLayout()
        grid.setSpacing(dp(8))
        self._create_fields_grid(fields, grid)
        parent_layout.addLayout(grid)

    def _create_fields_grid(self, fields: Dict, grid: QGridLayout, prefix: str = ""):
        """在网格中创建字段"""
        row = 0
        for field_key, field_info in fields.items():
            if isinstance(field_info, tuple):
                field_type = field_info[0]
                field_label = field_info[1] if len(field_info) > 1 else field_key
            else:
                field_type = field_info.get("type", "text")
                field_label = field_info.get("label", field_key)

            label = QLabel(f"{field_label}:")
            label.setObjectName("field_label")
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)

            widget = self._create_field_widget(field_type, field_info)
            grid.addWidget(widget, row, 1)

            full_key = f"{prefix}.{field_key}" if prefix else field_key
            self._field_widgets[full_key] = widget
            row += 1

    def _create_transparency_fields(self, fields: Dict, section: CollapsibleSection):
        """创建透明效果字段"""
        grid = QGridLayout()
        grid.setSpacing(dp(8))

        row = 0
        for field_key, field_info in fields.items():
            if isinstance(field_info, tuple):
                field_type = field_info[0]
                field_label = field_info[1] if len(field_info) > 1 else field_key
                field_options = field_info[2] if len(field_info) > 2 else {}
            else:
                field_type = "text"
                field_label = field_key
                field_options = {}

            label = QLabel(f"{field_label}:")
            label.setObjectName("field_label")
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)

            widget = self._create_field_widget(field_type, field_info)
            grid.addWidget(widget, row, 1)

            self._field_widgets[f"transparency.{field_key}"] = widget
            row += 1

        section.add_layout(grid)

    def _create_field_widget(self, field_type: str, field_info) -> QWidget:
        """根据字段类型创建输入组件"""
        # 解析选项
        options = {}
        if isinstance(field_info, tuple) and len(field_info) > 2:
            options = field_info[2] if isinstance(field_info[2], dict) else {}

        if field_type == "color":
            widget = ColorPickerWidget()
            widget.color_changed.connect(self.value_changed.emit)
        elif field_type == "size":
            widget = SizeInputWidget(allowed_units=["px", "em", "rem", "%", "ms"])
            widget.value_changed.connect(self.value_changed.emit)
        elif field_type == "font":
            widget = FontFamilySelector()
            widget.value_changed.connect(self.value_changed.emit)
        elif field_type == "switch":
            widget = SwitchWidget(label="", default=False)
            widget.toggled.connect(lambda: self.value_changed.emit())
        elif field_type == "slider":
            min_val = options.get("min", 0.0)
            max_val = options.get("max", 1.0)
            step = options.get("step", 0.1)
            widget = SliderInputWidget(
                label="",
                min_value=min_val,
                max_value=max_val,
                step=step,
                default_value=min_val,
                value_format="{:.0%}" if max_val <= 1 else "{:.0f}"
            )
            widget.value_changed.connect(self.value_changed.emit)
        elif field_type == "select":
            widget = QComboBox()
            widget.setObjectName("select_field")
            if isinstance(field_info, dict):
                for opt_val, opt_label in field_info.get("options", []):
                    widget.addItem(opt_label, opt_val)
            widget.currentIndexChanged.connect(lambda: self.value_changed.emit())
        else:  # text
            widget = QLineEdit()
            widget.setObjectName("text_field")
            widget.textChanged.connect(lambda: self.value_changed.emit())

        return widget

    def _on_variant_changed(self, variant_key: str):
        self._show_variant(variant_key)

    def _show_variant(self, variant_key: str):
        """显示指定变体"""
        self._current_variant = variant_key
        # 隐藏所有变体容器
        for i in range(self._variant_layout.count()):
            widget = self._variant_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(False)
        # 显示当前变体
        if variant_key in self._variant_widgets:
            index = list(self._variant_widgets.keys()).index(variant_key)
            widget = self._variant_layout.itemAt(index).widget()
            if widget:
                widget.setVisible(True)

    def get_values(self) -> Dict[str, Any]:
        """获取所有字段值"""
        result = {}

        # 直接字段
        for key, widget in self._field_widgets.items():
            result[key] = self._get_widget_value(widget)

        # 变体字段
        if self._variant_widgets:
            result["variants"] = {}
            for variant_key, fields in self._variant_widgets.items():
                result["variants"][variant_key] = {}
                for field_key, widget in fields.items():
                    result["variants"][variant_key][field_key] = self._get_widget_value(widget)

        return result

    def set_values(self, values: Dict[str, Any]):
        """设置所有字段值"""
        # 直接字段
        for key, widget in self._field_widgets.items():
            if key in values:
                self._set_widget_value(widget, values[key])

        # 变体字段
        variants_data = values.get("variants", {})
        for variant_key, fields in self._variant_widgets.items():
            variant_values = variants_data.get(variant_key, {})
            for field_key, widget in fields.items():
                if field_key in variant_values:
                    self._set_widget_value(widget, variant_values[field_key])

    def _get_widget_value(self, widget: QWidget) -> Any:
        """获取组件值"""
        if isinstance(widget, ColorPickerWidget):
            return widget.get_color()
        elif isinstance(widget, SizeInputWidget):
            return widget.get_value()
        elif isinstance(widget, FontFamilySelector):
            return widget.get_value()
        elif isinstance(widget, SwitchWidget):
            return widget.isChecked()
        elif isinstance(widget, SliderInputWidget):
            return widget.get_value()
        elif isinstance(widget, QComboBox):
            return widget.currentData()
        elif isinstance(widget, QLineEdit):
            return widget.text().strip()
        return None

    def _set_widget_value(self, widget: QWidget, value: Any):
        """设置组件值"""
        if value is None:
            return

        if isinstance(widget, ColorPickerWidget):
            widget.set_color(str(value))
        elif isinstance(widget, SizeInputWidget):
            widget.set_value(str(value))
        elif isinstance(widget, FontFamilySelector):
            widget.set_value(str(value))
        elif isinstance(widget, SwitchWidget):
            widget.setChecked(bool(value))
        elif isinstance(widget, SliderInputWidget):
            widget.set_value(float(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))


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


class V2ThemeEditorWidget(QWidget):
    """V2 主题配置编辑器主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()

        # 状态
        self._current_mode = "light"
        self._current_config_id = None
        self._configs: List[Dict] = []
        self._is_modified = False
        self._worker = None
        self._is_destroyed = False  # 标记widget是否已销毁

        # 编辑器组件
        self._effects_editor: Optional[EffectsEditor] = None
        self._component_editors: Dict[str, ComponentEditor] = {}
        self._token_editors: Dict[str, ComponentEditor] = {}

        self._create_ui()
        self._apply_theme()

        theme_manager.theme_changed.connect(self._apply_theme)

    def closeEvent(self, event):
        """关闭事件：清理异步工作线程"""
        self._cleanup_worker()
        super().closeEvent(event)

    def _cleanup_worker(self):
        """清理异步工作线程"""
        self._is_destroyed = True
        if self._worker is not None:
            try:
                # 尝试取消工作线程
                if hasattr(self._worker, 'cancel'):
                    self._worker.cancel()
                # 断开所有信号连接
                try:
                    self._worker.success.disconnect()
                    self._worker.error.disconnect()
                except (TypeError, RuntimeError):
                    pass
                # 等待线程结束（最多100ms）
                if self._worker.isRunning():
                    self._worker.wait(100)
            except RuntimeError:
                pass
            self._worker = None

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

    # ==================== 数据操作 ====================

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

    def _load_configs(self):
        """加载配置列表"""
        if self._is_destroyed:
            return

        def do_load():
            return self.api_client.get_theme_configs()

        def on_success(configs):
            if self._is_destroyed:
                return
            self._configs = configs
            self._update_config_list()

        def on_error(error):
            if self._is_destroyed:
                return
            logger.error(f"加载主题配置失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _update_config_list(self):
        """更新配置列表显示"""
        self.config_list.clear()

        mode_configs = [c for c in self._configs if c.get("parent_mode") == self._current_mode]

        for config in mode_configs:
            item = QListWidgetItem()
            name = config.get("config_name", "未命名")
            if config.get("is_active"):
                name = f"{name} *"
            item.setText(name)
            item.setData(Qt.ItemDataRole.UserRole, config.get("id"))
            self.config_list.addItem(item)

        if self.config_list.count() > 0:
            self.config_list.setCurrentRow(0)
        else:
            self._clear_editor()

    def _load_config_detail(self, config_id: int):
        """加载V2配置详情"""
        if self._is_destroyed:
            return

        def do_load():
            # 优先使用统一格式API
            return self.api_client.get_unified_theme_config(config_id)

        def on_success(config):
            if self._is_destroyed:
                return
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            if self._is_destroyed:
                return
            logger.error(f"加载配置详情失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

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

    # ==================== CRUD 操作 ====================

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
            return self.api_client.create_theme_v2_config({
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
            return self.api_client.update_theme_v2_config(self._current_config_id, data)

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
        """激活当前配置（应用主题和透明效果）"""
        from themes.theme_manager import theme_manager

        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_activate():
            return self.api_client.activate_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已激活：{config.get('config_name')}")
            self._load_configs()
            # 使用批量更新模式，避免多次信号发射
            theme_manager.begin_batch_update()
            try:
                # 应用主题配置
                self._apply_active_theme(config)
                # 透明度配置已在主题应用中处理，无需单独调用
            finally:
                # 结束批量更新，统一发射一次信号
                theme_manager.end_batch_update()

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
            return self.api_client.reset_theme_v2_config(self._current_config_id)

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
        """应用激活的主题配置到主题管理器

        支持V1和V2两种配置格式，根据config_version字段自动选择。
        """
        config_version = config.get("config_version", 1)

        if config_version == 2 and config.get("effects"):
            # V2配置：使用面向组件的配置
            if hasattr(theme_manager, 'apply_v2_config'):
                theme_manager.apply_v2_config(config)
        else:
            # V1配置：合并所有配置组为平面字典
            from .config_groups import CONFIG_GROUPS
            flat_config = {}
            for group_key in CONFIG_GROUPS:
                group_values = config.get(group_key, {}) or {}
                flat_config.update(group_values)

            if flat_config and hasattr(theme_manager, 'apply_custom_theme'):
                theme_manager.apply_custom_theme(flat_config)

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
