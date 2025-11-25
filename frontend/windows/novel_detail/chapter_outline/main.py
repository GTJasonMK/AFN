"""
章节大纲 Section - 现代化设计（重构版）

管理章节大纲的生成、展示和编辑，支持长篇和短篇流程
采用模块化设计，将UI组件和业务逻辑分离
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QInputDialog,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from api.client import ArborisAPIClient
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp, sp

from .async_helper import AsyncOperationHelper
from .empty_states import LongNovelEmptyState, ShortNovelEmptyState
from .part_outline_card import PartOutlineCard
from .chapter_list import ChapterOutlineList

import logging

logger = logging.getLogger(__name__)


class ChapterOutlineSection(ThemeAwareWidget):
    """章节大纲组件 - 现代化卡片设计（重构版）"""

    editRequested = pyqtSignal(str, str, object)
    refreshRequested = pyqtSignal()
    addRequested = pyqtSignal()

    def __init__(self, outline=None, blueprint=None, project_id='', editable=True, parent=None):
        self.outline = outline or []
        self.blueprint = blueprint or {}
        self.project_id = project_id
        self.editable = editable

        # 记录初始数据（调试用）
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
        self._part_outline_card = None
        self._chapter_list = None
        self._short_header = None

        # 先调用父类初始化
        super().__init__(parent)

        # 初始化服务
        self.api_client = ArborisAPIClient()
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
        self._main_layout.setSpacing(dp(24))

        # 判断模式并创建对应UI
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        self.current_mode = 'long' if needs_part_outlines else 'short'

        if self.current_mode == 'long':
            self._create_long_novel_ui()
        else:
            self._create_short_novel_ui()

    def _create_long_novel_ui(self):
        """创建长篇小说UI"""
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
            # 显示部分大纲卡片
            logger.info(f"创建部分大纲卡片，共 {len(part_outlines)} 个部分")
            self._part_outline_card = PartOutlineCard(
                part_outlines, editable=self.editable
            )
            self._part_outline_card.regenerateClicked.connect(self._on_regenerate_part_outlines)
            self._part_outline_card.regeneratePartClicked.connect(self._on_regenerate_specific_part)
            self._main_layout.addWidget(self._part_outline_card)

            # 显示章节大纲列表
            logger.info(
                f"创建章节大纲列表: "
                f"outlines={len(self.outline)}, "
                f"total_chapters={self.blueprint.get('total_chapters', 0)}"
            )
            self._chapter_list = ChapterOutlineList(
                outlines=self.outline,
                total_chapters=self.blueprint.get('total_chapters', 0),
                editable=self.editable,
                show_header=True
            )
            self._connect_chapter_list_signals()
            self._main_layout.addWidget(self._chapter_list)
            logger.info("长篇小说UI创建完成")

    def _create_short_novel_ui(self):
        """创建短篇小说UI"""
        if not self.outline:
            # 显示空状态
            self._empty_state = ShortNovelEmptyState()
            self._empty_state.actionClicked.connect(self._on_generate_chapter_outlines)
            self._main_layout.addWidget(self._empty_state)
        else:
            # 创建头部
            self._create_short_novel_header()

            # 显示章节大纲列表
            self._chapter_list = ChapterOutlineList(
                outlines=self.outline,
                total_chapters=len(self.outline),
                editable=self.editable,
                show_header=False  # 短篇模式下头部在外面
            )
            self._connect_chapter_list_signals()
            self._main_layout.addWidget(self._chapter_list)

    def _create_short_novel_header(self):
        """创建短篇小说头部"""
        header_layout = QHBoxLayout()

        title = QLabel("章节大纲")
        title.setStyleSheet(
            f"font-size: {sp(20)}px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};"
        )
        header_layout.addWidget(title, stretch=1)

        subtitle = QLabel(f"短篇小说 - 共 {len(self.outline)} 章")
        subtitle.setStyleSheet(
            f"font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY};"
        )
        header_layout.addWidget(subtitle)

        if self.editable:
            add_btn = QPushButton("新增章节")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.ACCENT_PALE};
                    color: {theme_manager.TEXT_PRIMARY};
                    border: 1px solid {theme_manager.ACCENT};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.ACCENT};
                    color: {theme_manager.BUTTON_TEXT};
                }}
            """)
            add_btn.clicked.connect(self.addRequested.emit)
            header_layout.addWidget(add_btn)

            edit_btn = QPushButton("编辑大纲")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(theme_manager.button_secondary())
            edit_btn.clicked.connect(
                lambda: self.editRequested.emit('chapter_outline', '章节大纲', self.outline)
            )
            header_layout.addWidget(edit_btn)

        self._main_layout.addLayout(header_layout)
        self._short_header = header_layout

    def _connect_chapter_list_signals(self):
        """连接章节列表信号"""
        if self._chapter_list:
            self._chapter_list.editAllClicked.connect(
                lambda: self.editRequested.emit('chapter_outline', '章节大纲', self.outline)
            )
            self._chapter_list.flexibleGenerateClicked.connect(self._on_flexible_generate)
            self._chapter_list.deleteLastClicked.connect(self._on_delete_last_chapters)
            self._chapter_list.regenerateChapterClicked.connect(self._on_regenerate_chapter)

    def _apply_theme(self):
        """应用主题"""
        self._rebuild_ui()

    def _rebuild_ui(self):
        """重建UI"""
        # 清空现有UI
        self._clear_ui()

        # 重新创建
        if self.current_mode == 'long':
            self._create_long_novel_ui()
        else:
            self._create_short_novel_ui()

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
        self._part_outline_card = None
        self._chapter_list = None
        self._short_header = None

    def _clear_layout(self, layout):
        """递归清空布局"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # ========== 事件处理 ==========

    def _on_generate_part_outlines(self):
        """生成部分大纲"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        if total_chapters == 0:
            MessageService.show_warning(self, "无法获取总章节数，请先生成蓝图", "提示")
            return

        chapters_per_part, ok = QInputDialog.getInt(
            self, "生成部分大纲",
            f"小说共 {total_chapters} 章\n请输入每个部分包含的章节数：",
            25, 10, 100
        )
        if not ok:
            return

        self.async_helper.execute(
            self.api_client.generate_part_outlines,
            self.project_id,
            total_chapters=total_chapters,
            chapters_per_part=chapters_per_part,
            loading_message="正在启动部分大纲生成任务...",
            success_message="部分大纲生成",
            error_context="启动生成任务",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_regenerate_part_outlines(self):
        """重新生成所有部分大纲"""
        if not confirm(
            self,
            "重新生成所有部分大纲将会覆盖现有的部分大纲结构。\n\n"
            "根据串行生成原则，所有已生成的章节大纲也会被删除。\n\n"
            "确定要继续吗？",
            "确认重新生成"
        ):
            return

        prompt, ok = QInputDialog.getText(
            self, "优化提示词（可选）",
            "请输入优化提示词，用于引导AI生成更符合预期的部分大纲：\n（留空则使用默认生成方式）"
        )
        if not ok:
            return

        self.async_helper.execute(
            self.api_client.regenerate_part_outlines,
            self.project_id,
            prompt=prompt if prompt else None,
            loading_message="正在重新生成所有部分大纲...",
            success_message="所有部分大纲重新生成",
            error_context="重新生成所有部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_regenerate_specific_part(self, part_number: int):
        """重新生成指定部分大纲"""
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            MessageService.show_warning(self, "未找到部分大纲数据", "提示")
            return

        # 找到最大部分号
        max_part_number = max(p.get('part_number', 0) for p in part_outlines)
        is_last_part = (part_number == max_part_number)

        # 如果不是最后一个部分，询问用户是否要级联删除
        cascade_delete = False
        if not is_last_part:
            # 提示用户级联删除的影响
            if not confirm(
                self,
                f"重新生成第{part_number}部分会影响后续所有部分（当前最后一个部分为第{max_part_number}部分）。\n\n"
                f"根据串行生成原则：\n"
                f"• 第{part_number}部分及之后的所有部分大纲会被删除\n"
                f"• 第{part_number}部分及之后的所有章节大纲会被删除\n\n"
                f"如果只想重新生成最后一个部分，请点击第{max_part_number}部分的重新生成按钮。\n\n"
                f"确定要继续吗？",
                "确认级联删除"
            ):
                return
            cascade_delete = True
        else:
            # 是最后一个部分，确认是否继续
            if not confirm(
                self,
                f"重新生成第{part_number}部分将会覆盖当前内容。\n\n"
                f"该部分对应的章节大纲也会被删除。\n\n"
                f"确定要继续吗？",
                "确认重新生成"
            ):
                return

        # 获取优化提示词
        prompt, ok = QInputDialog.getText(
            self, "优化提示词（可选）",
            f"请输入优化提示词，用于引导AI生成第{part_number}部分大纲：\n（留空则使用默认生成方式）"
        )
        if not ok:
            return

        self.async_helper.execute(
            self.api_client.regenerate_specific_part_outline,
            self.project_id,
            part_number,
            prompt=prompt if prompt else None,
            cascade_delete=cascade_delete,
            loading_message=f"正在重新生成第{part_number}部分大纲...",
            success_message=f"第{part_number}部分大纲重新生成",
            error_context="重新生成部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_generate_chapter_outlines(self):
        """生成章节大纲"""
        self.async_helper.execute(
            self.api_client.generate_all_chapter_outlines_async,
            self.project_id,
            async_mode=False,
            loading_message="正在生成章节大纲...",
            success_message=None,  # 自定义成功消息
            error_context="生成章节大纲",
            on_success=self._on_chapter_outlines_generated
        )

    def _on_chapter_outlines_generated(self, result):
        """章节大纲生成完成"""
        total = result.get('total_chapters', 0)
        MessageService.show_operation_success(self, f"章节大纲生成完成，共{total}章")
        self.refreshRequested.emit()

    def _on_flexible_generate(self):
        """灵活生成N个章节大纲"""
        count, ok = QInputDialog.getInt(
            self, "灵活生成章节大纲", "请输入要生成的章节数量：",
            1, 1, 100
        )
        if not ok:
            return

        logger.info(f"开始灵活生成 {count} 个章节大纲")

        self.async_helper.execute(
            self.api_client.generate_chapter_outlines_by_count,
            self.project_id, count,
            loading_message=f"正在生成 {count} 个章节大纲...",
            success_message=f"生成 {count} 个章节大纲",
            error_context="生成章节大纲",
            on_success=self._on_flexible_generate_success
        )

    def _on_flexible_generate_success(self, result):
        """灵活生成成功回调"""
        logger.info(f"灵活生成成功，结果: {result}")
        logger.info("发送refreshRequested信号")
        self.refreshRequested.emit()
        logger.info("refreshRequested信号已发送")

    def _on_delete_last_chapters(self):
        """删除最后N个章节"""
        max_count = len(self.outline)
        if max_count == 0:
            return

        count, ok = QInputDialog.getInt(
            self, "删除章节大纲", "请输入要删除的章节数量（从最后开始）：",
            1, 1, max_count
        )
        if not ok:
            return

        if not confirm(self, f"确定要删除最后 {count} 个章节大纲吗？此操作不可恢复！", "确认删除"):
            return

        self.async_helper.execute(
            self.api_client.delete_chapter_outlines,
            self.project_id, count,
            loading_message=f"正在删除 {count} 个章节大纲...",
            success_message=f"删除 {count} 个章节大纲",
            error_context="删除章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_regenerate_chapter(self, chapter_number: int):
        """重新生成单个章节大纲（串行生成原则）"""
        if not self.outline:
            MessageService.show_warning(self, "未找到章节大纲数据", "提示")
            return

        # 找到最大章节号
        max_chapter_number = max(ch.get('chapter_number', 0) for ch in self.outline)
        is_last_chapter = (chapter_number == max_chapter_number)

        # 如果不是最后一章，询问用户是否要级联删除
        cascade_delete = False
        if not is_last_chapter:
            # 提示用户级联删除的影响
            if not confirm(
                self,
                f"重新生成第{chapter_number}章会影响后续所有章节（当前最后一章为第{max_chapter_number}章）。\n\n"
                f"根据串行生成原则：\n"
                f"• 第{chapter_number}章及之后的所有章节大纲会被删除（共{max_chapter_number - chapter_number + 1}章）\n\n"
                f"如果只想重新生成最后一章，请点击第{max_chapter_number}章的重新生成按钮。\n\n"
                f"确定要继续吗？",
                "确认级联删除"
            ):
                return
            cascade_delete = True
        else:
            # 是最后一章，确认是否继续
            if not confirm(
                self,
                f"重新生成第{chapter_number}章将会覆盖当前内容。\n\n"
                f"确定要继续吗？",
                "确认重新生成"
            ):
                return

        # 获取优化提示词
        prompt, ok = QInputDialog.getText(
            self, "优化提示词（可选）",
            f"请输入优化提示词，用于引导AI重新生成第{chapter_number}章大纲：\n（留空则使用默认生成方式）"
        )
        if not ok:
            return

        self.async_helper.execute(
            self.api_client.regenerate_chapter_outline,
            self.project_id, chapter_number,
            prompt=prompt if prompt else None,
            cascade_delete=cascade_delete,
            loading_message=f"正在重新生成第{chapter_number}章大纲...",
            success_message=f"第{chapter_number}章大纲重新生成",
            error_context="重新生成章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _check_generation_status(self):
        """检查部分大纲生成状态"""
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
                    self._start_progress_polling()
        except Exception as e:
            logger.debug(f"检查部分大纲生成状态失败（正常情况，可忽略）: {e}")

    def _start_progress_polling(self):
        """开始轮询进度（保留用于特殊情况）"""
        # 注意：当前generate_part_outlines是同步操作，通常不需要轮询
        # 此方法保留用于处理页面刷新时发现有正在进行的任务
        pass

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
        self.async_helper.stop_all()

    def closeEvent(self, event):
        """组件关闭时清理资源"""
        logger.info("ChapterOutlineSection关闭，清理异步任务")
        self.stopAllTasks()
        super().closeEvent(event)
