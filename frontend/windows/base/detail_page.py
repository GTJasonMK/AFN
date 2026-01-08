"""
详情页基类

提供详情页的通用结构：Header + Tab导航 + 内容区域
可被 NovelDetail 和 CodingDetail 继承使用。
"""

import logging
from typing import Dict, List, Optional, Any, Callable

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QLabel, QFrame, QScrollArea, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer

from pages.base_page import BasePage
from components.loading_spinner import LoadingOverlay
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class BaseDetailPage(BasePage):
    """详情页基类

    提供通用的页面结构：
    +------------------------------------------------------------------+
    | Header: 项目图标 | 标题/类型/状态 | 操作按钮                        |
    +------------------------------------------------------------------+
    | Tab导航栏                                                         |
    +------------------------------------------------------------------+
    |                                                                  |
    |                    Section内容区域（可滚动）                       |
    |                                                                  |
    +------------------------------------------------------------------+

    子类需要实现：
    - get_tab_config() -> 返回Tab配置列表
    - create_section_content(section_id) -> 创建Section组件
    - get_blueprint() -> 获取蓝图数据
    - create_header_content() -> 创建Header内容
    """

    def __init__(self, project_id: str, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        # 项目数据
        self.project_data: Optional[Dict[str, Any]] = None

        # 当前激活的Section
        self.active_section: str = ''

        # Section组件缓存
        self.section_widgets: Dict[str, QWidget] = {}

        # 加载遮罩
        self._section_loading_overlay: Optional[LoadingOverlay] = None

        # UI组件引用（子类在create_header_content中设置）
        self.header: Optional[QWidget] = None
        self.tab_bar: Optional[QWidget] = None
        self.content_stack: Optional[QStackedWidget] = None

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_base_ui_structure()
        self._apply_theme()

    def _create_base_ui_structure(self):
        """创建基础UI结构"""
        from PyQt6.QtWidgets import QApplication

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部Header（由子类实现具体内容）
        self.header = self._create_header_frame()
        main_layout.addWidget(self.header)

        QApplication.processEvents()

        # Tab导航栏
        self.tab_bar = self._create_tab_bar()
        main_layout.addWidget(self.tab_bar)

        QApplication.processEvents()

        # 内容区域
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

    def _create_header_frame(self) -> QWidget:
        """创建Header框架

        子类应该重写 create_header_content() 来填充Header内容
        """
        header = QFrame()
        header.setObjectName("detail_header")
        header.setFixedHeight(dp(80))

        layout = QHBoxLayout(header)
        layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        layout.setSpacing(dp(16))

        # 调用子类方法创建Header内容
        self.create_header_content(layout)

        return header

    def _create_tab_bar(self) -> QWidget:
        """创建Tab导航栏"""
        tab_bar = QFrame()
        tab_bar.setObjectName("detail_tab_bar")
        tab_bar.setFixedHeight(dp(48))

        layout = QHBoxLayout(tab_bar)
        layout.setContentsMargins(dp(24), 0, dp(24), 0)
        layout.setSpacing(dp(8))

        # 获取Tab配置
        tabs = self.get_tab_config()

        for tab_config in tabs:
            tab_id = tab_config['id']
            tab_label = tab_config['label']

            btn = QPushButton(tab_label)
            btn.setObjectName(f"tab_btn_{tab_id}")
            btn.setCheckable(True)
            btn.setProperty("tab_id", tab_id)
            btn.clicked.connect(lambda checked, sid=tab_id: self.switch_section(sid))

            layout.addWidget(btn)

        layout.addStretch()

        # 设置默认选中的Tab
        if tabs:
            self.active_section = tabs[0]['id']
            first_btn = tab_bar.findChild(QPushButton, f"tab_btn_{self.active_section}")
            if first_btn:
                first_btn.setChecked(True)

        return tab_bar

    def switch_section(self, section_id: str):
        """切换到指定Section"""
        if self.active_section == section_id:
            return

        # 更新Tab按钮状态
        if self.tab_bar:
            for btn in self.tab_bar.findChildren(QPushButton):
                btn.setChecked(btn.property("tab_id") == section_id)

        self.active_section = section_id
        self.load_section(section_id)

    def load_section(self, section_id: str):
        """加载Section内容"""
        # 如果已缓存，直接显示
        if section_id in self.section_widgets:
            self.content_stack.setCurrentWidget(self.section_widgets[section_id])
            return

        # 显示加载状态
        self._ensure_section_loading_overlay()
        section_name = self._get_section_display_name(section_id)
        self._section_loading_overlay.show_with_animation(f"加载{section_name}...")

        # 创建Section骨架
        scroll, container, layout = self._create_section_skeleton()

        # 缓存并显示
        self.section_widgets[section_id] = scroll
        self.content_stack.addWidget(scroll)
        self.content_stack.setCurrentWidget(scroll)

        # 延迟填充内容
        QTimer.singleShot(8, lambda: self._fill_section_content(section_id, container, layout))

    def _ensure_section_loading_overlay(self):
        """确保加载遮罩存在"""
        if not self._section_loading_overlay:
            self._section_loading_overlay = LoadingOverlay(
                text="加载中...",
                parent=self.content_stack
            )

    def _create_section_skeleton(self):
        """创建Section骨架"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            {theme_manager.scrollbar()}
        """)

        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        scroll.setWidget(container)
        return scroll, container, layout

    def _fill_section_content(self, section_id: str, container: QWidget, layout: QVBoxLayout):
        """填充Section内容"""
        try:
            # 检查对象是否有效
            try:
                _ = layout.count()
                _ = container.isVisible()
            except RuntimeError:
                logger.debug("Section '%s' 的布局已被删除，跳过填充", section_id)
                return

            # 调用子类方法创建Section内容
            section = self.create_section_content(section_id)
            if section:
                layout.addWidget(section, stretch=1)

        except RuntimeError as e:
            logger.debug("填充Section '%s' 时对象已删除: %s", section_id, str(e))
        except Exception as e:
            logger.error("创建Section '%s' 时出错: %s", section_id, str(e), exc_info=True)
            try:
                _ = layout.count()
                error_label = QLabel(f"加载 {section_id} 失败: {str(e)}")
                error_label.setWordWrap(True)
                error_label.setStyleSheet(f"color: {theme_manager.ERROR}; padding: {dp(20)}px; background-color: transparent;")
                layout.addWidget(error_label)
            except RuntimeError:
                pass
        finally:
            # 隐藏加载状态
            if self._section_loading_overlay:
                try:
                    self._section_loading_overlay.hide_with_animation()
                except RuntimeError:
                    pass

    def refresh_current_section(self):
        """刷新当前Section"""
        if self.active_section in self.section_widgets:
            widget = self.section_widgets.pop(self.active_section)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()
        self.load_section(self.active_section)

    def clear_all_sections(self):
        """清除所有缓存的Section"""
        for section_id, widget in list(self.section_widgets.items()):
            try:
                if widget and hasattr(widget, 'stopAllTasks'):
                    widget.stopAllTasks()
            except RuntimeError:
                pass

        self.section_widgets.clear()

        while self.content_stack.count() > 0:
            try:
                widget = self.content_stack.widget(0)
                if widget:
                    self.content_stack.removeWidget(widget)
                    widget.deleteLater()
                else:
                    break
            except RuntimeError:
                break

    # ==================== 子类需要实现的方法 ====================

    def get_tab_config(self) -> List[Dict[str, str]]:
        """获取Tab配置

        返回格式: [{"id": "overview", "label": "概览"}, ...]
        """
        raise NotImplementedError("子类必须实现 get_tab_config()")

    def create_header_content(self, layout: QHBoxLayout):
        """创建Header内容

        Args:
            layout: Header的布局，子类在此添加组件
        """
        raise NotImplementedError("子类必须实现 create_header_content()")

    def create_section_content(self, section_id: str) -> Optional[QWidget]:
        """创建Section内容组件

        Args:
            section_id: Section的ID

        Returns:
            Section组件，或None
        """
        raise NotImplementedError("子类必须实现 create_section_content()")

    def get_blueprint(self) -> Dict[str, Any]:
        """获取蓝图数据

        Returns:
            蓝图字典
        """
        raise NotImplementedError("子类必须实现 get_blueprint()")

    def _get_section_display_name(self, section_id: str) -> str:
        """获取Section显示名称

        子类可以重写此方法提供自定义名称
        """
        tabs = self.get_tab_config()
        for tab in tabs:
            if tab['id'] == section_id:
                return tab['label']
        return section_id

    def _apply_theme(self):
        """应用主题样式

        子类可以重写此方法自定义样式
        """
        from themes.modern_effects import ModernEffects

        bg_color = theme_manager.book_bg_primary()
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = theme_manager.get_component_opacity("content")

        if transparency_enabled:
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)


__all__ = ["BaseDetailPage"]
