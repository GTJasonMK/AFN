"""
加载动画组件

提供多种样式的加载动画和加载状态管理：
- CircularSpinner: 圆形旋转动画
- DotsSpinner: 点状跳动动画
- LoadingOverlay: 全屏遮罩层
- InlineLoadingState: 内联加载状态（用于小区域）
- SkeletonLoader: 骨架屏占位
- ListLoadingState: 列表加载骨架
- LoadingStateManager: 上下文管理器（确保加载状态正确关闭）
"""

from contextlib import contextmanager
from typing import Optional, Callable, Any
import logging

from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QLinearGradient

from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes.transparency_tokens import OpacityTokens

logger = logging.getLogger(__name__)


class CircularSpinner(ThemeAwareWidget):
    """圆形旋转加载动画

    Material Design风格的圆形进度指示器
    """

    def __init__(self, size=40, color=None, parent=None, auto_start=True):
        self.size = size
        self._custom_color = color  # 自定义颜色（可选）
        self._auto_start = auto_start  # 是否自动启动动画
        self.angle = 0
        self.timer = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedSize(self.size, self.size)

        # 使用QTimer实现动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        # 仅当 auto_start=True 时自动启动
        if self._auto_start:
            self.timer.start(16)  # 约60 FPS

    def _apply_theme(self):
        """应用主题样式（重绘时使用主题色）"""
        self.update()

    def _rotate(self):
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
        if self.timer:
            self.timer.stop()

    def start(self):
        """启动动画"""
        if self.timer and not self.timer.isActive():
            self.timer.start(16)

    def cleanup(self):
        """清理资源"""
        self.stop()
        super().cleanup()


class DotsSpinner(ThemeAwareWidget):
    """点状加载动画

    三个点依次跳动的动画效果
    """

    def __init__(self, color=None, parent=None):
        self._custom_color = color  # 自定义颜色（可选）
        self.step = 0
        self.timer = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedSize(60, 20)

        # 动画定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(200)  # 每200ms切换一次

    def _apply_theme(self):
        """应用主题样式（重绘时使用主题色）"""
        self.update()

    def _animate(self):
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
        if self.timer:
            self.timer.stop()

    def start(self):
        """启动动画"""
        if self.timer and not self.timer.isActive():
            self.timer.start(200)

    def cleanup(self):
        """清理资源"""
        self.stop()
        super().cleanup()


