"""
Toast通知组件 - 禅意风格

现代化的非阻塞式通知系统，替代传统QMessageBox
符合2025年桌面UI最佳实践

特点：
- 非阻塞式通知
- 自动消失（可配置）
- 支持多种类型（成功、错误、警告、信息）
- 优雅的动画效果
- 可堆叠显示
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor
from themes.theme_manager import theme_manager


class Toast(QWidget):
    """单个Toast通知组件"""

    closed = pyqtSignal()

    def __init__(self, message, toast_type='info', duration=3000, parent=None):
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.message_label = None
        self.icon_label = None
        self.close_btn = None
        self._theme_connected = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setupUI()

        # 连接主题变化信号
        self._connect_theme_signal()

        # 自动关闭定时器
        if duration > 0:
            QTimer.singleShot(duration, self.fadeOut)

    def _connect_theme_signal(self):
        """连接主题信号"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._apply_theme)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._apply_theme)
            except TypeError:
                pass  # 信号可能已断开
            self._theme_connected = False

    def setupUI(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 图标
        self.icon_label = QLabel(self.getIcon())
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # 消息文本
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, stretch=1)

        # 关闭按钮（悬浮显示）
        self.close_btn = QLabel("×")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.close_btn.mousePressEvent = lambda e: self.fadeOut()
        layout.addWidget(self.close_btn)

        # 设置固定宽度和最小高度
        self.setFixedWidth(400)
        self.setMinimumHeight(60)

        # 初始透明度为0（用于淡入动画）
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

        # 应用主题
        self._apply_theme()

        # 调整大小以适应内容
        self.adjustSize()

    def _apply_theme(self):
        """应用主题样式"""
        # 根据类型获取颜色
        colors = self.getColors()
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        self.setStyleSheet(f"""
            Toast {{
                background-color: {colors['bg']};
                border: 2px solid {colors['border']};
                border-radius: {theme_manager.RADIUS_MD};
            }}
        """)

        # 重新设置透明度效果（因为shadow会覆盖）
        # 使用QGraphicsDropShadowEffect替代
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        # 注意：不能同时设置shadow和opacity_effect
        # self.setGraphicsEffect(shadow)

        if self.icon_label:
            self.icon_label.setStyleSheet(f"""
                font-size: 24px;
                color: {colors['icon']};
                background-color: transparent;
                padding: 8px;
            """)

        if self.message_label:
            self.message_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {theme_manager.FONT_SIZE_BASE};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {colors['text']};
                background-color: transparent;
            """)

        if self.close_btn:
            self.close_btn.setStyleSheet(f"""
                font-size: 20px;
                color: {colors['close']};
                background-color: transparent;
                border-radius: 12px;
                padding: 4px;
            """)

    def getColors(self):
        """根据类型获取颜色方案"""
        if self.toast_type == 'success':
            return {
                'bg': theme_manager.SUCCESS_BG,
                'border': theme_manager.SUCCESS,
                'icon': theme_manager.SUCCESS,
                'text': theme_manager.TEXT_PRIMARY,
                'close': theme_manager.SUCCESS
            }
        elif self.toast_type == 'error':
            return {
                'bg': theme_manager.ERROR_BG,
                'border': theme_manager.ERROR,
                'icon': theme_manager.ERROR,
                'text': theme_manager.TEXT_PRIMARY,
                'close': theme_manager.ERROR
            }
        elif self.toast_type == 'warning':
            return {
                'bg': theme_manager.WARNING_BG,
                'border': theme_manager.WARNING,
                'icon': theme_manager.WARNING,
                'text': theme_manager.TEXT_PRIMARY,
                'close': theme_manager.WARNING
            }
        else:  # info
            return {
                'bg': theme_manager.INFO_BG,
                'border': theme_manager.INFO,
                'icon': theme_manager.INFO,
                'text': theme_manager.TEXT_PRIMARY,
                'close': theme_manager.INFO
            }

    def getIcon(self):
        """根据类型获取图标"""
        icons = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': 'ℹ'
        }
        return icons.get(self.toast_type, 'ℹ')

    def show(self):
        """显示Toast（带淡入动画）"""
        super().show()
        self.fadeIn()

    def fadeIn(self):
        """淡入动画"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def fadeOut(self):
        """淡出动画"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(self.onFadeOutFinished)
        self.animation.start()

    def onFadeOutFinished(self):
        """淡出完成后关闭"""
        # 在删除前断开主题信号
        self._disconnect_theme_signal()
        self.closed.emit()
        self.close()
        self.deleteLater()


class ToastManager:
    """Toast管理器 - 管理多个Toast的显示位置"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.toasts = []
            cls._instance.spacing = 12
            cls._instance.margin_bottom = 80
            cls._instance.margin_right = 24
        return cls._instance

    def show(self, message, toast_type='info', duration=3000, parent=None):
        """显示Toast通知

        Args:
            message: 消息内容
            toast_type: 类型（success/error/warning/info）
            duration: 显示时长（毫秒），0表示不自动关闭
            parent: 父窗口（未使用，保持API兼容）
        """
        toast = Toast(message, toast_type, duration, None)  # 不设parent，作为独立窗口
        toast.closed.connect(lambda: self.removeToast(toast))

        # 添加到列表
        self.toasts.append(toast)

        # 先显示Toast（这样才能获取正确的尺寸）
        toast.show()

        # 然后计算位置
        self.updatePositions()

        return toast

    def removeToast(self, toast):
        """移除Toast"""
        if toast in self.toasts:
            self.toasts.remove(toast)
            self.updatePositions()

    def updatePositions(self):
        """更新所有Toast的位置（右下角堆叠）"""
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()  # 使用可用区域，避开任务栏

        y_offset = screen_geo.bottom() - self.margin_bottom

        for toast in reversed(self.toasts):
            # 确保获取正确的尺寸
            toast_width = toast.width() if toast.width() > 0 else 400
            toast_height = toast.height() if toast.height() > 0 else 60

            x = screen_geo.right() - toast_width - self.margin_right
            y = y_offset - toast_height

            toast.move(x, y)

            # 为下一个Toast留出空间
            y_offset = y - self.spacing

    def success(self, message, duration=3000, parent=None):
        """显示成功提示"""
        return self.show(message, 'success', duration, parent)

    def error(self, message, duration=4000, parent=None):
        """显示错误提示"""
        return self.show(message, 'error', duration, parent)

    def warning(self, message, duration=3500, parent=None):
        """显示警告提示"""
        return self.show(message, 'warning', duration, parent)

    def info(self, message, duration=3000, parent=None):
        """显示信息提示"""
        return self.show(message, 'info', duration, parent)


# 全局Toast实例
toast = ToastManager()
