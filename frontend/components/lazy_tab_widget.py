"""
懒加载Tab组件

只在Tab被激活时才加载其内容，减少初始渲染开销。

用法：
    tab_widget = LazyTabWidget()

    # 添加立即加载的Tab（如正文Tab）
    tab_widget.addTab(content_tab, "正文")

    # 添加懒加载Tab
    tab_widget.addLazyTab(
        "版本",
        loader_func=lambda: self._version_builder.create_versions_tab(chapter_data, self),
        placeholder_text="正在加载版本历史..."
    )
"""

import logging
from typing import Callable, Optional, Set, Dict

from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

logger = logging.getLogger(__name__)


class LazyTabWidget(QTabWidget):
    """懒加载Tab组件

    特性：
    - 懒加载：Tab内容仅在首次激活时加载
    - 占位符：未加载时显示占位Widget
    - 失效机制：支持标记Tab需要重新加载
    - 混合模式：支持普通Tab和懒加载Tab混用
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 懒加载相关
        self._tab_loaders: Dict[int, Callable[[], QWidget]] = {}  # tab_index -> loader_func
        self._tab_loaded: Set[int] = set()  # 已加载的tab索引
        self._placeholder_widgets: Dict[int, QWidget] = {}  # 占位Widget引用

        # 防止递归加载的标志
        self._is_loading = False

        # 连接Tab切换信号
        self.currentChanged.connect(self._on_tab_changed)

    def addLazyTab(
        self,
        title: str,
        loader_func: Callable[[], QWidget],
        placeholder_text: str = "正在加载..."
    ) -> int:
        """添加懒加载Tab

        Args:
            title: Tab标题
            loader_func: 加载函数，返回实际的Tab Widget
            placeholder_text: 占位提示文本

        Returns:
            Tab索引
        """
        # 创建占位Widget
        placeholder = self._create_placeholder(placeholder_text)

        # 添加Tab
        index = self.addTab(placeholder, title)

        # 记录加载器和占位Widget
        self._tab_loaders[index] = loader_func
        self._placeholder_widgets[index] = placeholder

        return index

    def _create_placeholder(self, text: str) -> QWidget:
        """创建占位Widget"""
        placeholder = QWidget()
        placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 加载提示标签
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding: {dp(20)}px;
        """)
        layout.addWidget(label)

        return placeholder

    def _on_tab_changed(self, index: int):
        """Tab切换时加载内容"""
        # 防止递归：如果正在加载中，跳过
        if self._is_loading:
            return

        # 检查是否是懒加载Tab且尚未加载
        if index in self._tab_loaders and index not in self._tab_loaded:
            self._load_tab(index)

    def _load_tab(self, index: int):
        """加载指定Tab的内容"""
        loader = self._tab_loaders.get(index)
        if not loader:
            return

        # 防止递归
        if self._is_loading:
            return

        self._is_loading = True

        try:
            # 保存当前标题
            title = self.tabText(index)

            # 调用加载器创建实际Widget
            actual_widget = loader()

            if actual_widget:
                # 获取旧的占位Widget
                old_widget = self._placeholder_widgets.get(index)

                # 暂时断开信号，避免替换Tab时触发递归
                self.currentChanged.disconnect(self._on_tab_changed)

                try:
                    # 替换Tab内容
                    self.removeTab(index)
                    self.insertTab(index, actual_widget, title)
                    self.setCurrentIndex(index)
                finally:
                    # 重新连接信号
                    self.currentChanged.connect(self._on_tab_changed)

                # 清理占位Widget
                if old_widget:
                    old_widget.deleteLater()
                    del self._placeholder_widgets[index]

                # 标记为已加载
                self._tab_loaded.add(index)

                logger.debug(f"懒加载Tab已加载: {title} (index={index})")

        except Exception as e:
            logger.error(f"加载Tab失败 (index={index}): {e}")

        finally:
            self._is_loading = False

    def invalidate_tab(self, index: int):
        """标记Tab需要重新加载

        下次切换到该Tab时会重新调用loader_func。

        Args:
            index: Tab索引
        """
        self._tab_loaded.discard(index)

    def invalidate_all_lazy_tabs(self):
        """标记所有懒加载Tab需要重新加载"""
        self._tab_loaded.clear()

    def is_tab_loaded(self, index: int) -> bool:
        """检查Tab是否已加载

        Args:
            index: Tab索引

        Returns:
            True表示已加载或非懒加载Tab
        """
        # 非懒加载Tab视为已加载
        if index not in self._tab_loaders:
            return True
        return index in self._tab_loaded

    def reload_tab(self, index: int):
        """强制重新加载指定Tab

        Args:
            index: Tab索引
        """
        if index not in self._tab_loaders:
            return

        # 防止递归
        if self._is_loading:
            return

        # 移除已加载标记
        self._tab_loaded.discard(index)

        # 如果当前显示的就是这个Tab，立即重新加载
        if self.currentIndex() == index:
            self._is_loading = True
            try:
                loader = self._tab_loaders.get(index)
                if not loader:
                    return

                title = self.tabText(index)
                old_widget = self.widget(index)

                # 调用加载器创建新Widget
                actual_widget = loader()

                if actual_widget:
                    # 暂时断开信号
                    self.currentChanged.disconnect(self._on_tab_changed)

                    try:
                        self.removeTab(index)
                        self.insertTab(index, actual_widget, title)
                        self.setCurrentIndex(index)
                    finally:
                        self.currentChanged.connect(self._on_tab_changed)

                    # 清理旧Widget
                    if old_widget:
                        old_widget.deleteLater()

                    # 标记为已加载
                    self._tab_loaded.add(index)

                    logger.debug(f"重新加载Tab: {title} (index={index})")

            except Exception as e:
                logger.error(f"重新加载Tab失败 (index={index}): {e}")

            finally:
                self._is_loading = False

    def update_loader(self, index: int, loader_func: Callable[[], QWidget]):
        """更新Tab的加载器函数

        用于章节切换时更新加载器，避免重建整个TabWidget。

        Args:
            index: Tab索引
            loader_func: 新的加载函数
        """
        if index in self._tab_loaders:
            self._tab_loaders[index] = loader_func
            # 标记需要重新加载
            self._tab_loaded.discard(index)

    def preload_tab(self, index: int):
        """预加载指定Tab（后台执行）

        用于在空闲时预加载Tab内容。

        Args:
            index: Tab索引
        """
        if index in self._tab_loaders and index not in self._tab_loaded:
            # 使用QTimer延迟执行，避免阻塞当前操作
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._load_tab(index))


__all__ = ['LazyTabWidget']
