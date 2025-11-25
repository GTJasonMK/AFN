"""
基础页面类 - 所有页面的父类

提供统一的导航信号和页面生命周期接口
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from themes.theme_manager import theme_manager
from components import LoadingOverlay


class BasePage(QWidget):
    """所有页面的基类

    功能：
    - 统一的导航信号（navigateRequested, goBackRequested）
    - 页面刷新接口（refresh）
    - 页面生命周期钩子（onShow, onHide）
    - 统一的LoadingOverlay支持
    """

    # 导航信号
    navigateRequested = pyqtSignal(str, dict)  # (page_type, params)
    goBackRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self.on_theme_changed)

        # 创建统一的LoadingOverlay（默认隐藏）
        self._loading_overlay = None
        self._init_loading_overlay()

    def on_theme_changed(self, mode: str):
        """主题改变时的回调

        子类应该重写此方法以重新应用样式

        推荐的实现模式：
        方案1：拆分创建和样式应用
        ```python
        def setupUI(self):
            if not self.layout():
                self._create_ui_structure()
            self._apply_theme()

        def _create_ui_structure(self):
            # 创建布局和组件（只调用一次）
            layout = QVBoxLayout(self)
            # ... 创建组件

        def _apply_theme(self):
            # 应用样式（可多次调用）
            self.setStyleSheet(...)
        ```

        方案2：清空布局重建
        ```python
        def setupUI(self):
            existing_layout = self.layout()
            if existing_layout:
                # 清空现有布局
                while existing_layout.count():
                    item = existing_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                main_layout = existing_layout
            else:
                main_layout = QVBoxLayout(self)
            # 重建组件并应用样式
        ```
        """
        # 调用setupUI重建界面（setupUI内部需要处理已存在的布局）
        if hasattr(self, 'setupUI'):
            self.setupUI()

    def refresh(self, **params):
        """刷新页面数据

        当页面已存在且被重新导航到时调用
        子类应该重写此方法以更新页面内容

        Args:
            **params: 页面参数（如project_id等）
        """
        pass

    def onShow(self):
        """页面显示时的钩子

        当页面被切换为当前页面时调用
        子类可以重写此方法执行初始化逻辑
        """
        pass

    def onHide(self):
        """页面隐藏时的钩子

        当页面被切换离开时调用
        子类可以重写此方法执行清理逻辑
        """
        pass

    def navigateTo(self, page_type, **params):
        """导航到其他页面的便捷方法

        Args:
            page_type: 页面类型（如'WORKSPACE', 'DETAIL'等）
            **params: 页面参数
        """
        self.navigateRequested.emit(page_type, params)

    def goBack(self):
        """返回上一页的便捷方法"""
        self.goBackRequested.emit()

    def _init_loading_overlay(self):
        """初始化LoadingOverlay（延迟创建）"""
        # 不在这里创建，而是在第一次调用show_loading时创建
        # 这样避免所有页面都创建不必要的overlay
        pass

    def _ensure_loading_overlay(self):
        """确保LoadingOverlay已创建"""
        if self._loading_overlay is None:
            self._loading_overlay = LoadingOverlay(parent=self)
            self._loading_overlay.hide()
            # 初始化大小
            self._loading_overlay.setGeometry(self.rect())

    def show_loading(self, text="加载中..."):
        """显示加载遮罩

        Args:
            text: 加载提示文字，默认"加载中..."

        Example:
            self.show_loading("正在生成蓝图...")
        """
        self._ensure_loading_overlay()
        self._loading_overlay.setText(text)
        self._loading_overlay.show()
        self._loading_overlay.raise_()  # 确保在最上层

    def hide_loading(self):
        """隐藏加载遮罩"""
        if self._loading_overlay:
            self._loading_overlay.hide()

    def resizeEvent(self, event):
        """窗口大小改变时自动调整overlay大小"""
        super().resizeEvent(event)
        if self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())
