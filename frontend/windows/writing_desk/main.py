"""
写作台主类

集成Header、Sidebar、Workspace，提供完整的章节写作功能
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QProgressDialog,
    QApplication, QFileDialog
)
from PyQt6.QtCore import Qt
from pages.base_page import BasePage
from api.client import ArborisAPIClient
from utils.async_worker import AsyncAPIWorker
from utils.error_handler import handle_errors
from utils.message_service import MessageService, confirm
from themes.theme_manager import theme_manager

from .header import WDHeader
from .sidebar import WDSidebar
from .workspace import WDWorkspace

logger = logging.getLogger(__name__)


class WritingDesk(BasePage):
    """写作台页面 - 禅意风格"""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = ArborisAPIClient()
        self.project = None
        self.selected_chapter_number = None
        self.generating_chapter = None

        # 异步任务管理 - 为不同操作维护独立的worker引用
        self.current_worker = None  # 用于评审和重试等长时间操作
        self.select_version_worker = None  # 用于版本选择
        self.edit_content_worker = None  # 用于内容编辑

        self.setupUI()
        self.loadProject()

    def setupUI(self):
        """初始化UI"""
        logger.info("WritingDesk.setupUI 被调用")
        # 如果布局不存在，创建UI结构
        if not self.layout():
            logger.info("布局不存在，调用 _create_ui_structure")
            self._create_ui_structure()
        else:
            logger.info("布局已存在，跳过 _create_ui_structure")
        # 总是应用主题样式
        logger.info("应用主题样式")
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        logger.info("WritingDesk._create_ui_structure 开始执行")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = WDHeader()
        self.header.goBackClicked.connect(self.goBack)
        self.header.viewDetailClicked.connect(self.openProjectDetail)
        self.header.exportClicked.connect(self.exportNovel)
        main_layout.addWidget(self.header)

        # 主内容区 - 紧凑布局
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)  # 从24减少到16
        content_layout.setSpacing(16)  # 从24减少到16

        # Sidebar
        self.sidebar = WDSidebar()
        self.sidebar.chapterSelected.connect(self.onChapterSelected)
        self.sidebar.generateChapter.connect(self.onGenerateChapter)
        self.sidebar.generateOutline.connect(self.onGenerateOutline)
        content_layout.addWidget(self.sidebar)

        # Workspace
        self.workspace = WDWorkspace()
        self.workspace.generateChapterRequested.connect(self.onGenerateChapter)
        self.workspace.saveContentRequested.connect(self.onSaveContent)
        self.workspace.selectVersion.connect(self.onSelectVersion)
        self.workspace.evaluateChapter.connect(self.onEvaluateChapter)
        self.workspace.retryVersion.connect(self.onRetryVersion)
        self.workspace.editContent.connect(self.onEditContent)
        self.workspace.setProjectId(self.project_id)
        content_layout.addWidget(self.workspace, stretch=1)

        main_layout.addWidget(self.content_widget, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 整体背景 - 使用渐变
        from themes.modern_effects import ModernEffects
        gradient_colors = theme_manager.current_theme.BG_GRADIENT

        # 主窗口背景
        self.setStyleSheet(f"""
            WritingDesk {{
                background: {ModernEffects.linear_gradient(gradient_colors, 180)};
            }}
        """)

        if hasattr(self, 'content_widget'):
            self.content_widget.setStyleSheet(f"""
                QWidget {{
                    background: transparent;
                }}
            """)

    @handle_errors("加载项目")
    def loadProject(self):
        """加载项目数据"""
        logger.info(f"WritingDesk.loadProject被调用, project_id={self.project_id}")
        self.project = self.api_client.get_novel(self.project_id)

        logger.info(f"项目数据加载成功")
        logger.info(f"项目键: {list(self.project.keys()) if isinstance(self.project, dict) else 'NOT A DICT'}")

        blueprint = self.project.get('blueprint', {})
        if blueprint:
            chapter_outline = blueprint.get('chapter_outline', [])
            logger.info(f"blueprint.chapter_outline数量: {len(chapter_outline)}")
        else:
            logger.warning("blueprint不存在")

        logger.info("调用 header.setProject")
        self.header.setProject(self.project)

        logger.info("调用 sidebar.setProject")
        self.sidebar.setProject(self.project)

    def onChapterSelected(self, chapter_number):
        """章节被选中"""
        self.selected_chapter_number = chapter_number
        self.workspace.loadChapter(chapter_number)

    def onGenerateChapter(self, chapter_number):
        """生成章节 - 使用同步模式"""
        # 防止快速点击导致多个生成任务同时运行
        if self.generating_chapter is not None:
            MessageService.show_warning(
                self,
                f"正在生成第{self.generating_chapter}章，请等待完成后再生成其他章节",
                "提示"
            )
            return

        if not confirm(
            self,
            f"确定要生成第{chapter_number}章吗？这可能需要几分钟时间。",
            "确认生成"
        ):
            return

        # 标记正在生成的章节
        self.generating_chapter = chapter_number
        self.sidebar.setGeneratingChapter(chapter_number)

        # 定义生成任务
        def generate_task():
            return self.api_client.generate_chapter(
                project_id=self.project_id,
                chapter_number=chapter_number
            )

        # 定义成功回调
        def on_success(result):
            self.generating_chapter = None
            self.sidebar.clearGeneratingState()
            MessageService.show_operation_success(self, f"第{chapter_number}章生成")
            self.loadProject()
            self.workspace.loadChapter(chapter_number)

        # 定义错误回调
        def on_error(error_msg):
            self.generating_chapter = None
            self.sidebar.clearGeneratingState()
            MessageService.show_error(self, f"生成失败：{error_msg}", "错误")

        # 使用AsyncWorker在后台线程执行
        worker = AsyncAPIWorker(generate_task)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        # 显示加载对话框
        loading_dialog = QProgressDialog(
            f"正在生成第{chapter_number}章，请稍候...\n这可能需要几分钟时间。",
            None,  # 无取消按钮
            0, 0,
            self
        )
        loading_dialog.setWindowTitle("生成中")
        loading_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        loading_dialog.setCancelButton(None)
        loading_dialog.setMinimumDuration(0)
        loading_dialog.setValue(0)

        # Worker完成后关闭对话框
        worker.finished.connect(loading_dialog.close)

        # 启动Worker
        worker.start()

        # 显示对话框（会阻塞直到Worker完成）
        loading_dialog.exec()

    def onGenerateOutline(self):
        """生成章节大纲"""
        MessageService.show_info(self, "章节大纲生成功能请在项目详情页操作", "提示")

    @handle_errors("保存章节内容", show_message=True)
    def onSaveContent(self, chapter_number, content):
        """保存章节内容"""
        self.api_client.update_chapter_content(self.project_id, chapter_number, content)

    def onSelectVersion(self, version_index):
        """选择版本（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在确认第{self.selected_chapter_number}章版本{version_index + 1}...")

        # 创建异步工作线程（保持引用防止被垃圾回收）
        self.select_version_worker = AsyncAPIWorker(
            self.api_client.select_chapter_version,
            self.project_id,
            self.selected_chapter_number,
            version_index
        )
        self.select_version_worker.success.connect(lambda r: self.onSelectVersionSuccess(r, version_index))
        self.select_version_worker.error.connect(self.onSelectVersionError)

        # 启动任务
        self.select_version_worker.start()

    def onSelectVersionSuccess(self, result, version_index):
        """版本选择成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "版本已确认！")

        # 清理工作线程引用
        if self.select_version_worker:
            self.select_version_worker = None

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onSelectVersionError(self, error_msg):
        """版本选择失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"选择版本失败：\n\n{error_msg}", "错误")

        # 清理工作线程引用
        if self.select_version_worker:
            self.select_version_worker = None

    def onEvaluateChapter(self):
        """评审章节（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在评审第{self.selected_chapter_number}章...")

        # 创建异步工作线程
        self.current_worker = AsyncAPIWorker(
            self.api_client.evaluate_chapter,
            self.project_id,
            self.selected_chapter_number
        )
        self.current_worker.success.connect(self.onEvaluateSuccess)
        self.current_worker.error.connect(self.onEvaluateError)

        # 启动评审任务
        self.current_worker.start()

    def onEvaluateSuccess(self, result):
        """章节评审成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "评审完成！")

        # 清理工作线程
        if self.current_worker:
            self.current_worker = None

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onEvaluateError(self, error_msg):
        """章节评审失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"评审失败：\n\n{error_msg}", "错误")

        # 清理工作线程
        if self.current_worker:
            self.current_worker = None

    def onEditContent(self, new_content):
        """编辑章节内容（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在保存第{self.selected_chapter_number}章内容...")

        # 创建异步工作线程（保持引用防止被垃圾回收）
        self.edit_content_worker = AsyncAPIWorker(
            self.api_client.update_chapter,
            self.project_id,
            self.selected_chapter_number,
            new_content
        )
        self.edit_content_worker.success.connect(self.onEditContentSuccess)
        self.edit_content_worker.error.connect(self.onEditContentError)

        # 启动任务
        self.edit_content_worker.start()

    def onEditContentSuccess(self, result):
        """编辑内容成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "内容已保存！")

        # 清理工作线程引用
        if self.edit_content_worker:
            self.edit_content_worker = None

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onEditContentError(self, error_msg):
        """编辑内容失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"保存失败：\n\n{error_msg}", "错误")

        # 清理工作线程引用
        if self.edit_content_worker:
            self.edit_content_worker = None

    def onRetryVersion(self, version_index):
        """重试章节版本（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        if not confirm(
            self,
            f"确定要重新生成第{self.selected_chapter_number}章的版本{version_index + 1}吗？\n\n这将替换当前版本的内容。",
            "确认重新生成"
        ):
            return

        # 询问用户输入优化提示词
        from PyQt6.QtWidgets import QInputDialog
        custom_prompt, ok = QInputDialog.getMultiLineText(
            self,
            "优化方向",
            f"请输入第{self.selected_chapter_number}章版本{version_index + 1}的优化方向：\n\n"
            "（可选，留空则按原设定重新生成）\n\n"
            "示例：\n"
            "- 增加心理描写\n"
            "- 加快节奏，减少环境描写\n"
            "- 强化角色冲突\n"
            "- 增加悬念感",
            ""
        )

        if not ok:
            return

        # 显示加载动画
        loading_msg = f"正在重新生成第{self.selected_chapter_number}章版本{version_index + 1}..."
        if custom_prompt.strip():
            loading_msg += f"\n优化方向：{custom_prompt[:50]}..."
        self.show_loading(loading_msg)

        # 创建异步工作线程
        self.current_worker = AsyncAPIWorker(
            self.api_client.retry_chapter_version,
            self.project_id,
            self.selected_chapter_number,
            version_index,
            custom_prompt.strip() if custom_prompt.strip() else None
        )
        self.current_worker.success.connect(lambda r: self.onRetrySuccess(r, version_index))
        self.current_worker.error.connect(self.onRetryError)

        # 启动重试任务
        self.current_worker.start()

    def onRetrySuccess(self, result, version_index):
        """版本重试成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_operation_success(
            self,
            f"第{self.selected_chapter_number}章版本{version_index + 1}重新生成"
        )

        # 清理工作线程
        if self.current_worker:
            self.current_worker = None

        # 重新加载项目并刷新显示
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onRetryError(self, error_msg):
        """版本重试失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"重新生成失败：\n\n{error_msg}", "错误")

        # 清理工作线程
        if self.current_worker:
            self.current_worker = None

    def openProjectDetail(self):
        """打开项目详情页"""
        self.navigateTo('DETAIL', project_id=self.project_id)

    def exportNovel(self, format_type):
        """导出小说"""
        @handle_errors("导出小说")
        def _export():
            content = self.api_client.export_novel(self.project_id, format_type)

            title = self.project.get('title', '小说')
            ext = 'md' if format_type == 'markdown' else 'txt'
            default_name = f"{title}.{ext}"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存导出文件",
                default_name,
                f"{'Markdown' if format_type == 'markdown' else '文本'}文件 (*.{ext})"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        _export()

    def onHide(self):
        """页面隐藏时清理资源"""
        # 停止所有正在运行的workers，防止信号发射到已删除的页面
        self._cleanup_workers()

    def _cleanup_workers(self):
        """清理所有异步工作线程"""
        workers = [
            ('current_worker', self.current_worker),
            ('select_version_worker', self.select_version_worker),
            ('edit_content_worker', self.edit_content_worker),
        ]

        for name, worker in workers:
            if worker is not None:
                try:
                    # 断开所有信号连接，防止回调到已删除的对象
                    worker.blockSignals(True)
                    # 如果线程正在运行，等待它完成（设置超时避免永久阻塞）
                    if worker.isRunning():
                        worker.quit()
                        worker.wait(1000)  # 最多等待1秒
                        if worker.isRunning():
                            worker.terminate()  # 强制终止
                            worker.wait(500)
                    logger.debug(f"清理worker: {name}")
                except Exception as e:
                    logger.warning(f"清理worker {name} 时发生错误: {e}")

        # 清空引用
        self.current_worker = None
        self.select_version_worker = None
        self.edit_content_worker = None

        # 隐藏加载动画（如果有）
        self.hide_loading()

        # 清除生成状态
        self.generating_chapter = None
        if hasattr(self, 'sidebar'):
            self.sidebar.clearGeneratingState()

    def __del__(self):
        """析构函数，确保资源被释放"""
        try:
            self._cleanup_workers()
            if hasattr(self, 'api_client') and self.api_client:
                self.api_client.close()
        except Exception:
            pass  # 忽略析构时的错误

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            if hasattr(self, 'workspace'):
                self.workspace.setProjectId(self.project_id)
            self.loadProject()
