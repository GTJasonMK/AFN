"""
主题切换过渡动画组件

提供平滑的主题切换过渡效果，遮盖样式更新时的闪烁和卡顿。
"""

import logging
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QTimer, QParallelAnimationGroup
)
from PyQt6.QtGui import QPainter, QColor

logger = logging.getLogger(__name__)


class ThemeTransitionOverlay(QWidget):
    """主题切换过渡覆盖层

    在主题切换时显示一个渐变遮罩，遮盖样式更新过程。

    使用方法：
        overlay = ThemeTransitionOverlay(main_window)
        overlay.start_transition(on_complete=lambda: theme_manager.switch_theme())
    """

    # 过渡完成信号
    transition_complete = pyqtSignal()

    # 动画时长（毫秒）
    FADE_IN_DURATION = 150   # 淡入（遮盖）
    FADE_OUT_DURATION = 200  # 淡出（显示新主题）
    HOLD_DURATION = 50       # 中间保持时间

    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置覆盖层属性
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # 初始状态：不可见
        self._opacity = 0.0
        self._target_color = QColor(0, 0, 0)  # 默认黑色遮罩

        # 创建透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        # 动画
        self._fade_in_anim = None
        self._fade_out_anim = None

        # 回调
        self._on_hidden_callback = None
        self._on_shown_callback = None

        # 隐藏
        self.hide()

    def set_transition_color(self, is_to_dark: bool):
        """设置过渡颜色

        Args:
            is_to_dark: 是否切换到深色主题
        """
        from themes.theme_manager.themes import DarkTheme, LightTheme
        if is_to_dark:
            # 切换到深色：使用目标主题的背景色
            self._target_color = QColor(DarkTheme.BG_PRIMARY)
        else:
            # 切换到浅色：使用目标主题的背景色
            self._target_color = QColor(LightTheme.BG_PRIMARY)

    def paintEvent(self, event):
        """绘制遮罩层"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._target_color)

    def start_transition(self, on_hidden=None, on_shown=None):
        """开始过渡动画

        Args:
            on_hidden: 覆盖层完全显示后的回调（此时执行主题切换）
            on_shown: 过渡完成后的回调
        """
        self._on_hidden_callback = on_hidden
        self._on_shown_callback = on_shown

        # 确保覆盖整个父窗口
        if self.parent():
            self.setGeometry(self.parent().rect())

        # 显示并开始淡入动画
        self.show()
        self.raise_()
        self._start_fade_in()

    def _start_fade_in(self):
        """开始淡入动画（显示遮罩）"""
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_anim.setDuration(self.FADE_IN_DURATION)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade_in_anim.finished.connect(self._on_fade_in_complete)
        self._fade_in_anim.start()

    def _on_fade_in_complete(self):
        """淡入完成（遮罩完全显示）"""
        # 执行主题切换回调
        if self._on_hidden_callback:
            try:
                self._on_hidden_callback()
            except Exception as e:
                logger.error(f"主题切换回调执行失败: {e}")

        # 短暂保持，让样式有时间应用
        QTimer.singleShot(self.HOLD_DURATION, self._start_fade_out)

    def _start_fade_out(self):
        """开始淡出动画（显示新主题）"""
        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(self.FADE_OUT_DURATION)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_out_anim.finished.connect(self._on_fade_out_complete)
        self._fade_out_anim.start()

    def _on_fade_out_complete(self):
        """淡出完成（过渡结束）"""
        self.hide()

        # 执行完成回调
        if self._on_shown_callback:
            try:
                self._on_shown_callback()
            except Exception as e:
                logger.error(f"过渡完成回调执行失败: {e}")

        # 发射完成信号
        self.transition_complete.emit()

    def cancel(self):
        """取消过渡动画"""
        if self._fade_in_anim and self._fade_in_anim.state() == QPropertyAnimation.State.Running:
            self._fade_in_anim.stop()
        if self._fade_out_anim and self._fade_out_anim.state() == QPropertyAnimation.State.Running:
            self._fade_out_anim.stop()
        self.hide()
        self._opacity_effect.setOpacity(0.0)


class ThemeSwitchHelper:
    """主题切换辅助类

    封装主题切换的完整流程，包括：
    1. 禁用窗口更新（减少重绘）
    2. 显示过渡动画
    3. 执行主题切换
    4. 恢复窗口更新
    5. 隐藏过渡动画

    使用方法：
        helper = ThemeSwitchHelper(main_window)
        helper.switch_theme()  # 切换到另一个主题
        helper.switch_theme(to_dark=True)  # 切换到深色主题
    """

    def __init__(self, window: QWidget):
        """初始化

        Args:
            window: 主窗口实例
        """
        self._window = window
        self._overlay = ThemeTransitionOverlay(window)
        self._is_switching = False

    @property
    def is_switching(self) -> bool:
        """是否正在切换主题"""
        return self._is_switching

    def switch_theme(self, to_dark: bool = None):
        """切换主题（带过渡动画）

        Args:
            to_dark: 是否切换到深色主题。None表示切换到另一个主题。
        """
        if self._is_switching:
            logger.warning("主题切换正在进行中，忽略重复请求")
            return

        from themes.theme_manager import theme_manager
        from themes.theme_manager.themes import ThemeMode

        # 确定目标主题
        if to_dark is None:
            to_dark = not theme_manager.is_dark_mode()

        self._is_switching = True

        # 设置过渡颜色
        self._overlay.set_transition_color(to_dark)

        def do_switch():
            """执行实际的主题切换"""
            # 禁用窗口更新
            self._window.setUpdatesEnabled(False)

            try:
                # 切换主题
                target_mode = ThemeMode.DARK if to_dark else ThemeMode.LIGHT
                theme_manager.switch_theme(target_mode)
            finally:
                # 恢复窗口更新
                self._window.setUpdatesEnabled(True)

        def on_complete():
            """过渡完成"""
            self._is_switching = False

        # 开始过渡
        self._overlay.start_transition(
            on_hidden=do_switch,
            on_shown=on_complete
        )

    def cleanup(self):
        """清理资源"""
        self._overlay.cancel()
        self._overlay.deleteLater()
