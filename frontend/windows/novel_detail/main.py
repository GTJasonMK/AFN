"""
项目详情主页面 - 现代化设计

采用顶部Tab导航，提高空间利用率
集成所有Section组件，提供流畅的浏览体验

架构说明：
- NovelDetail: 主页面类，负责UI布局和生命周期
- HeaderManagerMixin: Header创建和样式
- TabManagerMixin: Tab导航管理
- SectionLoaderMixin: Section加载
- AvatarHandlerMixin: 头像处理
- EditDispatcherMixin: 编辑请求分发
- SaveManagerMixin: 保存管理
- BlueprintRefinerMixin: 蓝图优化
- ImportAnalyzerMixin: 导入分析
"""

import logging

from PyQt6.QtWidgets import QVBoxLayout, QStackedWidget
from PyQt6.QtWidgets import QApplication

from pages.base_page import BasePage
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.message_service import MessageService
from utils.formatters import get_project_status_text
from utils.async_worker import AsyncAPIWorker
from utils.constants import WorkerTimeouts

from .dirty_tracker import DirtyTracker
from .mixins import (
    HeaderManagerMixin,
    TabManagerMixin,
    SectionLoaderMixin,
    AvatarHandlerMixin,
    EditDispatcherMixin,
    SaveManagerMixin,
    BlueprintRefinerMixin,
    ImportAnalyzerMixin,
)

logger = logging.getLogger(__name__)


