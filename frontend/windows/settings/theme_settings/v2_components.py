"""
V2主题编辑器辅助组件

包含可折叠区域、变体Tab、组件编辑器等可复用组件。
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils.dpi_utils import dp
from components.inputs import (
    ColorPickerWidget, SizeInputWidget, FontFamilySelector,
    SliderInputWidget, SwitchWidget
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
            else:
                field_type = "text"
                field_label = field_key

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


__all__ = [
    "CollapsibleSection",
    "VariantTabWidget",
    "ComponentEditor",
]
