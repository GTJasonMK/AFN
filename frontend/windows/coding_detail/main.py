"""
编程项目详情主页面

采用顶部Tab导航，提供编程项目的完整浏览和编辑体验。

架构说明：
- CodingDetail: 主页面类，负责UI布局和生命周期
- HeaderManagerMixin: Header创建和样式
- TabManagerMixin: Tab导航管理
- SectionLoaderMixin: Section加载
- SaveManagerMixin: 保存管理
- EditDispatcherMixin: 编辑请求分发
"""

import logging

from PyQt6.QtWidgets import QVBoxLayout, QStackedWidget, QApplication

from pages.base_page import BasePage
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.message_service import MessageService
from utils.formatters import get_project_status_text
from utils.async_worker import AsyncAPIWorker
from utils.worker_manager import WorkerManager
from windows.novel_detail.dirty_tracker import DirtyTracker

from .mixins import (
    HeaderManagerMixin,
    TabManagerMixin,
    SectionLoaderMixin,
    SaveManagerMixin,
    EditDispatcherMixin,
)

logger = logging.getLogger(__name__)


class CodingDetail(
    HeaderManagerMixin,
    TabManagerMixin,
    SectionLoaderMixin,
    SaveManagerMixin,
    EditDispatcherMixin,
    BasePage
):
    """编程项目详情页

    布局：
    +------------------------------------------------------------------+
    | Header: 项目图标 | 标题/类型/状态 | 保存/返回/生成按钮              |
    +------------------------------------------------------------------+
    | Tab导航: 概览 | 技术栈 | 模块 | 依赖 | 功能大纲 | 已生成            |
    +------------------------------------------------------------------+
    |                                                                  |
    |                    Section内容区域（可滚动）                       |
    |                                                                  |
    +------------------------------------------------------------------+
    """

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = APIClientManager.get_client()
        self.project_data = None
        self.section_data = {}
        self.active_section = 'overview'

        # Section组件映射
        self.section_widgets = {}

        # 脏数据追踪器
        self.dirty_tracker = DirtyTracker()

        # 异步任务管理
        self.worker_manager = WorkerManager(self)

        # 加载操作ID（用于防止加载动画竞态条件）
        self._load_project_op_id = None

        self.setupUI()
        self.loadProjectBasicInfo()
        self.loadSection('overview')

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部Header
        self.createHeader()
        main_layout.addWidget(self.header)

        QApplication.processEvents()

        # Tab导航栏
        self.createTabBar()
        main_layout.addWidget(self.tab_bar)

        QApplication.processEvents()

        # 内容区域
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

    def _apply_theme(self):
        """应用主题样式"""
        from PyQt6.QtCore import Qt
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

            transparent_containers = ['header', 'tab_bar', 'content_stack']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)
                    if container_name == 'content_stack':
                        container.setStyleSheet("background-color: transparent;")
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            containers_to_restore = ['header', 'tab_bar', 'content_stack']
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

        # 更新Header和Tab栏样式
        if hasattr(self, 'header') and self.header:
            self._applyHeaderStyle()
        if hasattr(self, 'tab_bar') and self.tab_bar:
            self._applyTabStyle()

    def loadProjectBasicInfo(self):
        """加载项目基本信息"""
        self._load_project_op_id = self.show_loading("正在加载项目信息...", "load_project")

        worker = AsyncAPIWorker(self.api_client.get_coding_project, self.project_id)
        worker.success.connect(self._onProjectBasicInfoLoaded)
        worker.error.connect(self._onProjectBasicInfoError)

        self.worker_manager.start(worker, 'load_project')

    def _onProjectBasicInfoLoaded(self, response):
        """项目基本信息加载成功"""
        self.hide_loading(self._load_project_op_id)
        self._load_project_op_id = None
        self.project_data = response

        # 获取编程项目蓝图
        blueprint = self.get_blueprint()

        logger.info(
            f"loadProjectBasicInfo: project_id={self.project_id}, "
            f"status={self.project_data.get('status')}, "
            f"blueprint存在={bool(blueprint)}"
        )

        # 更新Header信息
        title = self.project_data.get('title', '未命名项目')
        self.project_title.setText(title)

        # 获取项目类型描述
        project_type_desc = blueprint.get('project_type_desc', '未知类型')
        status = self.project_data.get('status', 'draft')

        self.type_tag.setText(project_type_desc)
        self.status_tag.setText(get_project_status_text(status))
        self._updateStatusTagStyle(status)

        # 刷新当前section
        if self.active_section in self.section_widgets:
            old_widget = self.section_widgets.pop(self.active_section)
            self.content_stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.loadSection(self.active_section)

    def _onProjectBasicInfoError(self, error_msg):
        """项目基本信息加载失败"""
        self.hide_loading(self._load_project_op_id)
        self._load_project_op_id = None
        logger.error(f"加载项目基本信息失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    def get_blueprint(self):
        """获取编程项目蓝图数据"""
        if not self.project_data:
            return {}
        return self.project_data.get('blueprint') or {}

    def refreshProject(self):
        """刷新项目数据"""
        logger.info(f"refreshProject: project_id={self.project_id}")

        # 清除缓存的Section
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

        # 重新加载
        self.loadProjectBasicInfo()
        self.loadSection(self.active_section)

    def goBackToWorkspace(self):
        """返回首页"""
        self.navigateTo('HOME')

    def openCodingDesk(self):
        """打开编程写作台"""
        logger.info(f"打开编程写作台: project_id={self.project_id}")
        self.navigateTo('CODING_DESK', project_id=self.project_id)

    def onSyncRAG(self):
        """同步RAG数据"""
        logger.info(f"同步RAG数据: project_id={self.project_id}")

        self.show_loading("正在同步RAG数据...")

        worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag_data,
            self.project_id,
            force=True
        )
        worker.success.connect(self._onRAGSyncSuccess)
        worker.error.connect(self._onRAGSyncError)
        self.worker_manager.start(worker, 'sync_rag')

    def _onRAGSyncSuccess(self, result):
        """RAG同步成功"""
        self.hide_loading()
        added = result.get('added', 0)
        total = result.get('total_items', 0)
        MessageService.show_success(self, f"RAG同步完成：已入库 {added}/{total} 项数据")

    def _onRAGSyncError(self, error_msg: str):
        """RAG同步失败"""
        self.hide_loading()
        logger.error(f"RAG同步失败: {error_msg}")
        MessageService.show_error(self, f"RAG同步失败：{error_msg}")

    def _on_regenerate_blueprint(self, preference: str):
        """处理蓝图重新生成请求

        Args:
            preference: 用户的偏好指导（可为空字符串）
        """
        logger.info(f"重新生成蓝图: project_id={self.project_id}, preference={preference}")

        self.show_loading("正在重新生成架构设计蓝图...")

        worker = AsyncAPIWorker(
            self.api_client.generate_coding_blueprint,
            self.project_id,
            allow_incomplete=True,
            preference=preference if preference else None
        )
        worker.success.connect(self._on_blueprint_regenerated)
        worker.error.connect(self._on_blueprint_regenerate_error)
        self.worker_manager.start(worker, 'regenerate_blueprint')

    def _on_blueprint_regenerated(self, result):
        """蓝图重新生成成功"""
        self.hide_loading()
        logger.info("蓝图重新生成成功")
        MessageService.show_success(self, "架构设计蓝图已重新生成")
        self.refreshProject()

    def _on_blueprint_regenerate_error(self, error_msg: str):
        """蓝图重新生成失败"""
        self.hide_loading()
        logger.error(f"蓝图重新生成失败: {error_msg}")
        MessageService.show_error(self, f"重新生成失败：{error_msg}")

    def _on_file_clicked(self, file_id: int):
        """处理文件点击事件 - 跳转到文件Prompt生成页面

        Args:
            file_id: 源文件ID
        """
        logger.info(f"文件点击: file_id={file_id}, project_id={self.project_id}")

        # 跳转到CodingDesk页面
        self.navigateTo('CODING_DESK', project_id=self.project_id, file_id=file_id)

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            self.refreshProject()

        if 'section' in params:
            section_id = params['section']
            valid_sections = ['overview', 'architecture', 'directory', 'generation']
            if section_id in valid_sections:
                self.switchSection(section_id)

    def onHide(self):
        """页面隐藏时清理资源"""
        logger.debug("CodingDetail.onHide() called for project_id=%s", self.project_id)

        # 停止所有进行中的Worker
        if hasattr(self, 'worker_manager'):
            self.worker_manager.stop_all()

        # 清理所有section widgets
        for section_id, section in self.section_widgets.items():
            try:
                if section and hasattr(section, 'cleanup'):
                    section.cleanup()
            except RuntimeError:
                logger.debug("%s section已被删除", section_id)

        logger.debug("CodingDetail.onHide() completed")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.onHide()
        super().closeEvent(event)


__all__ = [
    "CodingDetail",
]
