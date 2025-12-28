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
- 使用延迟刷新优化大量组件的主题切换
- 优先刷新可见组件
"""

import logging
from typing import Set, Optional, List
from weakref import WeakSet
from PyQt6.QtWidgets import QWidget, QFrame, QPushButton, QApplication
from PyQt6.QtCore import QEvent, QTimer
from themes.theme_manager import theme_manager

logger = logging.getLogger(__name__)


# 批量刷新管理器（模块级单例）
class _ThemeRefreshManager:
    """主题刷新管理器

    用于批量处理主题切换时的组件刷新，避免每个组件独立刷新导致的性能问题。

    性能优化：三阶段优先级提交
    1. 收集阶段：收集所有需要刷新的组件（不执行_apply_theme）
    2. 分类阶段：按可见性和优先级分类组件
    3. 执行阶段：
       - 先刷新可见组件（用户能看到的）
       - 延迟刷新不可见组件（用户看不到的）

    这样可以避免：
    - 每个组件独立刷新导致的多次重绘
    - _apply_theme和polish交替执行导致的布局抖动
    - 刷新不可见组件造成的性能浪费
    """

    _instance: Optional['_ThemeRefreshManager'] = None

    # 组件优先级（数值越小优先级越高）
    PRIORITY_HIGH = 0     # 顶层窗口、主要容器
    PRIORITY_NORMAL = 1   # 普通组件
    PRIORITY_LOW = 2      # 不可见组件、后台组件

    def __init__(self):
        self._pending_widgets: Set[QWidget] = set()
        self._deferred_widgets: WeakSet[QWidget] = WeakSet()  # 延迟刷新的不可见组件
        self._refresh_timer: Optional[QTimer] = None
        self._deferred_timer: Optional[QTimer] = None
        self._is_refreshing = False  # 防止递归刷新

    @classmethod
    def instance(cls) -> '_ThemeRefreshManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def schedule_theme_update(self, widget: QWidget):
        """调度组件主题更新（三阶段优先级提交：收集阶段）

        将组件添加到待更新集合，延迟执行实际的主题应用。
        """
        try:
            # 防止递归刷新期间添加新组件
            if self._is_refreshing:
                return

            # 检查组件是否有效
            if widget is None:
                return

            # 添加到待刷新集合
            self._pending_widgets.add(widget)

            # 启动或重置刷新定时器
            if self._refresh_timer is None:
                self._refresh_timer = QTimer()
                self._refresh_timer.setSingleShot(True)
                self._refresh_timer.timeout.connect(self._do_priority_refresh)

            # 重置定时器（合并多个刷新请求）
            if not self._refresh_timer.isActive():
                self._refresh_timer.start(16)  # 16ms，约1帧的延迟
        except RuntimeError:
            # 组件可能已被删除
            pass

    def _classify_widgets(self, widgets: List[QWidget]) -> tuple:
        """按优先级分类组件

        Returns:
            (visible_widgets, invisible_widgets): 可见组件列表和不可见组件列表
        """
        visible = []
        invisible = []

        for widget in widgets:
            try:
                if widget is None:
                    continue
                # 检查组件及其所有父级是否可见
                if self._is_widget_visible(widget):
                    visible.append(widget)
                else:
                    invisible.append(widget)
            except RuntimeError:
                # C++对象已删除
                continue

        return visible, invisible

    def _is_widget_visible(self, widget: QWidget) -> bool:
        """检查组件是否真正可见（包括父级）"""
        try:
            # 检查组件本身
            if not widget.isVisible():
                return False

            # 检查父级链
            parent = widget.parent()
            while parent is not None:
                if isinstance(parent, QWidget):
                    if not parent.isVisible():
                        return False
                parent = parent.parent() if hasattr(parent, 'parent') else None

            return True
        except RuntimeError:
            return False

    def _do_priority_refresh(self):
        """执行优先级刷新"""
        if not self._pending_widgets or self._is_refreshing:
            return

        self._is_refreshing = True

        # 获取并清空待刷新集合
        widgets = list(self._pending_widgets)
        self._pending_widgets.clear()

        # 分类组件
        visible_widgets, invisible_widgets = self._classify_widgets(widgets)

        # 获取主窗口
        main_window = None
        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                if w.isVisible() and hasattr(w, 'setUpdatesEnabled'):
                    main_window = w
                    break

        # 阶段1：禁用UI更新
        if main_window:
            main_window.setUpdatesEnabled(False)

        try:
            # 阶段2a：优先刷新可见组件
            for widget in visible_widgets:
                try:
                    if widget is not None and hasattr(widget, '_apply_theme'):
                        widget._apply_theme()
                except (RuntimeError, AttributeError):
                    continue

            # 阶段2b：批量执行polish（仅可见组件）
            for widget in visible_widgets:
                try:
                    if widget is not None:
                        widget.style().unpolish(widget)
                        widget.style().polish(widget)
                except (RuntimeError, AttributeError):
                    continue

            # 将不可见组件加入延迟队列
            for widget in invisible_widgets:
                self._deferred_widgets.add(widget)

        finally:
            # 阶段3：恢复UI更新并触发一次重绘
            self._is_refreshing = False
            if main_window:
                main_window.setUpdatesEnabled(True)
                main_window.repaint()

        # 启动延迟刷新定时器（如果有不可见组件）
        if self._deferred_widgets:
            if self._deferred_timer is None:
                self._deferred_timer = QTimer()
                self._deferred_timer.setSingleShot(True)
                self._deferred_timer.timeout.connect(self._do_deferred_refresh)

            if not self._deferred_timer.isActive():
                self._deferred_timer.start(100)  # 100ms后刷新不可见组件

    def _do_deferred_refresh(self):
        """延迟刷新不可见组件"""
        if self._is_refreshing:
            return

        self._is_refreshing = True

        # 获取延迟刷新的组件
        widgets = list(self._deferred_widgets)
        self._deferred_widgets.clear()

        try:
            # 批量刷新
            for widget in widgets:
                try:
                    if widget is not None and hasattr(widget, '_apply_theme'):
                        widget._apply_theme()
                        widget.style().unpolish(widget)
                        widget.style().polish(widget)
                except (RuntimeError, AttributeError):
                    continue
        finally:
            self._is_refreshing = False

    # 保留旧方法以兼容
    def schedule_refresh(self, widget: QWidget):
        """兼容旧接口：调度组件刷新"""
        self.schedule_theme_update(widget)


# 获取全局刷新管理器实例
_refresh_manager = _ThemeRefreshManager.instance()


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

        性能优化：不立即执行_apply_theme，而是注册到刷新管理器。
        刷新管理器会在收集完所有组件后，统一执行两阶段提交刷新。

        子类通常不需要重写此方法。
        如果需要在主题切换时做额外处理，可以重写此方法，但记得调用 super()。
        """
        if self._is_cleaned_up:
            return
        try:
            # 使用debug级别避免主题切换时的日志洪流
            logger.debug("Theme changed to %s for %s", mode, self.__class__.__name__)
            # 性能优化：只注册到刷新管理器，不立即执行_apply_theme
            # 刷新管理器会批量执行所有组件的_apply_theme
            _refresh_manager.schedule_theme_update(self)
        except RuntimeError:
            # C++ 对象可能已被删除
            self._disconnect_theme_signal()

    def _force_style_refresh(self):
        """强制刷新自身的样式缓存"""
        try:
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        except (RuntimeError, AttributeError):
            # 组件可能已被删除或style不可用
            pass

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
