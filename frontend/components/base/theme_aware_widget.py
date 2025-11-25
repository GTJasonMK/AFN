"""
主题感知组件基类 - 统一管理主题切换逻辑

提供两个基类：
- ThemeAwareWidget: 基于 QWidget
- ThemeAwareFrame: 基于 QFrame

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
- 统一主题切换行为
"""

from PyQt6.QtWidgets import QWidget, QFrame
from themes.theme_manager import theme_manager


class ThemeAwareWidget(QWidget):
    """主题感知 Widget 基类

    特性：
    - 自动管理主题切换信号连接（避免重复连接）
    - 提供标准的 setupUI() 方法
    - 强制子类实现 _create_ui_structure() 和 _apply_theme()

    生命周期：
    1. __init__() - 初始化
    2. setupUI() - 设置UI
       -> _create_ui_structure() - 创建UI结构（只调用一次）
       -> _apply_theme() - 应用主题（每次主题切换都调用）
    3. on_theme_changed() - 主题改变时自动调用
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_connected = False
        self._ui_created = False

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
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

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
        self._apply_theme()

    def refresh_theme(self):
        """手动刷新主题

        在某些情况下（如组件动态创建后），可能需要手动刷新主题。
        """
        self._apply_theme()


class ThemeAwareFrame(QFrame):
    """主题感知 Frame 基类

    功能与 ThemeAwareWidget 相同，但基于 QFrame。
    适用于需要边框样式的组件。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_connected = False
        self._ui_created = False

    def setupUI(self):
        """初始化UI（模板方法）"""
        if not self._ui_created:
            self._create_ui_structure()
            self._ui_created = True

        self._apply_theme()

        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _create_ui_structure(self):
        """创建UI结构（子类必须实现）"""
        raise NotImplementedError("子类必须实现 _create_ui_structure() 方法")

    def _apply_theme(self):
        """应用主题样式（子类必须实现）"""
        raise NotImplementedError("子类必须实现 _apply_theme() 方法")

    def _on_theme_changed(self, mode: str):
        """主题改变时的内部处理"""
        self._apply_theme()

    def refresh_theme(self):
        """手动刷新主题"""
        self._apply_theme()
