"""
加载动画组件

提供多种样式的加载动画
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager


class CircularSpinner(ThemeAwareWidget):
    """圆形旋转加载动画

    Material Design风格的圆形进度指示器
    """

    def __init__(self, size=40, color=None, parent=None):
        super().__init__(parent)
        self.size = size
        self._custom_color = color  # 自定义颜色（可选）
        self.angle = 0

        self.setFixedSize(size, size)

        # 使用QTimer实现动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(16)  # 约60 FPS

    def update_theme(self):
        """主题更新时重新绘制"""
        self.update()

    def rotate(self):
        """旋转动画"""
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        """绘制旋转的圆弧"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 设置画笔颜色（使用自定义颜色或主题色）
        color = QColor(self._custom_color) if self._custom_color else QColor(theme_manager.PRIMARY)
        pen = QPen(color)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # 绘制旋转的圆弧
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawArc(rect, self.angle * 16, 270 * 16)

    def stop(self):
        """停止动画"""
        self.timer.stop()

    def start(self):
        """启动动画"""
        if not self.timer.isActive():
            self.timer.start(16)


class DotsSpinner(ThemeAwareWidget):
    """点状加载动画

    三个点依次跳动的动画效果
    """

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._custom_color = color  # 自定义颜色（可选）
        self.step = 0

        self.setFixedSize(60, 20)

        # 动画定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(200)  # 每200ms切换一次

    def update_theme(self):
        """主题更新时重新绘制"""
        self.update()

    def animate(self):
        """切换动画状态"""
        self.step = (self.step + 1) % 4
        self.update()

    def paintEvent(self, event):
        """绘制三个点"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 使用自定义颜色或主题色
        base_color = QColor(self._custom_color) if self._custom_color else QColor(theme_manager.PRIMARY)

        dot_radius = 4
        spacing = 15
        y_offset = 10

        for i in range(3):
            # 根据步骤调整Y位置和透明度
            if self.step == i + 1:
                y = y_offset - 3
                alpha = 255
            else:
                y = y_offset
                alpha = 100

            color = QColor(base_color)
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            x = 10 + i * spacing
            painter.drawEllipse(x - dot_radius, y - dot_radius,
                              dot_radius * 2, dot_radius * 2)

    def stop(self):
        """停止动画"""
        self.timer.stop()

    def start(self):
        """启动动画"""
        if not self.timer.isActive():
            self.timer.start(200)


class LoadingOverlay(ThemeAwareWidget):
    """全屏半透明加载遮罩

    覆盖在内容上方，显示加载动画和提示文字
    """

    def __init__(self, text="加载中...", spinner_type="circular", parent=None):
        super().__init__(parent)
        self.text = text
        self.spinner_type = spinner_type
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        # 应用主题样式
        self._apply_theme()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # 创建加载动画
        if self.spinner_type == "circular":
            self.spinner = CircularSpinner(size=48)
        else:
            self.spinner = DotsSpinner()

        spinner_container = QHBoxLayout()
        spinner_container.addStretch()
        spinner_container.addWidget(self.spinner)
        spinner_container.addStretch()
        layout.addLayout(spinner_container)

        # 加载文字
        self.label = QLabel(self.text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def update_theme(self):
        """主题更新"""
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        # 使用主题背景色
        bg_color = theme_manager.BG_PRIMARY

        self.setStyleSheet(f"""
            LoadingOverlay {{
                background-color: {bg_color};
            }}
        """)

        # 更新文字样式
        if hasattr(self, 'label'):
            self.label.setStyleSheet(f"""
                font-size: 15px;
                color: {theme_manager.TEXT_SECONDARY};
                font-weight: 500;
            """)

    def setText(self, text):
        """更新显示文字"""
        self.label.setText(text)

    def show(self):
        """显示遮罩"""
        super().show()
        self.spinner.start()

    def hide(self):
        """隐藏遮罩"""
        self.spinner.stop()
        super().hide()


class InlineSpinner(ThemeAwareWidget):
    """内联加载动画

    用于按钮或行内显示的小型加载指示器
    """

    def __init__(self, text="处理中...", size=16, parent=None):
        super().__init__(parent)
        self.text = text
        self.size = size
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 小型spinner（使用次要文字颜色）
        self.spinner = CircularSpinner(size=self.size)
        layout.addWidget(self.spinner)

        # 文字
        self.label = QLabel(self.text)
        layout.addWidget(self.label)

        # 应用主题
        self._apply_theme()

    def update_theme(self):
        """主题更新"""
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        if hasattr(self, 'label'):
            self.label.setStyleSheet(f"""
                font-size: 13px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

    def setText(self, text):
        """更新文字"""
        self.label.setText(text)

    def show(self):
        """显示"""
        super().show()
        self.spinner.start()

    def hide(self):
        """隐藏"""
        self.spinner.stop()
        super().hide()
