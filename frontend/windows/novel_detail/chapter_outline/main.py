"""
章节大纲 Section - 重构版（横条布局）

管理章节大纲的生成、展示和编辑，支持长篇和短篇流程
采用横条布局设计，统一的三按钮操作栏

架构说明：
- 主类 ChapterOutlineSection 负责UI布局和状态管理
- PartOutlineHandlerMixin 负责部分大纲的生成、继续生成、重新生成和删除
- ChapterOutlineHandlerMixin 负责章节大纲的生成、继续生成、编辑、重新生成和删除
"""

import logging

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget
from PyQt6.QtCore import pyqtSignal, QTimer

from api.manager import APIClientManager
from components.base import ThemeAwareWidget
from components.dialogs import LoadingDialog
from themes.theme_manager import theme_manager
from utils.message_service import MessageService
from utils.dpi_utils import dp, sp
from utils.constants import WorkerTimeouts
from utils.async_worker import AsyncAPIWorker
from utils.worker_manager import WorkerManager

from .components import LongNovelEmptyState, ShortNovelEmptyState, OutlineActionBar, OutlineListView
from .handlers import PartOutlineHandlerMixin, ChapterOutlineHandlerMixin

logger = logging.getLogger(__name__)


class ChapterOutlineSection(PartOutlineHandlerMixin, ChapterOutlineHandlerMixin, ThemeAwareWidget):
    """章节大纲组件 - 横条布局设计"""

    editRequested = pyqtSignal(str, str, object)
    refreshRequested = pyqtSignal()
    addRequested = pyqtSignal()

    def __init__(self, outline=None, blueprint=None, project_id='', editable=True, initial_tab_index=0, parent=None):
        self.outline = outline or []
        self.blueprint = blueprint or {}
        self.project_id = project_id
        self.editable = editable
        self._initial_tab_index = initial_tab_index  # 保存初始tab索引

        logger.info(
            f"ChapterOutlineSection初始化: project_id={project_id}, "
            f"outline章节数={len(self.outline)}, "
            f"needs_part_outlines={self.blueprint.get('needs_part_outlines', False)}, "
            f"part_outlines数={len(self.blueprint.get('part_outlines', []))}, "
            f"initial_tab_index={initial_tab_index}"
        )

        # UI模式: 'long' or 'short'
        self.current_mode = None

        # UI组件引用
        self._empty_state = None
        self._part_action_bar = None
        self._chapter_action_bar = None
        self._part_list = None
        self._chapter_list = None
        self._tab_widget = None
        self._max_covered_chapter = 0  # 部分大纲覆盖的最大章节数

        # 进度轮询相关
        self._progress_timer = None
        self._progress_dialog = None

        # 异步任务引用（防止被垃圾回收）
        self._generate_worker = None
        self._sse_worker = None  # SSE流式进度worker

        # 先调用父类初始化
        super().__init__(parent)

        # 初始化服务
        self.api_client = APIClientManager.get_client()
        self.worker_manager = WorkerManager(self)

        # 初始化UI
        self.setupUI()

        # 延迟检查部分大纲生成状态
        QTimer.singleShot(100, self._check_generation_status)

    # ========== UI结构 ==========

    def _create_ui_structure(self):
        """创建UI结构"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(dp(16))

        # 判断模式并创建对应UI
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        self.current_mode = 'long' if needs_part_outlines else 'short'

        if self.current_mode == 'long':
            self._create_long_novel_ui()
        else:
            self._create_short_novel_ui()

    def _create_long_novel_ui(self):
        """创建长篇小说UI（带Tab切换）"""
        part_outlines = self.blueprint.get('part_outlines', [])

        logger.info(
            f"创建长篇小说UI: "
            f"part_outlines数量={len(part_outlines)}, "
            f"chapter_outline数量={len(self.outline)}"
        )

        if not part_outlines:
            # 显示空状态
            logger.info("part_outlines为空，显示空状态")
            self._empty_state = LongNovelEmptyState()
            self._empty_state.actionClicked.connect(self._on_generate_part_outlines)
            self._main_layout.addWidget(self._empty_state)
        else:
            # 使用Tab切换部分大纲和章节大纲
            self._tab_widget = QTabWidget()
            self._tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: none;
                    background: transparent;
                }}
                QTabBar::tab {{
                    background: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_SECONDARY};
                    padding: {dp(10)}px {dp(20)}px;
                    border: none;
                    border-top-left-radius: {dp(8)}px;
                    border-top-right-radius: {dp(8)}px;
                    font-size: {sp(14)}px;
                    font-weight: 600;
                    margin-right: {dp(4)}px;
                }}
                QTabBar::tab:selected {{
                    background: {theme_manager.BG_CARD};
                    color: {theme_manager.PRIMARY};
                }}
                QTabBar::tab:hover:!selected {{
                    background: {theme_manager.BG_SECONDARY};
                }}
            """)

            # Tab 1: 部分大纲
            part_tab = QWidget()
            part_layout = QVBoxLayout(part_tab)
            part_layout.setContentsMargins(0, dp(16), 0, 0)
            part_layout.setSpacing(dp(16))

            # 部分大纲操作栏（显示继续生成按钮，支持增量生成，不显示新增按钮）
            total_parts = len(part_outlines)
            # 计算目标总部分数（基于蓝图的总章节数）
            total_chapters = self.blueprint.get('total_chapters', 0)
            chapters_per_part = self.blueprint.get('chapters_per_part', 25)
            import math
            target_total_parts = math.ceil(total_chapters / chapters_per_part) if total_chapters > 0 else total_parts

            self._part_action_bar = OutlineActionBar(
                title="部分大纲",
                current_count=total_parts,
                total_count=target_total_parts,
                outline_type="part",
                editable=self.editable,
                show_continue_button=True,  # 启用继续生成按钮
                show_add_button=False  # 部分大纲不支持手动新增
            )
            self._part_action_bar.continueGenerateClicked.connect(self._on_continue_generate_parts)
            self._part_action_bar.regenerateLatestClicked.connect(self._on_regenerate_latest_parts)
            self._part_action_bar.deleteLatestClicked.connect(self._on_delete_latest_parts)
            part_layout.addWidget(self._part_action_bar)

            # 部分大纲列表
            self._part_list = OutlineListView(part_outlines, item_type="part")
            part_layout.addWidget(self._part_list, stretch=1)

            self._tab_widget.addTab(part_tab, f"部分大纲 ({total_parts})")

            # Tab 2: 章节大纲
            chapter_tab = QWidget()
            chapter_layout = QVBoxLayout(chapter_tab)
            chapter_layout.setContentsMargins(0, dp(16), 0, 0)
            chapter_layout.setSpacing(dp(16))

            # 计算部分大纲覆盖的最大章节数
            # 章节大纲只能生成到已有部分大纲覆盖的范围内
            max_covered_chapter = 0
            for part in part_outlines:
                end_chapter = part.get('end_chapter', 0)
                if end_chapter > max_covered_chapter:
                    max_covered_chapter = end_chapter

            # 章节大纲操作栏 - 使用部分大纲覆盖范围作为上限
            total_chapters = self.blueprint.get('total_chapters', 0)
            # 如果部分大纲覆盖范围小于总章节数，显示覆盖范围
            effective_total = max_covered_chapter if max_covered_chapter > 0 else total_chapters
            self._max_covered_chapter = max_covered_chapter  # 保存供后续使用

            self._chapter_action_bar = OutlineActionBar(
                title="章节大纲",
                current_count=len(self.outline),
                total_count=effective_total,
                outline_type="chapter",
                editable=self.editable
            )
            self._chapter_action_bar.addOutlineClicked.connect(self._on_add_chapter_outline)
            self._chapter_action_bar.continueGenerateClicked.connect(self._on_continue_generate_chapters)
            self._chapter_action_bar.regenerateLatestClicked.connect(self._on_regenerate_latest_chapters)
            self._chapter_action_bar.deleteLatestClicked.connect(self._on_delete_latest_chapters)
            chapter_layout.addWidget(self._chapter_action_bar)

            # 章节大纲列表
            self._chapter_list = OutlineListView(self.outline, item_type="chapter")
            self._chapter_list.editRequested.connect(self._on_chapter_edit_requested)
            chapter_layout.addWidget(self._chapter_list, stretch=1)

            # Tab标题显示当前进度和可生成范围
            if max_covered_chapter > 0 and max_covered_chapter < total_chapters:
                tab_title = f"章节大纲 ({len(self.outline)}/{max_covered_chapter}，共{total_chapters}章)"
            else:
                tab_title = f"章节大纲 ({len(self.outline)}/{total_chapters})"
            self._tab_widget.addTab(chapter_tab, tab_title)

            self._main_layout.addWidget(self._tab_widget, stretch=1)
            logger.info("长篇小说UI创建完成")

    def _create_short_novel_ui(self):
        """创建短篇小说UI"""
        if not self.outline:
            # 显示空状态
            self._empty_state = ShortNovelEmptyState()
            self._empty_state.actionClicked.connect(self._on_generate_chapter_outlines)
            self._main_layout.addWidget(self._empty_state)
        else:
            # 章节大纲操作栏
            total_chapters = len(self.outline)
            self._chapter_action_bar = OutlineActionBar(
                title="章节大纲",
                current_count=total_chapters,
                total_count=total_chapters,
                outline_type="chapter",
                editable=self.editable
            )
            self._chapter_action_bar.addOutlineClicked.connect(self._on_add_chapter_outline)
            self._chapter_action_bar.continueGenerateClicked.connect(self._on_continue_generate_chapters)
            self._chapter_action_bar.regenerateLatestClicked.connect(self._on_regenerate_latest_chapters)
            self._chapter_action_bar.deleteLatestClicked.connect(self._on_delete_latest_chapters)
            self._main_layout.addWidget(self._chapter_action_bar)

            # 章节大纲列表
            self._chapter_list = OutlineListView(self.outline, item_type="chapter")
            self._chapter_list.editRequested.connect(self._on_chapter_edit_requested)
            self._main_layout.addWidget(self._chapter_list, stretch=1)

    def _apply_theme(self):
        """应用主题"""
        self._rebuild_ui()

    def _rebuild_ui(self):
        """重建UI"""
        # 保存当前Tab索引（优先使用当前显示的，其次使用初始化时传入的）
        saved_tab_index = self._initial_tab_index
        if self._tab_widget:
            saved_tab_index = self._tab_widget.currentIndex()

        self._clear_ui()

        if self.current_mode == 'long':
            self._create_long_novel_ui()
        else:
            self._create_short_novel_ui()

        # 恢复Tab索引
        if self._tab_widget and saved_tab_index > 0:
            # 确保索引不越界
            if saved_tab_index < self._tab_widget.count():
                self._tab_widget.setCurrentIndex(saved_tab_index)
                logger.debug(f"恢复tab索引: {saved_tab_index}")

    def getCurrentTabIndex(self):
        """获取当前tab索引（用于刷新时保存状态）"""
        if self._tab_widget:
            return self._tab_widget.currentIndex()
        return 0

    def _clear_ui(self):
        """清空UI"""
        layout = self.layout()
        if not layout:
            return

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        self._empty_state = None
        self._part_action_bar = None
        self._chapter_action_bar = None
        self._part_list = None
        self._chapter_list = None
        self._tab_widget = None
        self._max_covered_chapter = 0

    def _clear_layout(self, layout):
        """递归清空布局"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _run_async_action(
        self,
        api_func,
        *args,
        loading_message: str = "正在处理...",
        success_message: str = "操作成功",
        error_context: str = "操作",
        on_success=None,
        on_error=None,
        **kwargs
    ):
        """统一执行异步API调用"""
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message=loading_message,
            cancelable=True
        )
        loading_dialog.show()

        worker = AsyncAPIWorker(api_func, *args, **kwargs)

        def handle_success(result):
            loading_dialog.close()
            if success_message:
                MessageService.show_operation_success(self, success_message)
            if on_success:
                on_success(result)

        def handle_error(error_msg):
            loading_dialog.close()
            MessageService.show_api_error(self, error_msg, error_context)
            if on_error:
                on_error(error_msg)

        def handle_cancel():
            try:
                if worker.isRunning():
                    worker.cancel()
                    worker.quit()
                    worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass
            loading_dialog.close()

        worker.success.connect(handle_success)
        worker.error.connect(handle_error)
        loading_dialog.rejected.connect(handle_cancel)
        self.worker_manager.start(worker)
        return worker

    # ========== 部分大纲操作（由PartOutlineHandlerMixin提供） ==========
    # ========== 章节大纲操作（由ChapterOutlineHandlerMixin提供） ==========

    def cleanup(self):
        """清理所有资源（供父组件在页面隐藏时调用）"""
        self._cleanup_part_outline_sse()
        self._cleanup_chapter_outline_sse()
        if self.worker_manager:
            self.worker_manager.cleanup_all()
        super().cleanup()

    # ========== 状态检查 ==========

    def _check_generation_status(self):
        """检查部分大纲生成状态"""
        # 只有长篇模式且需要部分大纲时才检查
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        if not needs_part_outlines:
            logger.debug("短篇模式，跳过部分大纲生成状态检查")
            return

        # 如果已有部分大纲，检查是否正在生成中
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            logger.debug("尚未开始生成部分大纲，跳过状态检查")
            return

        try:
            status_data = self.api_client.get_part_outline_generation_status(self.project_id)
            status = status_data.get('status', 'pending')
            completed_parts = status_data.get('completed_parts', 0)
            total_parts = status_data.get('total_parts', 0)
            parts = status_data.get('parts', [])

            if status == 'partial' and completed_parts < total_parts:
                has_generating = any(p.get('generation_status') == 'generating' for p in parts)
                if has_generating:
                    logger.info(
                        f"检测到正在生成的部分大纲任务 ({completed_parts}/{total_parts})，自动开始轮询"
                    )
                    # 显示进度对话框
                    self._progress_dialog = LoadingDialog(
                        parent=self,
                        title="生成部分大纲",
                        message=f"正在生成部分大纲...\n已完成: {completed_parts} / {total_parts}",
                        cancelable=True
                    )
                    self._progress_dialog.rejected.connect(self._stop_progress_polling)
                    self._progress_dialog.show()
                    # 开始轮询
                    self._start_progress_polling()
        except Exception as e:
            logger.debug(f"检查部分大纲生成状态失败（正常情况，可忽略）: {e}")

    # ========== 公共方法 ==========

    def updateData(self, new_outline, new_blueprint):
        """更新数据并刷新显示"""
        self.outline = new_outline
        self.blueprint = new_blueprint

        needs_part_outlines = new_blueprint.get('needs_part_outlines', False)
        self.current_mode = 'long' if needs_part_outlines else 'short'

        self._rebuild_ui()

    def stopAllTasks(self):
        """停止所有异步任务"""
        self._stop_progress_polling()
        self._cleanup_chapter_outline_sse()
        self._cleanup_part_outline_sse()
        if self.worker_manager:
            self.worker_manager.stop_all()

        # 清理生成任务worker
        if self._generate_worker is not None:
            try:
                self._generate_worker.blockSignals(True)
                if self._generate_worker.isRunning():
                    self._generate_worker.quit()
                    self._generate_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except Exception as e:
                logger.warning(f"清理_generate_worker时出错: {e}")
            self._generate_worker = None

    def closeEvent(self, event):
        """组件关闭时清理资源"""
        logger.info("ChapterOutlineSection关闭，清理异步任务")
        self.stopAllTasks()
        super().closeEvent(event)
