"""
基础页面类 - 所有页面的父类

提供统一的导航信号和页面生命周期接口
"""

import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from themes.theme_manager import theme_manager
from components import LoadingOverlay

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """所有页面的基类

    功能：
    - 统一的导航信号（navigateRequested, goBackRequested）
    - 页面刷新接口（refresh）
    - 页面生命周期钩子（onShow, onHide）
    - 统一的LoadingOverlay支持
    - 主题信号的安全管理
    """

    # 导航信号
    navigateRequested = pyqtSignal(str, dict)  # (page_type, params)
    goBackRequested = pyqtSignal()
    # 替换导航信号：导航到新页面并清除当前页面的历史记录
    navigateReplaceRequested = pyqtSignal(str, dict)  # (page_type, params)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 主题信号连接标志
        self._theme_connected = False
        self._connect_theme_signal()

        # LoadingOverlay 延迟创建，首次调用 show_loading 时初始化
        self._loading_overlay = None

    def _connect_theme_signal(self):
        """连接主题信号（只连接一次）"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._safe_on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._safe_on_theme_changed)
            except TypeError:
                pass  # 信号可能已断开
            self._theme_connected = False

    def _safe_on_theme_changed(self, mode: str):
        """安全的主题改变回调（检查对象有效性）"""
        try:
            # 检查对象是否仍有效
            if not self.isVisible() and not self.parent():
                # 对象可能正在被删除，跳过处理
                return
            self.on_theme_changed(mode)
        except RuntimeError:
            # 对象已被删除，静默处理
            logger.debug("主题回调时对象已被删除")

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
            page_type: 页面类型（如'HOME', 'DETAIL', 'WRITING_DESK'等）
            **params: 页面参数
        """
        logger.info("BasePage.navigateTo called: page_type=%s, params=%s", page_type, params)
        self.navigateRequested.emit(page_type, params)
        logger.info("BasePage.navigateTo signal emitted")

    def navigateReplace(self, page_type, **params):
        """导航到其他页面并替换当前历史记录

        用于完成某个流程后导航到新页面，使返回按钮跳过当前流程页面。
        例如：灵感对话完成后跳转到项目详情页，返回时应直接到首页而非灵感对话。

        Args:
            page_type: 页面类型（如'HOME', 'DETAIL', 'WRITING_DESK'等）
            **params: 页面参数
        """
        self.navigateReplaceRequested.emit(page_type, params)

    def goBack(self):
        """返回上一页的便捷方法"""
        self.goBackRequested.emit()

    def _ensure_loading_overlay(self):
        """确保LoadingOverlay已创建"""
        if self._loading_overlay is None:
            self._loading_overlay = LoadingOverlay(parent=self)
            self._loading_overlay.hide()
            # 初始化大小
            self._loading_overlay.setGeometry(self.rect())

    def show_loading(self, text="加载中..."):
        """显示加载遮罩（带动画效果）

        Args:
            text: 加载提示文字，默认"加载中..."

        Example:
            self.show_loading("正在生成蓝图...")
        """
        self._ensure_loading_overlay()
        self._loading_overlay.show_with_animation(text)

    def hide_loading(self):
        """隐藏加载遮罩（带动画效果）"""
        if self._loading_overlay:
            self._loading_overlay.hide_with_animation()

    def resizeEvent(self, event):
        """窗口大小改变时自动调整overlay大小"""
        super().resizeEvent(event)
        if self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())

    def closeEvent(self, event):
        """关闭时清理主题信号连接"""
        self._disconnect_theme_signal()
        super().closeEvent(event)

    def deleteLater(self):
        """删除前清理信号连接"""
        self._disconnect_theme_signal()
        super().deleteLater()
