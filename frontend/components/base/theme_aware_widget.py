"""
主题感知组件基类 - 统一管理主题切换逻辑

提供多个基类：
- ThemeAwareWidget: 基于 QWidget
- ThemeAwareFrame: 基于 QFrame
- ThemeAwareButton: 基于 QPushButton

用法示例：
    from components.base import ThemeAwareWidget

    class MyComponent(ThemeAwareWidget):
        def __init__(self, parent=None):
            self.my_label = None
            super().__init__(parent)
            self.setupUI()

        def _create_ui_structure(self):
            # 创建UI结构（只调用一次）
            layout = QVBoxLayout(self)
            self.my_label = QLabel("Hello")
            layout.addWidget(self.my_label)

        def _apply_theme(self):
            # 应用主题样式（可多次调用）
            if self.my_label:
                self.my_label.setStyleSheet(f"color: {theme_manager.TEXT_PRIMARY};")

设计原则：
- 拆分UI创建和样式应用
- 避免信号重复连接
- 自动断开信号，防止内存泄漏
- 统一主题切换行为
"""

import logging
from PyQt6.QtWidgets import QWidget, QFrame, QPushButton
from PyQt6.QtCore import QEvent
from themes.theme_manager import theme_manager

logger = logging.getLogger(__name__)


class ThemeAwareMixin:
    """主题感知混入类

    提供主题切换所需的所有共享逻辑，消除 ThemeAwareWidget 和 ThemeAwareFrame 之间的代码重复。

    此类不能单独使用，必须与 QWidget 或 QFrame 子类一起混入。
    """

    # 类型提示，表明这些属性会在子类中存在
    _theme_connected: bool
    _ui_created: bool
    _is_cleaned_up: bool

    def _init_theme_aware_state(self):
        """初始化主题感知状态（由子类的 __init__ 调用）"""
        self._theme_connected = False
        self._ui_created = False
        self._is_cleaned_up = False

    def setupUI(self):
        """初始化UI（模板方法）

        子类应该调用此方法来初始化UI，通常在 __init__() 之后调用。
        不要重写此方法，而是实现 _create_ui_structure() 和 _apply_theme()。
        """
        # 只在第一次调用时创建UI结构
        if not self._ui_created:
            self._create_ui_structure()
            self._ui_created = True

        # 每次都应用主题
        self._apply_theme()

        # 只连接一次主题信号
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题切换信号（内部使用）"""
        if not self._theme_connected and not self._is_cleaned_up:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题切换信号（内部使用）"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except (TypeError, RuntimeError):
                # 信号可能已断开或对象已删除
                pass
            self._theme_connected = False

    def _create_ui_structure(self):
        """创建UI结构（子类必须实现）

        在这里创建所有UI组件和布局，并保存组件引用。
        此方法只在第一次调用 setupUI() 时执行。

        示例：
            def _create_ui_structure(self):
                layout = QVBoxLayout(self)
                self.title_label = QLabel("Title")
                layout.addWidget(self.title_label)
        """
        raise NotImplementedError("子类必须实现 _create_ui_structure() 方法")

    def _apply_theme(self):
        """应用主题样式（子类必须实现）

        在这里设置所有组件的样式。
        此方法会在主题切换时被调用，所以必须是幂等的。

        示例：
            def _apply_theme(self):
                if self.title_label:
                    self.title_label.setStyleSheet(f"color: {theme_manager.TEXT_PRIMARY};")
        """
        raise NotImplementedError("子类必须实现 _apply_theme() 方法")

    def _on_theme_changed(self, mode: str):
        """主题改变时的内部处理

        子类通常不需要重写此方法。
        如果需要在主题切换时做额外处理，可以重写此方法，但记得调用 super()。
        """
        if self._is_cleaned_up:
            return
        try:
            self._apply_theme()
        except RuntimeError:
            # C++ 对象可能已被删除
            self._disconnect_theme_signal()

    def refresh_theme(self):
        """手动刷新主题

        在某些情况下（如组件动态创建后），可能需要手动刷新主题。
        """
        if not self._is_cleaned_up:
            self._apply_theme()

    def cleanup(self):
        """清理资源（显式调用）

        在需要手动清理组件时调用此方法。
        通常在 deleteLater() 或 closeEvent() 中会自动调用。
        """
        if not self._is_cleaned_up:
            self._is_cleaned_up = True
            self._disconnect_theme_signal()


class ThemeAwareWidget(ThemeAwareMixin, QWidget):
    """主题感知 Widget 基类

    特性：
    - 自动管理主题切换信号连接（避免重复连接）
    - 自动在组件销毁时断开信号（防止内存泄漏）
    - 提供标准的 setupUI() 方法
    - 强制子类实现 _create_ui_structure() 和 _apply_theme()

    生命周期：
    1. __init__() - 初始化
    2. setupUI() - 设置UI
       -> _create_ui_structure() - 创建UI结构（只调用一次）
       -> _apply_theme() - 应用主题（每次主题切换都调用）
    3. _on_theme_changed() - 主题改变时自动调用
    4. cleanup() / deleteLater() - 销毁时自动断开信号
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_theme_aware_state()

    def deleteLater(self):
        """重写 deleteLater，确保在删除前断开信号"""
        self.cleanup()
        super().deleteLater()

    def closeEvent(self, event):
        """重写关闭事件，确保断开信号"""
        self.cleanup()
        super().closeEvent(event)

    def event(self, event):
        """拦截 DeferredDelete 事件，确保清理"""
        if event.type() == QEvent.Type.DeferredDelete:
            self.cleanup()
        return super().event(event)


class ThemeAwareFrame(ThemeAwareMixin, QFrame):
    """主题感知 Frame 基类

    功能与 ThemeAwareWidget 相同，但基于 QFrame。
    适用于需要边框样式的组件。

    特性：
    - 自动管理主题切换信号连接（避免重复连接）
    - 自动在组件销毁时断开信号（防止内存泄漏）
    - 提供标准的 setupUI() 方法
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_theme_aware_state()

    def deleteLater(self):
        """重写 deleteLater，确保在删除前断开信号"""
        self.cleanup()
        super().deleteLater()

    def closeEvent(self, event):
        """重写关闭事件，确保断开信号"""
        self.cleanup()
        super().closeEvent(event)

    def event(self, event):
        """拦截 DeferredDelete 事件，确保清理"""
        if event.type() == QEvent.Type.DeferredDelete:
            self.cleanup()
        return super().event(event)


class ThemeAwareButton(ThemeAwareMixin, QPushButton):
    """主题感知 Button 基类

    功能与 ThemeAwareWidget 相同，但基于 QPushButton。
    适用于需要主题感知的自定义按钮。

    注意：由于 QPushButton 通常不需要复杂的 UI 结构，
    可以只实现 _apply_theme() 方法，_create_ui_structure() 默认为空实现。

    特性：
    - 自动管理主题切换信号连接（避免重复连接）
    - 自动在组件销毁时断开信号（防止内存泄漏）
    - 提供标准的 setupUI() 方法
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._init_theme_aware_state()

    def _create_ui_structure(self):
        """QPushButton 通常不需要创建额外的 UI 结构，默认空实现"""
        pass

    def deleteLater(self):
        """重写 deleteLater，确保在删除前断开信号"""
        self.cleanup()
        super().deleteLater()

    def closeEvent(self, event):
        """重写关闭事件，确保断开信号"""
        self.cleanup()
        super().closeEvent(event)

    def event(self, event):
        """拦截 DeferredDelete 事件，确保清理"""
        if event.type() == QEvent.Type.DeferredDelete:
            self.cleanup()
        return super().event(event)
