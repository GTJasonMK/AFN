"""
统一主题配置设置Widget

支持两种编辑模式：
- V1（经典模式）：面向常量的配置编辑
- V2（组件模式）：面向组件的配置编辑

布局：
+------------------------------------------------------------------+
| [经典模式] [组件模式]                              模式切换按钮    |
+------------------------------------------------------------------+
|                                                                  |
|              对应模式的编辑器内容                                  |
|                                                                  |
+------------------------------------------------------------------+
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
    QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, QTimer

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .widget import ThemeSettingsWidget
from .v2_editor_widget import V2ThemeEditorWidget

logger = logging.getLogger(__name__)


class UnifiedThemeSettingsWidget(QWidget):
    """统一主题配置设置Widget

    提供V1（经典模式）和V2（组件模式）两种编辑界面的切换。
    默认使用V2组件模式，用户可以切换到V1经典模式以访问旧的配置方式。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 状态 - 初始设为None，让_switch_mode正确执行
        self._current_mode = None
        self._is_destroyed = False  # 标记widget是否正在销毁

        # 刷新定时器（可取消）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._do_delayed_refresh)
        self._pending_refresh_widget = None  # 待刷新的widget

        # 子Widget（延迟创建）
        self._v1_widget: Optional[ThemeSettingsWidget] = None
        self._v2_widget: Optional[V2ThemeEditorWidget] = None

        self._create_ui()
        self._apply_theme()

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def closeEvent(self, event):
        """关闭事件：清理子widget"""
        self._cleanup_all()
        super().closeEvent(event)

    def _cleanup_all(self):
        """清理所有资源"""
        self._is_destroyed = True

        # 停止待处理的刷新定时器
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self._pending_refresh_widget = None

        # 清理子widget
        self._cleanup_child_widgets()

    def _cleanup_child_widgets(self):
        """清理子widget的异步工作线程"""
        if self._v1_widget is not None:
            if hasattr(self._v1_widget, '_cleanup_worker'):
                self._v1_widget._cleanup_worker()
        if self._v2_widget is not None:
            if hasattr(self._v2_widget, '_cleanup_worker'):
                self._v2_widget._cleanup_worker()

    def _do_delayed_refresh(self):
        """执行延迟刷新（定时器回调）"""
        if self._is_destroyed:
            return
        if self._pending_refresh_widget is not None:
            try:
                self._pending_refresh_widget.refresh()
            except RuntimeError:
                pass  # widget可能已被删除
            self._pending_refresh_widget = None

    def _create_ui(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部模式切换栏
        mode_bar = self._create_mode_bar()
        main_layout.addWidget(mode_bar)

        # 内容区域（堆叠）
        self.stack = QStackedWidget()
        self.stack.setObjectName("theme_editor_stack")

        # 添加占位符，延迟创建实际widget
        self._v2_placeholder = QWidget()
        self._v1_placeholder = QWidget()
        self.stack.addWidget(self._v2_placeholder)  # index 0 = V2
        self.stack.addWidget(self._v1_placeholder)  # index 1 = V1

        main_layout.addWidget(self.stack, stretch=1)

        # 默认显示V2模式
        self._switch_mode("v2")

    def _create_mode_bar(self) -> QWidget:
        """创建模式切换栏"""
        bar = QFrame()
        bar.setObjectName("mode_bar")
        bar.setFixedHeight(dp(48))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(dp(16), dp(8), dp(16), dp(8))
        layout.setSpacing(dp(8))

        # 模式说明标签
        mode_label = QLabel("编辑模式：")
        mode_label.setObjectName("mode_label")
        layout.addWidget(mode_label)

        # V2（组件模式）按钮 - 默认选中
        self.v2_btn = QPushButton("组件模式")
        self.v2_btn.setObjectName("mode_btn")
        self.v2_btn.setCheckable(True)
        self.v2_btn.setChecked(True)
        self.v2_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.v2_btn.setToolTip("面向组件的配置，直接编辑按钮、卡片、侧边栏等组件的样式")
        self.v2_btn.clicked.connect(lambda: self._switch_mode("v2"))
        layout.addWidget(self.v2_btn)

        # V1（经典模式）按钮
        self.v1_btn = QPushButton("经典模式")
        self.v1_btn.setObjectName("mode_btn")
        self.v1_btn.setCheckable(True)
        self.v1_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.v1_btn.setToolTip("面向常量的配置，编辑颜色、字体等基础常量")
        self.v1_btn.clicked.connect(lambda: self._switch_mode("v1"))
        layout.addWidget(self.v1_btn)

        layout.addStretch()

        # 模式说明
        hint_label = QLabel("透明度配置在经典模式中")
        hint_label.setObjectName("mode_hint")
        layout.addWidget(hint_label)

        return bar

    def _switch_mode(self, mode: str):
        """切换编辑模式"""
        if mode == self._current_mode:
            return

        if self._is_destroyed:
            return

        self._current_mode = mode

        # 更新按钮状态
        self.v1_btn.setChecked(mode == "v1")
        self.v2_btn.setChecked(mode == "v2")

        # 切换堆叠页面并刷新数据
        if mode == "v2":
            self._ensure_v2_widget()
            self.stack.setCurrentIndex(0)
            # 使用可取消的延迟刷新
            if self._v2_widget:
                self._pending_refresh_widget = self._v2_widget
                self._refresh_timer.start(50)
        else:
            self._ensure_v1_widget()
            self.stack.setCurrentIndex(1)
            # 使用可取消的延迟刷新
            if self._v1_widget:
                self._pending_refresh_widget = self._v1_widget
                self._refresh_timer.start(50)

        logger.info(f"主题编辑器切换到 {mode.upper()} 模式")

    def _ensure_v2_widget(self):
        """确保V2 widget已创建"""
        if self._v2_widget is None:
            # 移除占位符
            self.stack.removeWidget(self._v2_placeholder)
            self._v2_placeholder.deleteLater()

            # 创建实际widget
            self._v2_widget = V2ThemeEditorWidget()
            self.stack.insertWidget(0, self._v2_widget)
            # 注意：数据加载在_switch_mode中统一处理

    def _ensure_v1_widget(self):
        """确保V1 widget已创建"""
        if self._v1_widget is None:
            # 移除占位符
            self.stack.removeWidget(self._v1_placeholder)
            self._v1_placeholder.deleteLater()

            # 创建实际widget
            self._v1_widget = ThemeSettingsWidget()
            self.stack.insertWidget(1, self._v1_widget)
            # 注意：数据加载在_switch_mode中统一处理

    def refresh(self):
        """刷新当前模式的配置"""
        if self._current_mode == "v2" and self._v2_widget:
            self._v2_widget.refresh()
        elif self._current_mode == "v1" and self._v1_widget:
            self._v1_widget.refresh()

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 模式切换栏样式
        mode_bar = self.findChild(QFrame, "mode_bar")
        if mode_bar:
            mode_bar.setStyleSheet(f"""
                QFrame#mode_bar {{
                    background-color: {palette.bg_secondary};
                    border-bottom: 1px solid {palette.border_color};
                }}
            """)

        # 模式标签样式
        mode_label = self.findChild(QLabel, "mode_label")
        if mode_label:
            mode_label.setStyleSheet(f"""
                QLabel#mode_label {{
                    font-family: {palette.ui_font};
                    font-size: {sp(13)}px;
                    color: {palette.text_secondary};
                }}
            """)

        # 模式按钮样式
        mode_btn_style = f"""
            QPushButton#mode_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(16)}px;
            }}
            QPushButton#mode_btn:hover {{
                color: {palette.text_primary};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            QPushButton#mode_btn:checked {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {theme_manager.PRIMARY_PALE};
                font-weight: 500;
            }}
        """
        self.v1_btn.setStyleSheet(mode_btn_style)
        self.v2_btn.setStyleSheet(mode_btn_style)

        # 模式提示样式
        mode_hint = self.findChild(QLabel, "mode_hint")
        if mode_hint:
            mode_hint.setStyleSheet(f"""
                QLabel#mode_hint {{
                    font-family: {palette.ui_font};
                    font-size: {sp(12)}px;
                    color: {palette.text_tertiary};
                    font-style: italic;
                }}
            """)

        # 堆叠区域背景
        self.stack.setStyleSheet("background-color: transparent;")


__all__ = [
    "UnifiedThemeSettingsWidget",
]
