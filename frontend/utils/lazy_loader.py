"""
懒加载工具

提供UI组件的延迟初始化功能，减少页面首次加载时间。

使用方式：

1. 使用 LazyWidget 包装复杂组件：

    from utils.lazy_loader import LazyWidget

    # 在_create_ui_structure中
    self.complex_panel = LazyWidget(
        factory=lambda: ComplexPanel(self.project_id),
        placeholder_text="加载中...",
    )
    layout.addWidget(self.complex_panel)

    # 在onShow中触发加载
    def onShow(self):
        self.complex_panel.ensure_loaded()

2. 使用 @lazy_property 装饰器延迟创建属性：

    from utils.lazy_loader import lazy_property

    class MyPage(BasePage):
        @lazy_property
        def api_client(self):
            return APIClient()
"""

import logging
from typing import Callable, Optional, TypeVar, Generic

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QStackedWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer

logger = logging.getLogger(__name__)

T = TypeVar('T')


class lazy_property(Generic[T]):
    """延迟属性装饰器

    第一次访问时才创建值，之后缓存。

    Usage:
        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return create_expensive_resource()
    """

    def __init__(self, factory: Callable[..., T]):
        self._factory = factory
        self._attr_name = None

    def __set_name__(self, owner, name):
        self._attr_name = f"_lazy_{name}"

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self  # type: ignore

        if not hasattr(instance, self._attr_name):
            value = self._factory(instance)
            setattr(instance, self._attr_name, value)
        return getattr(instance, self._attr_name)


class LazyWidget(QWidget):
    """懒加载Widget包装器

    首次需要时才创建实际的Widget，之前显示占位符。

    特性：
    - 延迟创建：实际Widget在ensure_loaded()时才创建
    - 占位符：创建前显示loading文本
    - 尺寸策略：自动继承实际Widget的尺寸策略

    Args:
        factory: 创建实际Widget的工厂函数
        placeholder_text: 占位符文本
        auto_load_delay: 自动加载延迟(ms)，0表示不自动加载
        parent: 父Widget
    """

    def __init__(
        self,
        factory: Callable[[], QWidget],
        placeholder_text: str = "加载中...",
        auto_load_delay: int = 0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._factory = factory
        self._placeholder_text = placeholder_text
        self._auto_load_delay = auto_load_delay
        self._actual_widget: Optional[QWidget] = None
        self._is_loaded = False

        self._setup_ui()

        # 自动加载
        if auto_load_delay > 0:
            QTimer.singleShot(auto_load_delay, self.ensure_loaded)

    def _setup_ui(self):
        """设置占位符UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 使用QStackedWidget在占位符和实际Widget之间切换
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # 占位符
        self._placeholder = QLabel(self._placeholder_text)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: gray; background-color: transparent;")
        self._stack.addWidget(self._placeholder)

    def ensure_loaded(self) -> QWidget:
        """确保Widget已加载，返回实际Widget

        如果尚未加载，会立即创建。
        如果已加载，直接返回缓存的Widget。
        """
        if self._is_loaded:
            return self._actual_widget

        try:
            # 创建实际Widget
            self._actual_widget = self._factory()

            # 添加到栈并切换
            self._stack.addWidget(self._actual_widget)
            self._stack.setCurrentWidget(self._actual_widget)

            # 继承尺寸策略
            if self._actual_widget:
                self.setSizePolicy(self._actual_widget.sizePolicy())
                if self._actual_widget.minimumSize().isValid():
                    self.setMinimumSize(self._actual_widget.minimumSize())

            self._is_loaded = True
            logger.debug("LazyWidget loaded: %s", type(self._actual_widget).__name__)

        except Exception as e:
            logger.error("LazyWidget加载失败: %s", e)
            self._placeholder.setText(f"加载失败: {e}")
            raise

        return self._actual_widget

    @property
    def is_loaded(self) -> bool:
        """检查是否已加载"""
        return self._is_loaded

    @property
    def widget(self) -> Optional[QWidget]:
        """获取实际Widget（如未加载返回None）"""
        return self._actual_widget

    def unload(self):
        """卸载实际Widget，释放资源

        可用于内存压力大时主动释放非活跃组件。
        """
        if not self._is_loaded or self._actual_widget is None:
            return

        # 从栈中移除
        self._stack.removeWidget(self._actual_widget)

        # 清理资源
        if hasattr(self._actual_widget, 'cleanup'):
            try:
                self._actual_widget.cleanup()
            except Exception as e:
                logger.warning("LazyWidget cleanup失败: %s", e)

        # 删除Widget
        self._actual_widget.deleteLater()
        self._actual_widget = None
        self._is_loaded = False

        # 切回占位符
        self._stack.setCurrentWidget(self._placeholder)
        self._placeholder.setText(self._placeholder_text)

        logger.debug("LazyWidget unloaded")


class DeferredInitMixin:
    """延迟初始化混入类

    用于需要延迟初始化复杂组件的页面。

    Usage:
        class MyPage(BasePage, DeferredInitMixin):
            def __init__(self):
                super().__init__()
                self.setupUI()

            def _create_ui_structure(self):
                # 创建基础UI
                ...
                # 注册延迟初始化
                self.defer_init('complex_panel', self._create_complex_panel)

            def _create_complex_panel(self):
                return ComplexPanel()

            def onShow(self):
                # 触发延迟初始化
                self.run_deferred_inits()
    """

    def __init__(self):
        self._deferred_inits: dict = {}
        self._deferred_complete: set = set()

    def defer_init(self, name: str, factory: Callable[[], None]):
        """注册延迟初始化任务

        Args:
            name: 任务名称
            factory: 初始化函数
        """
        if not hasattr(self, '_deferred_inits'):
            self._deferred_inits = {}
            self._deferred_complete = set()

        self._deferred_inits[name] = factory

    def run_deferred_inits(self):
        """执行所有未完成的延迟初始化"""
        if not hasattr(self, '_deferred_inits'):
            return

        for name, factory in self._deferred_inits.items():
            if name not in self._deferred_complete:
                try:
                    factory()
                    self._deferred_complete.add(name)
                    logger.debug("Deferred init completed: %s", name)
                except Exception as e:
                    logger.error("Deferred init failed: %s - %s", name, e)

    def is_init_complete(self, name: str) -> bool:
        """检查指定的延迟初始化是否已完成"""
        if not hasattr(self, '_deferred_complete'):
            return False
        return name in self._deferred_complete
