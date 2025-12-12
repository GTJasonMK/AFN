"""
章节大纲 Section - 重构版（横条布局）

管理章节大纲的生成、展示和编辑，支持长篇和短篇流程
采用横条布局设计，统一的三按钮操作栏
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QTabWidget
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from api.manager import APIClientManager
from components.base import ThemeAwareWidget
from components.dialogs import IntInputDialog, InputDialog, LoadingDialog
from themes.theme_manager import theme_manager
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp, sp
from utils.sse_worker import SSEWorker
from utils.constants import WorkerTimeouts

from .async_helper import AsyncOperationHelper
from .empty_states import LongNovelEmptyState, ShortNovelEmptyState
from .action_bar import OutlineActionBar
from .outline_list import OutlineListView

import logging

logger = logging.getLogger(__name__)


class ChapterOutlineSection(ThemeAwareWidget):
    """章节大纲组件 - 横条布局设计"""

    editRequested = pyqtSignal(str, str, object)
    refreshRequested = pyqtSignal()
    addRequested = pyqtSignal()

    def __init__(self, outline=None, blueprint=None, project_id='', editable=True, parent=None):
        self.outline = outline or []
        self.blueprint = blueprint or {}
        self.project_id = project_id
        self.editable = editable

        logger.info(
            f"ChapterOutlineSection初始化: project_id={project_id}, "
            f"outline章节数={len(self.outline)}, "
            f"needs_part_outlines={self.blueprint.get('needs_part_outlines', False)}, "
            f"part_outlines数={len(self.blueprint.get('part_outlines', []))}"
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
        self.async_helper = AsyncOperationHelper(self)

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

            # 部分大纲操作栏（显示继续生成按钮，支持增量生成）
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
                show_continue_button=True  # 启用继续生成按钮
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
            self._chapter_action_bar.continueGenerateClicked.connect(self._on_continue_generate_chapters)
            self._chapter_action_bar.regenerateLatestClicked.connect(self._on_regenerate_latest_chapters)
            self._chapter_action_bar.deleteLatestClicked.connect(self._on_delete_latest_chapters)
            chapter_layout.addWidget(self._chapter_action_bar)

            # 章节大纲列表
            self._chapter_list = OutlineListView(self.outline, item_type="chapter")
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
            self._chapter_action_bar.continueGenerateClicked.connect(self._on_continue_generate_chapters)
            self._chapter_action_bar.regenerateLatestClicked.connect(self._on_regenerate_latest_chapters)
            self._chapter_action_bar.deleteLatestClicked.connect(self._on_delete_latest_chapters)
            self._main_layout.addWidget(self._chapter_action_bar)

            # 章节大纲列表
            self._chapter_list = OutlineListView(self.outline, item_type="chapter")
            self._main_layout.addWidget(self._chapter_list, stretch=1)

    def _apply_theme(self):
        """应用主题"""
        self._rebuild_ui()

    def _rebuild_ui(self):
        """重建UI"""
        # 保存当前Tab索引
        saved_tab_index = 0
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

    # ========== 部分大纲操作 ==========

    def _on_generate_part_outlines(self):
        """生成部分大纲"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        if total_chapters == 0:
            MessageService.show_warning(self, "无法获取总章节数，请先生成蓝图", "提示")
            return

        # 使用新的配置对话框（支持指定生成范围）
        from components.dialogs import PartOutlineConfigDialog
        result = PartOutlineConfigDialog.getConfigStatic(
            parent=self,
            total_chapters=total_chapters
        )
        if not result:
            return

        generate_chapters, chapters_per_part = result

        # 计算预计生成的部分数
        import math
        estimated_parts = math.ceil(generate_chapters / chapters_per_part)

        logger.info(f"开始生成部分大纲（使用SSE流式进度）: {generate_chapters}章, 每部分{chapters_per_part}章, 预计{estimated_parts}部分")

        # 显示带进度的加载对话框
        if generate_chapters < total_chapters:
            message = f"正在生成第1-{generate_chapters}章的部分大纲...\n预计生成 {estimated_parts} 个部分"
        else:
            message = f"正在准备生成 {estimated_parts} 个部分大纲..."

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="生成部分大纲",
            message=message,
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_part_outline_sse_cancelled)
        self._progress_dialog.show()

        # 使用SSE流式端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/parts/generate-stream"
        payload = {
            "total_chapters": generate_chapters,
            "chapters_per_part": chapters_per_part
        }

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_part_outline_progress)
        self._sse_worker.complete.connect(self._on_part_outline_complete)
        self._sse_worker.error_data.connect(self._on_part_outline_error)
        self._sse_worker.start()

    def _on_part_outline_progress(self, data: dict):
        """处理部分大纲生成进度更新"""
        if not self._progress_dialog:
            return

        status = data.get('status', '')
        current_part = data.get('current_part', 0)
        total_parts = data.get('total_parts', 0)
        message = data.get('message', '')

        if status == 'starting':
            progress_text = f"{message}\n预计生成 {total_parts} 个部分"
        elif status == 'generating':
            progress_text = f"正在生成第 {current_part}/{total_parts} 部分..."
        else:
            progress_text = message

        self._progress_dialog.setMessage(progress_text)

    def _on_part_outline_complete(self, data: dict):
        """部分大纲生成完成"""
        self._cleanup_part_outline_sse()

        message = data.get('message', '生成完成')
        total_parts = data.get('total_parts', 0)

        logger.info(f"部分大纲生成完成: {message}, 共{total_parts}部分")
        MessageService.show_operation_success(self, message)
        self.refreshRequested.emit()

    def _on_part_outline_error(self, error_data: dict):
        """部分大纲生成错误"""
        self._cleanup_part_outline_sse()

        error_msg = error_data.get('message', '未知错误')
        saved_count = error_data.get('saved_count', 0)
        saved_parts = error_data.get('saved_parts', [])

        logger.error(f"部分大纲生成失败: {error_msg}, 已保存 {saved_count} 部分")

        if saved_count > 0:
            saved_info = f"\n\n已成功保存 {saved_count} 个部分大纲。\n刷新页面可查看已保存的内容。"
            MessageService.show_api_error(self, f"{error_msg}{saved_info}", "生成部分大纲")
            self.refreshRequested.emit()
        else:
            MessageService.show_api_error(self, error_msg, "生成部分大纲")

    def _on_part_outline_sse_cancelled(self):
        """用户取消部分大纲生成"""
        logger.info("用户取消部分大纲生成")
        self._cleanup_part_outline_sse()

    def _cleanup_part_outline_sse(self):
        """清理部分大纲SSE相关资源"""
        if self._sse_worker:
            # SSEWorker.stop() 已经断开信号并关闭连接，无需 blockSignals
            self._sse_worker.stop()
            if self._sse_worker.isRunning():
                self._sse_worker.quit()
                self._sse_worker.wait(WorkerTimeouts.DEFAULT_MS)
            self._sse_worker = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _on_continue_generate_parts(self):
        """继续生成部分大纲（增量模式）- 使用专用的继续生成对话框"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        if total_chapters == 0:
            MessageService.show_warning(self, "无法获取总章节数，请先生成蓝图", "提示")
            return

        # 获取当前已覆盖的章节范围
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            # 如果没有部分大纲，应该用首次生成
            self._on_generate_part_outlines()
            return

        # 计算当前已覆盖到第几章
        current_covered_chapter = max(p.get('end_chapter', 0) for p in part_outlines)
        current_parts = len(part_outlines)
        chapters_per_part = self.blueprint.get('chapters_per_part', 25)

        if current_covered_chapter >= total_chapters:
            MessageService.show_warning(
                self,
                f"已生成所有部分大纲（覆盖到第{current_covered_chapter}章），无需继续生成",
                "提示"
            )
            return

        # 使用专用的继续生成配置对话框
        from components.dialogs import PartOutlineConfigDialog
        result = PartOutlineConfigDialog.getContinueConfigStatic(
            parent=self,
            total_chapters=total_chapters,
            current_covered_chapter=current_covered_chapter,
            current_parts=current_parts,
            chapters_per_part=chapters_per_part
        )
        if not result:
            return

        generate_chapters, chapters_per_part = result

        # 计算预计新增的部分数
        import math
        estimated_parts = math.ceil(generate_chapters / chapters_per_part)
        new_parts = estimated_parts - current_parts

        logger.info(
            f"继续生成部分大纲（SSE增量模式）: "
            f"当前{current_parts}部分(覆盖到第{current_covered_chapter}章), "
            f"目标覆盖到第{generate_chapters}章, 预计新增{new_parts}部分"
        )

        # 显示进度对话框
        message = f"从第{current_covered_chapter + 1}章开始继续生成...\n目标覆盖到第{generate_chapters}章"

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="继续生成部分大纲",
            message=message,
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_part_outline_sse_cancelled)
        self._progress_dialog.show()

        # 使用SSE增量生成端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/parts/continue-stream"
        payload = {
            "total_chapters": generate_chapters,
            "chapters_per_part": chapters_per_part
        }

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_part_outline_progress)
        self._sse_worker.complete.connect(self._on_part_outline_complete)
        self._sse_worker.error_data.connect(self._on_part_outline_error)
        self._sse_worker.start()

    def _on_generate_completed(self, result):
        """生成任务完成（旧版轮询模式，保留兼容）"""
        self._stop_progress_polling()
        total_parts = result.get('total_parts', 0)
        logger.info(f"部分大纲生成完成: {result}")
        MessageService.show_operation_success(self, f"部分大纲生成完成，共 {total_parts} 个部分")
        self.refreshRequested.emit()

    def _on_generate_started(self, result):
        """生成任务启动成功，开始轮询进度（已弃用，保留兼容）"""
        logger.info(f"部分大纲生成任务已启动: {result}")
        # 启动进度轮询
        self._start_progress_polling()

    def _on_generate_error(self, error_msg):
        """生成任务启动失败（旧版轮询模式，保留兼容）"""
        self._stop_progress_polling()
        MessageService.show_api_error(self, error_msg, "启动生成任务")

    def _start_progress_polling(self):
        """开始轮询进度"""
        if self._progress_timer:
            self._progress_timer.stop()

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._poll_progress)
        self._progress_timer.start(2000)  # 每2秒轮询一次

    def _stop_progress_polling(self):
        """停止进度轮询"""
        if self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _poll_progress(self):
        """轮询生成进度"""
        try:
            status_data = self.api_client.get_part_outline_generation_status(self.project_id)
            status = status_data.get('status', 'pending')
            completed_parts = status_data.get('completed_parts', 0)
            total_parts = status_data.get('total_parts', 0)
            parts = status_data.get('parts', [])

            logger.info(f"部分大纲生成进度: {completed_parts}/{total_parts}, 状态: {status}")

            # 更新进度显示
            if self._progress_dialog:
                progress_text = f"正在生成部分大纲...\n已完成: {completed_parts} / {total_parts}"

                # 查找正在生成的部分
                generating_part = None
                for part in parts:
                    if part.get('generation_status') == 'generating':
                        generating_part = part.get('part_number', 0)
                        break

                if generating_part:
                    progress_text += f"\n当前正在生成: 第 {generating_part} 部分"

                self._progress_dialog.setMessage(progress_text)

            # 检查是否完成
            if status == 'completed' or completed_parts >= total_parts:
                self._stop_progress_polling()
                MessageService.show_operation_success(self, f"部分大纲生成完成，共 {total_parts} 个部分")
                self.refreshRequested.emit()
            elif status == 'failed':
                self._stop_progress_polling()
                MessageService.show_error(self, "部分大纲生成失败，请重试", "生成失败")

        except Exception as e:
            logger.error(f"轮询进度失败: {e}")
            # 轮询失败不停止，继续尝试

    def _on_regenerate_latest_parts(self):
        """重新生成最新N个部分大纲"""
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            MessageService.show_warning(self, "没有部分大纲可以重新生成", "提示")
            return

        max_count = len(part_outlines)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="重新生成最新N个部分大纲",
            label=f"共有 {max_count} 个部分大纲\n请输入要重新生成的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        # 确认级联删除
        start_part = max_count - count + 1
        if not confirm(
            self,
            f"将重新生成最后 {count} 个部分大纲（第{start_part}-{max_count}部分）。\n\n"
            f"根据串行生成原则：\n"
            f"• 这些部分对应的所有章节大纲也会被删除\n\n"
            f"确定要继续吗？",
            "确认重新生成"
        ):
            return

        # 获取优化提示词
        prompt, ok = InputDialog.getTextStatic(
            parent=self,
            title="优化提示词（可选）",
            label="请输入优化提示词，用于引导AI生成更符合预期的部分大纲：",
            placeholder="留空则使用默认生成方式"
        )
        if not ok:
            return

        # 从第start_part部分开始重新生成（级联删除后续所有）
        self.async_helper.execute(
            self.api_client.regenerate_specific_part_outline,
            self.project_id,
            start_part,
            prompt=prompt if prompt else None,
            cascade_delete=True,
            loading_message=f"正在重新生成第{start_part}部分及之后的部分大纲...",
            success_message=f"部分大纲重新生成",
            error_context="重新生成部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_delete_latest_parts(self):
        """删除最新N个部分大纲"""
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            MessageService.show_warning(self, "没有部分大纲可以删除", "提示")
            return

        max_count = len(part_outlines)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="删除最新N个部分大纲",
            label=f"共有 {max_count} 个部分大纲\n请输入要删除的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        start_part = max_count - count + 1
        if not confirm(
            self,
            f"确定要删除最后 {count} 个部分大纲（第{start_part}-{max_count}部分）吗？\n\n"
            f"这些部分对应的章节大纲也会被一起删除。\n\n"
            f"此操作不可恢复！",
            "确认删除"
        ):
            return

        self.async_helper.execute(
            self.api_client.delete_part_outlines,
            self.project_id,
            count,
            loading_message=f"正在删除 {count} 个部分大纲...",
            success_message=f"删除 {count} 个部分大纲",
            error_context="删除部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    # ========== 章节大纲操作 ==========

    def _on_generate_chapter_outlines(self):
        """生成章节大纲"""
        self.async_helper.execute(
            self.api_client.generate_all_chapter_outlines_async,
            self.project_id,
            async_mode=False,
            loading_message="正在生成章节大纲...",
            success_message=None,
            error_context="生成章节大纲",
            on_success=self._on_chapter_outlines_generated
        )

    def _on_chapter_outlines_generated(self, result):
        """章节大纲生成完成"""
        total = result.get('total_chapters', 0)
        MessageService.show_operation_success(self, f"章节大纲生成完成，共{total}章")
        self.refreshRequested.emit()

    def _on_continue_generate_chapters(self):
        """继续生成N个章节大纲"""
        # 计算当前已生成的章节数
        current_count = len(self.outline)

        # 长篇模式下，检查部分大纲覆盖范围
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        if needs_part_outlines:
            # 计算部分大纲覆盖的最大章节数
            part_outlines = self.blueprint.get('part_outlines', [])
            max_covered_chapter = 0
            for part in part_outlines:
                end_chapter = part.get('end_chapter', 0)
                if end_chapter > max_covered_chapter:
                    max_covered_chapter = end_chapter

            # 检查是否还有可生成的空间
            remaining = max_covered_chapter - current_count
            if remaining <= 0:
                if max_covered_chapter < self.blueprint.get('total_chapters', 0):
                    MessageService.show_warning(
                        self,
                        f"当前部分大纲仅覆盖到第{max_covered_chapter}章，\n"
                        f"已生成{current_count}章，无法继续生成。\n\n"
                        f"请先生成更多部分大纲以覆盖后续章节。",
                        "提示"
                    )
                else:
                    MessageService.show_warning(self, "所有章节大纲已生成完成", "提示")
                return

            # 限制最大可生成数量为剩余覆盖范围
            max_generate = min(remaining, 100)
            label_text = (
                f"当前已生成 {current_count} 章，部分大纲覆盖到第 {max_covered_chapter} 章\n"
                f"还可生成 {remaining} 章\n\n"
                f"请输入要生成的章节数量："
            )
        else:
            # 短篇模式，使用总章节数
            total_chapters = self.blueprint.get('total_chapters', 0) or len(self.outline)
            remaining = total_chapters - current_count if total_chapters > 0 else 100
            max_generate = min(remaining, 100) if remaining > 0 else 100
            label_text = "请输入要生成的章节数量："

        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="继续生成章节大纲",
            label=label_text,
            value=min(5, max_generate),
            min_value=1,
            max_value=max_generate
        )
        if not ok:
            return

        logger.info(f"开始继续生成 {count} 个章节大纲（使用SSE流式进度）")

        # 显示进度对话框
        self._progress_dialog = LoadingDialog(
            parent=self,
            title="生成章节大纲",
            message=f"正在准备生成 {count} 个章节大纲...",
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_chapter_outline_sse_cancelled)
        self._progress_dialog.show()

        # 使用SSEWorker连接流式端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/chapter-outlines/generate-by-count"
        payload = {"count": count}

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_chapter_outline_progress)
        self._sse_worker.complete.connect(self._on_chapter_outline_complete)
        self._sse_worker.error_data.connect(self._on_chapter_outline_error)  # 使用error_data获取完整错误信息
        self._sse_worker.start()

    def _on_chapter_outline_progress(self, data: dict):
        """处理章节大纲生成进度更新"""
        if not self._progress_dialog:
            return

        status = data.get('status', '')
        current_batch = data.get('current_batch', 0)
        total_batches = data.get('total_batches', 0)
        generated_count = data.get('generated_count', 0)
        total_count = data.get('total_count', 0)
        current_range = data.get('current_range', '')

        if status == 'starting':
            message = f"正在准备生成...\n{current_range}"
        elif status == 'generating':
            message = f"批次进度: {current_batch}/{total_batches}\n{current_range}\n已完成: {generated_count}/{total_count} 章"
        elif status == 'batch_done':
            message = f"批次进度: {current_batch}/{total_batches}\n{current_range}\n已完成: {generated_count}/{total_count} 章"
        else:
            message = current_range

        self._progress_dialog.setMessage(message)

    def _on_chapter_outline_complete(self, data: dict):
        """章节大纲生成完成"""
        self._cleanup_chapter_outline_sse()

        message = data.get('message', '生成完成')
        generated_chapters = data.get('generated_chapters', [])
        total_chapters = data.get('total_chapters', 0)

        logger.info(f"章节大纲生成完成: {message}, 共{len(generated_chapters)}章")
        MessageService.show_operation_success(self, message)
        self.refreshRequested.emit()

    def _on_chapter_outline_error(self, error_data: dict):
        """章节大纲生成错误"""
        self._cleanup_chapter_outline_sse()

        # 解析错误数据
        error_msg = error_data.get('message', '未知错误')
        saved_count = error_data.get('saved_count', 0)
        saved_chapters = error_data.get('saved_chapters', [])

        logger.error(f"章节大纲生成失败: {error_msg}, 已保存 {saved_count} 章")

        # 构建用户友好的错误信息
        if saved_count > 0:
            # 有部分章节已保存
            saved_info = f"\n\n已成功保存 {saved_count} 章大纲（第{min(saved_chapters)}-{max(saved_chapters)}章）。\n刷新页面可查看已保存的内容。"
            MessageService.show_api_error(self, f"{error_msg}{saved_info}", "生成章节大纲")
            # 刷新页面以显示已保存的内容
            self.refreshRequested.emit()
        else:
            MessageService.show_api_error(self, error_msg, "生成章节大纲")

    def _on_chapter_outline_sse_cancelled(self):
        """用户取消章节大纲生成"""
        logger.info("用户取消章节大纲生成")
        self._cleanup_chapter_outline_sse()

    def _cleanup_chapter_outline_sse(self):
        """清理章节大纲SSE相关资源"""
        if self._sse_worker:
            # SSEWorker.stop() 已经断开信号并关闭连接，无需 blockSignals
            self._sse_worker.stop()
            if self._sse_worker.isRunning():
                self._sse_worker.quit()
                self._sse_worker.wait(WorkerTimeouts.DEFAULT_MS)
            self._sse_worker = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _on_regenerate_latest_chapters(self):
        """重新生成最新N个章节大纲"""
        if not self.outline:
            MessageService.show_warning(self, "没有章节大纲可以重新生成", "提示")
            return

        max_count = len(self.outline)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="重新生成最新N个章节大纲",
            label=f"共有 {max_count} 个章节大纲\n请输入要重新生成的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        # 计算起始章节
        start_chapter = max_count - count + 1

        if not confirm(
            self,
            f"将重新生成最后 {count} 个章节大纲（第{start_chapter}-{max_count}章）。\n\n"
            f"确定要继续吗？",
            "确认重新生成"
        ):
            return

        # 获取优化提示词
        prompt, ok = InputDialog.getTextStatic(
            parent=self,
            title="优化提示词（可选）",
            label=f"请输入优化提示词，用于引导AI重新生成章节大纲：",
            placeholder="留空则使用默认生成方式"
        )
        if not ok:
            return

        # 从start_chapter开始重新生成（级联删除后续所有）
        self.async_helper.execute(
            self.api_client.regenerate_chapter_outline,
            self.project_id, start_chapter,
            prompt=prompt if prompt else None,
            cascade_delete=True,
            loading_message=f"正在重新生成第{start_chapter}章及之后的章节大纲...",
            success_message=f"章节大纲重新生成",
            error_context="重新生成章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_delete_latest_chapters(self):
        """删除最新N个章节大纲"""
        if not self.outline:
            MessageService.show_warning(self, "没有章节大纲可以删除", "提示")
            return

        max_count = len(self.outline)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="删除最新N个章节大纲",
            label=f"共有 {max_count} 个章节大纲\n请输入要删除的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        if not confirm(
            self,
            f"确定要删除最后 {count} 个章节大纲吗？\n\n此操作不可恢复！",
            "确认删除"
        ):
            return

        self.async_helper.execute(
            self.api_client.delete_chapter_outlines,
            self.project_id, count,
            loading_message=f"正在删除 {count} 个章节大纲...",
            success_message=f"删除 {count} 个章节大纲",
            error_context="删除章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def cleanup(self):
        """清理所有资源（供父组件在页面隐藏时调用）"""
        self._cleanup_part_outline_sse()
        self._cleanup_chapter_outline_sse()
        if self.async_helper:
            self.async_helper.cleanup()
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
        self.async_helper.stop_all()

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
