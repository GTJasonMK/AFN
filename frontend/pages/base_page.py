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
            # 仅当对象正在被删除时才跳过（没有父对象且已被标记删除）
            # 注意：在QStackedWidget中的非当前页面虽然不可见，但仍需要更新主题
            logger.info(f"=== BasePage._safe_on_theme_changed({mode}) for {self.__class__.__name__} ===")
            self.on_theme_changed(mode)
        except RuntimeError:
            # 对象已被删除，静默处理
            logger.debug("主题回调时对象已被删除")

    def on_theme_changed(self, mode: str):
        """主题改变时的回调

        子类应该重写此方法以重新应用样式。
        默认实现只调用 _apply_theme()，不会触发数据加载。

        注意：子组件（ThemeAware* 类）会自动响应主题信号，
        不需要父组件递归刷新子组件。
        """
        # 只调用 _apply_theme() 应用样式，不调用完整的 setupUI()
        # 这样避免了可能的副作用（如动画重播、数据重载等）
        has_apply_theme = hasattr(self, '_apply_theme')
        if has_apply_theme:
            logger.debug(f"BasePage.on_theme_changed: calling {self.__class__.__name__}._apply_theme()")
            self._apply_theme()
            # 只刷新自身样式缓存，不递归刷新子组件
            # 子组件会通过各自的主题信号响应来刷新
            self._force_style_refresh()

    def _force_style_refresh(self):
        """强制刷新自身的样式缓存

        注意：不再递归刷新子组件，因为子组件会通过
        各自的主题信号响应（ThemeAwareMixin）来自行刷新。
        递归刷新会导致重复操作和性能问题。
        """
        try:
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        except RuntimeError:
            # 组件可能已被删除
            pass

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
