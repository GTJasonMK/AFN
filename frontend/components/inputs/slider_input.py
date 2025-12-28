"""
滑块输入组件

提供带标签和数值显示的滑块输入，支持浮点数和实时预览。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class SliderInputWidget(QWidget):
    """滑块输入组件

    布局：
    ┌────────────────────────────────────────┐
    │ 侧边栏透明度                    [85%]  │
    │ ════════════════════●═══════════════   │
    │ 描述文字（可选）                        │
    └────────────────────────────────────────┘

    - 标签显示名称
    - 数值显示当前值
    - 滑块支持浮点数（内部使用整数模拟）
    - 可选描述文字
    """

    # 值变更信号
    value_changed = pyqtSignal(float)

    def __init__(
        self,
        label: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.01,
        default_value: float = 0.5,
        description: str = "",
        value_format: str = "{:.0%}",
        parent: Optional[QWidget] = None
    ):
        """初始化滑块输入组件

        Args:
            label: 标签文字
            min_value: 最小值
            max_value: 最大值
            step: 步进值
            default_value: 默认值
            description: 描述文字（可选）
            value_format: 值显示格式（默认百分比格式）
            parent: 父组件
        """
        super().__init__(parent)

        self._label = label
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._default_value = default_value
        self._description = description
        self._value_format = value_format

        # 计算滑块的整数范围（用于模拟浮点数）
        # 对于步进>=1的情况，使用1:1映射；否则使用倒数作为缩放因子
        if step >= 1:
            self._scale = 1
            self._slider_min = int(min_value)
            self._slider_max = int(max_value)
        else:
            self._scale = int(1.0 / step) if step > 0 else 100
            self._slider_min = int(min_value * self._scale)
            self._slider_max = int(max_value * self._scale)

        self._create_ui()
        self._apply_theme()
        self.set_value(default_value)

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        # 标签行：标签 + 数值显示
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label_widget = QLabel(self._label)
        self.label_widget.setObjectName("slider_label")
        header_layout.addWidget(self.label_widget)

        header_layout.addStretch()

        self.value_label = QLabel()
        self.value_label.setObjectName("slider_value")
        header_layout.addWidget(self.value_label)

        layout.addLayout(header_layout)

        # 滑块
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("slider_control")
        self.slider.setRange(self._slider_min, self._slider_max)
        # 对于整数步进使用步进值本身，否则使用1
        if self._step >= 1:
            self.slider.setSingleStep(int(self._step))
            self.slider.setPageStep(int(self._step * 2))
        else:
            self.slider.setSingleStep(1)
            self.slider.setPageStep(max(1, int(0.1 * self._scale)))
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        # 描述文字（可选）
        if self._description:
            self.desc_label = QLabel(self._description)
            self.desc_label.setObjectName("slider_description")
            self.desc_label.setWordWrap(True)
            layout.addWidget(self.desc_label)

    def _apply_theme(self, theme_name: str = None):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 标签样式
        self.label_widget.setStyleSheet(f"""
            QLabel#slider_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                font-weight: 500;
                color: {palette.text_primary};
            }}
        """)

        # 数值显示样式
        self.value_label.setStyleSheet(f"""
            QLabel#slider_value {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {palette.accent_color};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
            }}
        """)

        # 滑块样式
        self.slider.setStyleSheet(f"""
            QSlider#slider_control {{
                height: {dp(24)}px;
            }}
            QSlider#slider_control::groove:horizontal {{
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                height: {dp(6)}px;
                border-radius: {dp(3)}px;
            }}
            QSlider#slider_control::handle:horizontal {{
                background-color: {palette.accent_color};
                border: 2px solid {palette.accent_color};
                width: {dp(16)}px;
                height: {dp(16)}px;
                margin: {dp(-6)}px 0;
                border-radius: {dp(8)}px;
            }}
            QSlider#slider_control::handle:horizontal:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
                border-color: {theme_manager.PRIMARY_LIGHT};
            }}
            QSlider#slider_control::sub-page:horizontal {{
                background-color: {palette.accent_color};
                border-radius: {dp(3)}px;
            }}
        """)

        # 描述文字样式
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"""
                QLabel#slider_description {{
                    font-family: {palette.ui_font};
                    font-size: {sp(11)}px;
                    color: {palette.text_tertiary};
                    padding-top: {dp(2)}px;
                }}
            """)

    def _on_slider_changed(self, slider_value: int):
        """滑块值变更处理"""
        # 转换为实际浮点值
        value = slider_value / self._scale
        self._update_value_display(value)
        self.value_changed.emit(value)

    def _update_value_display(self, value: float):
        """更新数值显示"""
        try:
            display_text = self._value_format.format(value)
        except (ValueError, KeyError):
            display_text = str(value)
        self.value_label.setText(display_text)

    def get_value(self) -> float:
        """获取当前值"""
        return self.slider.value() / self._scale

    def set_value(self, value: float, emit_signal: bool = True):
        """设置值

        Args:
            value: 浮点数值
            emit_signal: 是否发射 value_changed 信号（默认 True）
        """
        # 限制范围
        value = max(self._min_value, min(self._max_value, value))
        # 转换为滑块整数值
        slider_value = int(value * self._scale)

        if not emit_signal:
            # 阻止信号，避免循环触发
            self.slider.blockSignals(True)
            self.slider.setValue(slider_value)
            self.slider.blockSignals(False)
        else:
            self.slider.setValue(slider_value)

        self._update_value_display(value)

    def reset_to_default(self):
        """重置为默认值"""
        self.set_value(self._default_value)

    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)
        # 禁用时降低透明度
        opacity = "1.0" if enabled else "0.5"
        self.setStyleSheet(f"opacity: {opacity};")

    # 属性接口
    value = property(get_value, set_value)