class LoadingOverlay(ThemeAwareWidget):
    """全屏半透明加载遮罩

    覆盖在内容上方，显示加载动画和提示文字。
    支持淡入淡出动画效果。

    使用方式：
        # 作为父组件的覆盖层
        self.loading_overlay = LoadingOverlay(parent=self)
        self.loading_overlay.show_with_animation()  # 显示
        self.loading_overlay.hide_with_animation()  # 隐藏
    """

    def __init__(self, text="加载中...", spinner_type="circular", parent=None, translucent=True):
        """初始化加载遮罩

        Args:
            text: 显示的文字
            spinner_type: 动画类型 "circular" 或 "dots"
            parent: 父组件
            translucent: 是否使用半透明背景
        """
        self.text = text
        self.spinner_type = spinner_type
        self.translucent = translucent
        self.spinner = None
        self.label = None
        self._fade_animation = None
        self._opacity_effect = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # 创建加载动画（不自动启动，等show时再启动）
        if self.spinner_type == "circular":
            self.spinner = CircularSpinner(size=48, auto_start=False)
        else:
            self.spinner = DotsSpinner()
            self.spinner.stop()  # 先停止

        spinner_container = QHBoxLayout()
        spinner_container.addStretch()
        spinner_container.addWidget(self.spinner)
        spinner_container.addStretch()
        layout.addLayout(spinner_container)

        # 加载文字
        self.label = QLabel(self.text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # 设置透明度效果（用于淡入淡出动画）
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self._opacity_effect)

        # 创建淡入淡出动画
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(200)  # 200ms
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 初始隐藏
        self.hide()

    def _apply_theme(self):
        """应用主题样式 - 使用透明度Token系统"""
        ui_font = theme_manager.ui_font()

        if self.translucent:
            # 使用Token系统获取加载层透明度
            # 如果透明效果全局启用，使用配置的透明度；否则使用Token默认值
            if theme_manager.is_transparency_globally_enabled():
                opacity = theme_manager.get_component_opacity("loading")
            else:
                opacity = OpacityTokens.LOADING

            if theme_manager.is_dark_mode():
                bg_color = f"rgba(0, 0, 0, {opacity})"
            else:
                bg_color = f"rgba(255, 255, 255, {opacity})"
        else:
            bg_color = theme_manager.BG_PRIMARY

        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        self.setStyleSheet(f"""
            background-color: {bg_color};
        """)

        # 更新文字样式
        if self.label:
            self.label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: 15px;
                color: {theme_manager.TEXT_SECONDARY};
                font-weight: 500;
            """)

    def setText(self, text):
        """更新显示文字"""
        self.text = text
        if self.label:
            self.label.setText(text)

    def show_with_animation(self, text=None):
        """带淡入动画显示遮罩

        Args:
            text: 可选，更新显示的文字
        """
        if text:
            self.setText(text)

        # 调整大小以覆盖父组件
        if self.parent():
            self.setGeometry(self.parent().rect())
            self.raise_()  # 确保在最上层

        super().show()

        # 启动动画
        if self.spinner:
            self.spinner.start()

        # 淡入动画
        if self._fade_animation:
            self._fade_animation.stop()
            # 断开可能存在的淡出完成回调，防止淡入完成后错误触发隐藏
            try:
                self._fade_animation.finished.disconnect(self._on_fade_out_finished)
            except TypeError:
                pass  # 未连接时忽略
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.start()

    def hide_with_animation(self):
        """带淡出动画隐藏遮罩"""
        if self._fade_animation:
            self._fade_animation.stop()
            self._fade_animation.setStartValue(1.0)
            self._fade_animation.setEndValue(0.0)
            # 动画结束后隐藏
            self._fade_animation.finished.connect(self._on_fade_out_finished)
            self._fade_animation.start()
        else:
            self.hide()

    def _on_fade_out_finished(self):
        """淡出动画完成"""
        # 断开信号避免重复调用
        try:
            self._fade_animation.finished.disconnect(self._on_fade_out_finished)
        except TypeError:
            pass
        self.hide()
        if self.spinner:
            self.spinner.stop()

    def show(self):
        """显示遮罩（无动画）"""
        # 调整大小以覆盖父组件
        if self.parent():
            self.setGeometry(self.parent().rect())
            self.raise_()

        if self._opacity_effect:
            self._opacity_effect.setOpacity(1.0)

        super().show()
        if self.spinner:
            self.spinner.start()

    def hide(self):
        """隐藏遮罩（无动画）"""
        if self.spinner:
            self.spinner.stop()
        super().hide()

    def resizeEvent(self, event):
        """父组件大小改变时调整自身大小"""
        super().resizeEvent(event)
        if self.parent() and self.isVisible():
            self.setGeometry(self.parent().rect())

    def cleanup(self):
        """清理资源"""
        if self._fade_animation:
            self._fade_animation.stop()
        if self.spinner:
            self.spinner.cleanup()
        super().cleanup()


class InlineLoadingState(ThemeAwareWidget):
    """内联加载状态组件

    用于按钮旁边、列表项内等小区域的加载指示。
    可选显示文字，支持水平/垂直布局。

    使用方式：
        loading = InlineLoadingState(text="加载中")
        layout.addWidget(loading)
        # 显示
        loading.show()
        # 隐藏
        loading.hide()
    """

    def __init__(
        self,
        text: str = "",
        spinner_size: int = 16,
        orientation: str = "horizontal",
        parent=None
    ):
        """初始化

        Args:
            text: 显示文字（可选）
            spinner_size: spinner尺寸
            orientation: 布局方向 "horizontal" 或 "vertical"
            parent: 父组件
        """
        self._text = text
        self._spinner_size = spinner_size
        self._orientation = orientation
        self._spinner: Optional[CircularSpinner] = None
        self._label: Optional[QLabel] = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI"""
        if self._orientation == "vertical":
            layout = QVBoxLayout(self)
        else:
            layout = QHBoxLayout(self)

        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spinner
        self._spinner = CircularSpinner(
            size=self._spinner_size,
            auto_start=False
        )
        layout.addWidget(self._spinner)

        # 文字（可选）
        if self._text:
            self._label = QLabel(self._text)
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._label)

    def _apply_theme(self):
        """应用主题"""
        if self._label:
            self._label.setStyleSheet(f"""
                font-size: 12px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

    def setText(self, text: str):
        """更新文字"""
        self._text = text
        if self._label:
            self._label.setText(text)

    def show(self):
        """显示并启动动画"""
        super().show()
        if self._spinner:
            self._spinner.start()

    def hide(self):
        """隐藏并停止动画"""
        if self._spinner:
            self._spinner.stop()
        super().hide()

    def cleanup(self):
        """清理"""
        if self._spinner:
            self._spinner.cleanup()
        super().cleanup()


class SkeletonLoader(ThemeAwareWidget):
    """骨架屏加载组件

    用于内容加载时的占位显示，带有shimmer动画效果。

    使用方式：
        skeleton = SkeletonLoader(width=200, height=20)
        layout.addWidget(skeleton)
    """

    def __init__(
        self,
        width: int = 100,
        height: int = 16,
        radius: int = 4,
        animate: bool = True,
        parent=None
    ):
        """初始化

        Args:
            width: 宽度
            height: 高度
            radius: 圆角半径
            animate: 是否启用shimmer动画
            parent: 父组件
        """
        self._skeleton_width = width
        self._skeleton_height = height
        self._radius = radius
        self._animate = animate
        self._shimmer_offset = 0
        self._timer: Optional[QTimer] = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI"""
        self.setFixedSize(self._skeleton_width, self._skeleton_height)

        if self._animate:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._update_shimmer)
            self._timer.start(50)  # 20 FPS

    def _apply_theme(self):
        """应用主题"""
        self.update()

    def _update_shimmer(self):
        """更新shimmer动画"""
        self._shimmer_offset = (self._shimmer_offset + 10) % (self._skeleton_width * 2)
        self.update()

    def paintEvent(self, event):
        """绘制骨架"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 基础颜色
        if theme_manager.is_dark_mode():
            base_color = QColor(60, 60, 60)
            shimmer_color = QColor(80, 80, 80)
        else:
            base_color = QColor(230, 230, 230)
            shimmer_color = QColor(245, 245, 245)

        # 绘制圆角矩形
        rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)

        if self._animate:
            # 创建shimmer渐变
            gradient = QLinearGradient(
                self._shimmer_offset - self._skeleton_width, 0,
                self._shimmer_offset, 0
            )
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(0.5, shimmer_color)
            gradient.setColorAt(1, base_color)
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(base_color)

        painter.drawRoundedRect(rect, self._radius, self._radius)

    def stop(self):
        """停止动画"""
        if self._timer:
            self._timer.stop()

    def start(self):
        """启动动画"""
        if self._timer and not self._timer.isActive():
            self._timer.start(50)

    def cleanup(self):
        """清理"""
        self.stop()
        super().cleanup()


class ListLoadingState(ThemeAwareWidget):
    """列表加载状态组件

    显示多行骨架屏，用于列表/卡片加载时的占位。

    使用方式：
        loading = ListLoadingState(row_count=5, row_height=60)
        layout.addWidget(loading)
    """

    def __init__(
        self,
        row_count: int = 5,
        row_height: int = 48,
        spacing: int = 8,
        show_avatar: bool = False,
        parent=None
    ):
        """初始化

        Args:
            row_count: 行数
            row_height: 每行高度
            spacing: 行间距
            show_avatar: 是否显示头像占位
            parent: 父组件
        """
        self._row_count = row_count
        self._row_height = row_height
        self._spacing = spacing
        self._show_avatar = show_avatar
        self._skeletons: list = []
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(self._spacing)

        for i in range(self._row_count):
            row = self._create_skeleton_row()
            layout.addWidget(row)
            self._skeletons.append(row)

        layout.addStretch()

    def _create_skeleton_row(self) -> QWidget:
        """创建一行骨架"""
        row = QWidget()
        row.setFixedHeight(self._row_height)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        if self._show_avatar:
            # 头像占位
            avatar = SkeletonLoader(
                width=self._row_height - 8,
                height=self._row_height - 8,
                radius=(self._row_height - 8) // 2
            )
            layout.addWidget(avatar)

        # 内容区域
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(8)

        # 标题行
        title = SkeletonLoader(width=180, height=16, radius=4)
        content_layout.addWidget(title)

        # 描述行（较短）
        if self._row_height > 40:
            desc = SkeletonLoader(width=120, height=12, radius=3)
            content_layout.addWidget(desc)

        content_layout.addStretch()
        layout.addWidget(content, 1)

        return row

    def _apply_theme(self):
        """应用主题"""
        pass

    def stop(self):
        """停止所有动画"""
        for row in self._skeletons:
            for skeleton in row.findChildren(SkeletonLoader):
                skeleton.stop()

    def start(self):
        """启动所有动画"""
        for row in self._skeletons:
            for skeleton in row.findChildren(SkeletonLoader):
                skeleton.start()

    def cleanup(self):
        """清理"""
        self.stop()
        super().cleanup()


class LoadingStateManager:
    """加载状态管理器

    使用上下文管理器模式，确保加载状态在操作完成后正确关闭。
    支持异常情况下也能正确关闭加载状态。

    使用方式1 - 装饰器模式：
        @LoadingStateManager.with_loading(widget, "保存中...")
        def save_data():
            ...

    使用方式2 - 上下文管理器：
        with LoadingStateManager(widget, "加载中..."):
            await load_data()

    使用方式3 - 手动管理：
        manager = LoadingStateManager(widget)
        manager.start("处理中...")
        try:
            ...
        finally:
            manager.stop()
    """

    def __init__(
        self,
        widget: QWidget,
        text: str = "加载中...",
        overlay: Optional[LoadingOverlay] = None
    ):
        """初始化

        Args:
            widget: 要显示加载状态的组件
            text: 加载提示文字
            overlay: 可选，已有的LoadingOverlay实例
        """
        self._widget = widget
        self._text = text
        self._overlay = overlay
        self._created_overlay = False

    def _ensure_overlay(self):
        """确保overlay存在"""
        if self._overlay is None:
            self._overlay = LoadingOverlay(
                text=self._text,
                parent=self._widget
            )
            self._created_overlay = True

    def start(self, text: Optional[str] = None):
        """开始加载状态"""
        self._ensure_overlay()
        if self._overlay:
            self._overlay.show_with_animation(text or self._text)

    def stop(self):
        """停止加载状态"""
        if self._overlay:
            self._overlay.hide_with_animation()

    def update_text(self, text: str):
        """更新加载文字"""
        if self._overlay:
            self._overlay.setText(text)

    def __enter__(self):
        """进入上下文"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文（无论是否异常都关闭加载状态）"""
        self.stop()
        return False  # 不抑制异常

    def cleanup(self):
        """清理资源"""
        if self._created_overlay and self._overlay:
            self._overlay.cleanup()
            self._overlay = None

    @staticmethod
    def with_loading(
        widget: QWidget,
        text: str = "加载中...",
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """装饰器模式

        Args:
            widget: 显示加载状态的组件
            text: 加载文字
            on_error: 错误处理回调

        Returns:
            装饰器函数
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                manager = LoadingStateManager(widget, text)
                manager.start()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    if on_error:
                        on_error(e)
                    else:
                        logger.error("操作失败: %s", e)
                    raise
                finally:
                    # 使用QTimer延迟关闭，确保UI更新
                    QTimer.singleShot(100, manager.stop)
            return wrapper
        return decorator


@contextmanager
def loading_context(
    widget: QWidget,
    text: str = "加载中...",
    overlay: Optional[LoadingOverlay] = None
):
    """加载状态上下文管理器（函数版本）

    使用方式：
        with loading_context(self, "保存中..."):
            do_something()

    Args:
        widget: 显示加载状态的组件
        text: 加载文字
        overlay: 可选的已有overlay

    Yields:
        LoadingStateManager实例
    """
    manager = LoadingStateManager(widget, text, overlay)
    try:
        manager.start()
        yield manager
    finally:
        manager.stop()
