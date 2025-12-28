"""
开关输入组件

提供iOS风格的开关控件，支持标签和描述文字。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class SwitchControl(QWidget):
    """iOS风格开关控件

    自定义绘制的开关，支持动画过渡。
    """

    toggled = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None, checked: bool = False):
        super().__init__(parent)
        self._checked = checked
        self._handle_position = 1.0 if checked else 0.0
        self._animation = None

        # 固定尺寸
        self.setFixedSize(dp(44), dp(24))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool):
        if self._checked != value:
            self._checked = value
            self._animate_toggle()
            self.toggled.emit(value)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        """设置选中状态（不发射信号）"""
        if self._checked != checked:
            self._checked = checked
            self._handle_position = 1.0 if checked else 0.0
            self.update()

    def toggle(self):
        """切换状态"""
        self.checked = not self._checked

    def _animate_toggle(self):
        """动画切换"""
        self._animation = QPropertyAnimation(self, b"handle_position")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setStartValue(self._handle_position)
        self._animation.setEndValue(1.0 if self._checked else 0.0)
        self._animation.start()

    def get_handle_position(self) -> float:
        return self._handle_position

    def set_handle_position(self, value: float):
        self._handle_position = value
        self.update()

    # 使用pyqtProperty定义属性用于动画
    handle_position = pyqtProperty(float, get_handle_position, set_handle_position)

    def mousePressEvent(self, event):
        """鼠标点击切换"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.checked = not self._checked

    def paintEvent(self, event):
        """绘制开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取主题颜色
        if self._checked:
            track_color = QColor(theme_manager.PRIMARY)
        else:
            track_color = QColor(theme_manager.BG_TERTIARY)

        handle_color = QColor("#FFFFFF")
        border_color = QColor(theme_manager.BORDER_DEFAULT)

        # 绘制轨道
        track_rect = self.rect().adjusted(1, 1, -1, -1)
        track_radius = track_rect.height() / 2

        # 轨道路径
        track_path = QPainterPath()
        track_path.addRoundedRect(
            float(track_rect.x()),
            float(track_rect.y()),
            float(track_rect.width()),
            float(track_rect.height()),
            track_radius,
            track_radius
        )

        # 填充轨道
        painter.fillPath(track_path, track_color)

        # 绘制边框
        if not self._checked:
            painter.setPen(border_color)
            painter.drawPath(track_path)

        # 计算手柄位置
        handle_margin = dp(2)
        handle_size = track_rect.height() - 2 * handle_margin
        handle_x = track_rect.x() + handle_margin + self._handle_position * (
            track_rect.width() - handle_size - 2 * handle_margin
        )
        handle_y = track_rect.y() + handle_margin

        # 绘制手柄
        handle_path = QPainterPath()
        handle_path.addEllipse(
            float(handle_x),
            float(handle_y),
            float(handle_size),
            float(handle_size)
        )

        # 手柄阴影
        shadow_color = QColor(0, 0, 0, 40)
        shadow_path = QPainterPath()
        shadow_path.addEllipse(
            float(handle_x),
            float(handle_y + 1),
            float(handle_size),
            float(handle_size)
        )
        painter.fillPath(shadow_path, shadow_color)

        # 填充手柄
        painter.fillPath(handle_path, handle_color)


class SwitchWidget(QWidget):
    """开关输入组件

    布局：
    ┌────────────────────────────────────────┐
    │ 启用透明效果                    [═●]   │
    │ 开启后侧边栏将显示半透明效果            │
    └────────────────────────────────────────┘

    - 标签显示名称
    - iOS风格开关
    - 可选描述文字
    """

    # 值变更信号
    toggled = pyqtSignal(bool)

    def __init__(
        self,
        label: str,
        default: bool = False,
        description: str = "",
        parent: Optional[QWidget] = None
    ):
        """初始化开关输入组件

        Args:
            label: 标签文字
            default: 默认值
            description: 描述文字（可选）
            parent: 父组件
        """
        super().__init__(parent)

        self._label = label
        self._default = default
        self._description = description

        self._create_ui()
        self._apply_theme()

        # 设置默认值
        self.switch.setChecked(default)

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        # 标签行：标签 + 开关
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label_widget = QLabel(self._label)
        self.label_widget.setObjectName("switch_label")
        header_layout.addWidget(self.label_widget)

        header_layout.addStretch()

        self.switch = SwitchControl(checked=self._default)
        self.switch.toggled.connect(self._on_toggled)
        header_layout.addWidget(self.switch)

        layout.addLayout(header_layout)

        # 描述文字（可选）
        if self._description:
            self.desc_label = QLabel(self._description)
            self.desc_label.setObjectName("switch_description")
            self.desc_label.setWordWrap(True)
            layout.addWidget(self.desc_label)

    def _apply_theme(self, theme_name: str = None):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 标签样式
        self.label_widget.setStyleSheet(f"""
            QLabel#switch_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                font-weight: 500;
                color: {palette.text_primary};
            }}
        """)

        # 描述文字样式
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"""
                QLabel#switch_description {{
                    font-family: {palette.ui_font};
                    font-size: {sp(11)}px;
                    color: {palette.text_tertiary};
                    padding-top: {dp(2)}px;
                }}
            """)

        # 开关控件会在绘制时使用主题颜色
        self.switch.update()

    def _on_toggled(self, checked: bool):
        """开关切换处理"""
        self.toggled.emit(checked)

    def isChecked(self) -> bool:
        """获取当前状态"""
        return self.switch.isChecked()

    def setChecked(self, checked: bool):
        """设置状态（不发射信号）"""
        self.switch.setChecked(checked)

    def reset_to_default(self):
        """重置为默认值"""
        self.switch.setChecked(self._default)

    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        super().setEnabled(enabled)
        self.switch.setEnabled(enabled)
        # 禁用时降低透明度
        opacity = "1.0" if enabled else "0.5"
        self.setStyleSheet(f"opacity: {opacity};")

    # 属性接口
    checked = property(isChecked, setChecked)