class NovelDetail(
    HeaderManagerMixin,
    TabManagerMixin,
    SectionLoaderMixin,
    AvatarHandlerMixin,
    EditDispatcherMixin,
    SaveManagerMixin,
    BlueprintRefinerMixin,
    ImportAnalyzerMixin,
    BasePage
):
    """项目详情页面 - 现代化设计

    布局：
    +------------------------------------------------------------------+
    | Header: 项目图标 | 标题/类型/状态 | 保存/返回/导出/优化/创作按钮  |
    +------------------------------------------------------------------+
    | Tab导航: 概览 | 世界观 | 角色 | 关系 | 章节大纲 | 已生成章节      |
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

        # 异步任务管理
        self.refine_worker = None  # 蓝图优化异步worker

        # 脏数据追踪器
        self.dirty_tracker = DirtyTracker()

        self.setupUI()
        self.loadProjectBasicInfo()
        self.loadSection('overview')

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次，优化版：分步创建避免卡顿）"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部Header（项目信息 + 操作按钮）
        self.createHeader()
        main_layout.addWidget(self.header)

        # 让出事件循环
        QApplication.processEvents()

        # Tab导航栏
        self.createTabBar()
        main_layout.addWidget(self.tab_bar)

        # 让出事件循环
        QApplication.processEvents()

        # 内容区域
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格 + 透明效果支持"""
        from PyQt6.QtCore import Qt
        from themes.modern_effects import ModernEffects

        bg_color = theme_manager.book_bg_primary()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = transparency_config.get("content_opacity", 0.95)

        if transparency_enabled:
            # 透明模式：使用RGBA背景色实现半透明效果
            # 当content_opacity=0时，页面完全透明，能看到桌面
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")

            # 设置WA_TranslucentBackground使透明生效（真正的窗口透明）
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            # 指定容器设置透明（不使用findChildren避免影响其他页面）
            transparent_containers = ['header', 'tab_bar', 'content_stack']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)
                    if container_name == 'content_stack':
                        container.setStyleSheet("background-color: transparent;")
        else:
            # 普通模式：使用实色背景，恢复背景填充
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            # 恢复容器的背景填充
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
        """加载项目基本信息（异步非阻塞，带加载指示器）"""
        # 显示加载动画
        self.show_loading("正在加载项目信息...")

        # 使用异步worker加载项目，避免阻塞UI线程
        worker = AsyncAPIWorker(self.api_client.get_novel, self.project_id)
        worker.success.connect(self._onProjectBasicInfoLoaded)
        worker.error.connect(self._onProjectBasicInfoError)

        # 保持worker引用，防止被垃圾回收
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _onProjectBasicInfoLoaded(self, response):
        """项目基本信息加载成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        self.project_data = response

        # 调试日志
        blueprint = self.project_data.get('blueprint', {})
        chapter_outline = blueprint.get('chapter_outline', [])
        logger.info(
            f"loadProjectBasicInfo: project_id={self.project_id}, "
            f"status={self.project_data.get('status')}, "
            f"blueprint存在={bool(blueprint)}, "
            f"chapter_outline数量={len(chapter_outline)}"
        )

        # 更新Header信息
        title = self.project_data.get('title', '未命名项目')
        self.project_title.setText(title)

        genre = self.project_data.get('blueprint', {}).get('genre', '未知类型')
        status = self.project_data.get('status', 'draft')

        self.genre_tag.setText(genre)
        self.status_tag.setText(get_project_status_text(status))

        # 根据状态更新状态标签样式
        self._updateStatusTagStyle(status)

        # 根据项目类型动态调整按钮可见性
        is_imported = self.project_data.get('is_imported', False)
        analysis_status = self.project_data.get('import_analysis_status', '')
        analysis_completed = analysis_status == 'completed'

        # 导入项目且分析未完成时的按钮逻辑
        if is_imported and not analysis_completed:
            # 显示"开始分析"或"继续分析"按钮
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setVisible(True)
                if analysis_status == 'analyzing':
                    self.analyze_btn.setText("分析中...")
                    self.analyze_btn.setEnabled(False)
                elif analysis_status in ('failed', 'cancelled'):
                    # 之前分析中断，显示"继续分析"
                    self.analyze_btn.setText("继续分析")
                    self.analyze_btn.setEnabled(True)
                else:
                    self.analyze_btn.setText("开始分析")
                    self.analyze_btn.setEnabled(True)
            # 隐藏"优化蓝图"按钮（没有蓝图可优化）
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setVisible(False)
            # 隐藏"开始创作"按钮（还没分析完）
            if hasattr(self, 'create_btn') and self.create_btn:
                self.create_btn.setVisible(False)
        else:
            # 非导入项目或分析已完成
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setVisible(False)
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setVisible(True)
            if hasattr(self, 'create_btn') and self.create_btn:
                self.create_btn.setVisible(True)

        # 加载头像（如果有）
        blueprint = self.project_data.get('blueprint', {})
        avatar_svg = blueprint.get('avatar_svg') if blueprint else None
        self._loadAvatar(avatar_svg)

        # 刷新当前显示的section（因为初始加载时project_data还是空的）
        if self.active_section in self.section_widgets:
            # 删除旧的section，重新创建
            old_widget = self.section_widgets.pop(self.active_section)
            self.content_stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.loadSection(self.active_section)

    def _onProjectBasicInfoError(self, error_msg):
        """项目基本信息加载失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        logger.error(f"加载项目基本信息失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    def refreshProject(self):
        """刷新项目数据"""
        logger.info(f"refreshProject被调用: project_id={self.project_id}, active_section={self.active_section}")

        # 保存当前section的状态（如tab索引）
        saved_section_state = {}
        if self.active_section == 'chapter_outline' and 'chapter_outline' in self.section_widgets:
            section = self.section_widgets['chapter_outline']
            if hasattr(section, 'getCurrentTabIndex'):
                saved_section_state['tab_index'] = section.getCurrentTabIndex()
                logger.info(f"保存章节大纲tab状态: tab_index={saved_section_state['tab_index']}")

        # 保存状态到实例变量，供后续创建section时使用
        self._saved_section_state = saved_section_state

        # 安全地停止所有section的异步任务
        for section_id, widget in list(self.section_widgets.items()):
            try:
                if widget is not None and hasattr(widget, 'stopAllTasks'):
                    widget.stopAllTasks()
            except RuntimeError:
                logger.debug(f"section {section_id} 已被删除，跳过清理")
            except Exception as e:
                logger.warning(f"停止section {section_id} 异步任务时出错: {e}")

        # 清除缓存的Section widgets
        self.section_widgets.clear()

        # 安全地移除content_stack中的widgets
        while self.content_stack.count() > 0:
            try:
                widget = self.content_stack.widget(0)
                if widget is not None:
                    self.content_stack.removeWidget(widget)
                    widget.deleteLater()
                else:
                    # widget为None，直接跳出循环避免无限循环
                    break
            except RuntimeError:
                logger.debug("widget已被删除，跳过")
                break
            except Exception as e:
                logger.warning(f"移除widget时出错: {e}")
                break

        # 重新加载
        try:
            logger.info("开始重新加载项目基本信息")
            self.loadProjectBasicInfo()
            logger.info(f"重新加载section: {self.active_section}")
            self.loadSection(self.active_section)
            logger.info("refreshProject完成")
        except Exception as e:
            logger.error(f"刷新项目数据时出错: {e}", exc_info=True)

    def openWritingDesk(self):
        """打开写作台"""
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('WRITING_DESK', project_id=self.project_id)

    def goBackToWorkspace(self):
        """返回首页"""
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('HOME')

    def goToWorkspace(self):
        """返回首页"""
        logger.info("goToWorkspace called, navigating to HOME")
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('HOME')

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            self.refreshProject()

        # 支持通过section参数切换到指定Tab
        if 'section' in params:
            section_id = params['section']
            # 验证section_id是否有效
            valid_sections = ['overview', 'world_setting', 'characters', 'relationships', 'chapter_outline', 'chapters']
            if section_id in valid_sections:
                self.switchSection(section_id)

    def onHide(self):
        """页面隐藏时清理资源"""
        logger.debug("NovelDetail.onHide() called for project_id=%s", self.project_id)

        # 清理蓝图优化worker
        try:
            if self.refine_worker and self.refine_worker.isRunning():
                self.refine_worker.cancel()
                self.refine_worker.quit()
                self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
        except RuntimeError:
            pass  # C++对象已被删除，忽略
        except Exception as e:
            logger.warning("清理refine_worker时出错: %s", str(e))
        finally:
            self.refine_worker = None

        # 安全地清理所有section widgets
        try:
            for section_id, section in self.section_widgets.items():
                try:
                    if section is not None and hasattr(section, 'cleanup'):
                        section.cleanup()
                except RuntimeError:
                    # C++对象已被删除
                    logger.debug("%s section已被删除，跳过清理", section_id)
                except Exception as e:
                    logger.warning("清理%s section时出错: %s", section_id, str(e))
        except Exception as e:
            logger.warning("访问section_widgets时出错: %s", str(e))

        logger.debug("NovelDetail.onHide() completed")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 检查未保存的修改
        if self.dirty_tracker.is_dirty():
            if not self._checkUnsavedChanges():
                event.ignore()
                return
        self.onHide()
        super().closeEvent(event)


__all__ = [
    "NovelDetail",
]
