"""
写作台左侧章节列表

功能：蓝图预览、章节大纲列表、章节选择
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QFrame, QWidget, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from components.base import ThemeAwareFrame
from components.empty_state import EmptyState
from components.loading_spinner import ListLoadingState
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens
from utils.dpi_utils import dp
from utils.message_service import MessageService, confirm
from utils.async_worker import AsyncWorker
from utils.component_pool import ComponentPool, reset_chapter_card
from api.manager import APIClientManager
from windows.novel_detail.chapter_outline.components import OutlineActionBar
from .components import ChapterCard, FlippableBlueprintCard
from .dialogs import OutlineEditDialog
from .utils import extract_protagonist_name

logger = logging.getLogger(__name__)


class WDSidebar(TransparencyAwareMixin, ThemeAwareFrame):
    """左侧章节列表 - 禅意风格

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符
    _transparency_component_id = "sidebar"

    chapterSelected = pyqtSignal(int)  # chapter_number
    generateChapter = pyqtSignal(int)
    generateOutline = pyqtSignal()
    createChapter = pyqtSignal()  # 手动新增章节（用于空白项目）
    viewProtagonistProfile = pyqtSignal()  # 查看主角档案

    def __init__(self, project=None, parent=None):
        self.project = project or {}
        self.selected_chapter = None
        self.generating_chapter = None
        self.chapter_cards = []  # 存储所有章节卡片
        self.api_client = APIClientManager.get_client()  # 使用单例客户端
        self._portrait_worker = None  # 异步加载立绘的worker

        # 组件池：复用章节卡片，避免重复创建开销
        self._chapter_card_pool = ComponentPool(
            ChapterCard,
            max_size=100,  # 最多缓存100个卡片
            factory_kwargs={'chapter_data': {}, 'is_selected': False},
            reset_callback=reset_chapter_card
        )

        # 保存组件引用
        self.blueprint_card = None  # 可翻转的蓝图卡片
        self.chapters_container = None  # 章节卡片容器
        self.empty_state = None
        self.outline_action_bar = None

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
        self.setupUI()

    def _get_blueprint(self, project=None):
        """获取蓝图数据（小说项目专用）

        Args:
            project: 项目数据，如果为None则使用self.project

        Returns:
            dict: 蓝图数据
        """
        proj = project or self.project
        if not proj:
            return {}
        return proj.get('blueprint') or {}

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        logger.info("WDSidebar._create_ui_structure 开始执行")
        self.setFixedWidth(dp(280))  # 从340减少到280，节省60px横向空间

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 从16减少到12
        layout.setSpacing(dp(12))  # 从16减少到12

        # 可翻转的蓝图卡片（正面：蓝图信息，背面：主角立绘）
        self.blueprint_card = FlippableBlueprintCard()
        self.blueprint_card.viewProfileRequested.connect(self._on_view_profile_requested)
        layout.addWidget(self.blueprint_card)

        # 章节列表操作栏
        self.outline_action_bar = OutlineActionBar(
            title="章节列表",
            current_count=0,
            total_count=0,
            outline_type="chapter",
            editable=True,
            show_continue_button=True,
            show_add_button=True,
            show_regenerate_button=False,
            show_delete_button=False,
            show_progress=False,
            add_label="+",
            continue_label="生成大纲",
            add_tooltip="新增章节",
            continue_tooltip="生成章节大纲",
        )
        self.outline_action_bar.addOutlineClicked.connect(self.createChapter.emit)
        self.outline_action_bar.continueGenerateClicked.connect(self.generateOutline.emit)
        layout.addWidget(self.outline_action_bar)

        # 章节列表容器（使用滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(theme_manager.scrollbar())
        # 设置viewport透明背景
        if scroll_area.viewport():
            scroll_area.viewport().setStyleSheet("background-color: transparent;")

        # 章节容器widget
        self.chapters_container = QWidget()
        self.chapters_layout = QVBoxLayout(self.chapters_container)
        self.chapters_layout.setContentsMargins(0, 0, 0, 0)
        self.chapters_layout.setSpacing(dp(8))  # 修正：6不符合8pt网格

        # 章节列表加载骨架屏
        self.chapters_loading = ListLoadingState(
            row_count=6,
            row_height=dp(48),
            spacing=dp(8),
            parent=self.chapters_container
        )
        self.chapters_loading.hide()  # 初始隐藏
        self.chapters_layout.addWidget(self.chapters_loading)

        self.chapters_layout.addStretch()

        scroll_area.setWidget(self.chapters_container)
        layout.addWidget(scroll_area, stretch=1)

        logger.info("WDSidebar._create_ui_structure 完成")

        # 如果之前调用setProject时UI还未初始化，现在加载待处理的数据
        if hasattr(self, '_pending_chapter_outlines') and self._pending_chapter_outlines:
            logger.info(f"检测到待处理的章节大纲数据({len(self._pending_chapter_outlines)}章)，现在填充")
            self._populate_chapters(self._pending_chapter_outlines)
            del self._pending_chapter_outlines

        # 如果已有项目数据，加载
        if self.project:
            logger.info(f"在_create_ui_structure中检测到project数据，调用setProject")
            self.setProject(self.project)

    def _apply_theme(self):
        """应用主题样式（可多次调用）- 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        # 调试日志
        logger.info(f"=== WDSidebar._apply_theme() ===")
        logger.info(f"transparency_enabled: {self._transparency_enabled}, opacity: {self._current_opacity}")

        # Sidebar背景 - 支持透明效果
        if self._transparency_enabled:
            # 使用Mixin提供的透明背景样式
            bg_style = self._get_transparent_bg(
                theme_manager.BG_SECONDARY,
                border_color=theme_manager.BORDER_LIGHT
            )

            # 直接设置样式，不使用Python类名选择器
            self.setStyleSheet(f"""
                {bg_style}
                border-right: 1px solid {self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_DEFAULT)};
            """)

            # 使用Mixin方法使子组件透明
            self._make_children_transparent()

            # 额外处理特定子组件
            if hasattr(self, 'chapters_container') and self.chapters_container:
                self._make_widget_transparent(self.chapters_container)

        else:
            # 非透明模式 - 使用正常背景色
            # 直接设置样式，不使用Python类名选择器
            self.setStyleSheet(f"""
                background-color: {theme_manager.BG_SECONDARY};
                border-right: 1px solid {theme_manager.BORDER_LIGHT};
            """)

        # 蓝图卡片主题由FlippableBlueprintCard自行管理

        # OutlineActionBar 自带样式，侧边栏仅需保持透明背景处理

    def setProject(self, project):
        """设置项目数据"""
        self.project = project

        logger.info(f"WDSidebar.setProject被调用")
        logger.info(f"项目数据键: {list(project.keys()) if isinstance(project, dict) else 'NOT A DICT'}")

        # 更新蓝图预览 - 使用辅助方法获取蓝图
        blueprint = self._get_blueprint(project)
        logger.info(f"blueprint存在: {bool(blueprint)}")

        # 判断是否为空白项目
        is_empty_project = not blueprint or not blueprint.get('one_sentence_summary')

        if self.blueprint_card:
            if blueprint:
                logger.info(f"blueprint键: {list(blueprint.keys()) if isinstance(blueprint, dict) else 'NOT A DICT'}")
                style = blueprint.get('style', '未设定风格')
                summary = blueprint.get('one_sentence_summary', '暂无概要')
                self.blueprint_card.setStyle(style)
                self.blueprint_card.setSummary(summary)
            else:
                # 空白项目：显示提示信息
                self.blueprint_card.setStyle("自由创作模式")
                self.blueprint_card.setSummary("可直接创建章节开始写作，无需生成蓝图和大纲")

            # 设置章节进度
            self._update_chapter_progress()

            # 加载主角立绘和信息
            self._load_protagonist_portrait()

        # 根据项目类型调整按钮显示
        if self.outline_action_bar:
            # 空白项目隐藏生成大纲按钮
            self.outline_action_bar.set_continue_visible(not is_empty_project)
            # 新增章节按钮始终显示（空白项目更需要）
            self.outline_action_bar.set_add_visible(True)

        # 更新章节列表
        chapter_outlines = blueprint.get('chapter_outline', [])
        logger.info(f"chapter_outline数量: {len(chapter_outlines)}")

        if not hasattr(self, 'chapters_container') or self.chapters_container is None:
            logger.error("chapters_container组件不存在！可能UI还未完全初始化，稍后会自动加载")
            # 保存数据，等UI初始化完成后再填充
            self._pending_chapter_outlines = chapter_outlines
            return

        # 填充章节列表
        self._populate_chapters(chapter_outlines)

    def _update_chapter_progress(self):
        """更新章节进度显示"""
        if not self.project or not self.blueprint_card:
            return

        # 获取总章节数（从大纲或实际章节中取最大值）
        blueprint = self._get_blueprint()
        chapter_outlines = blueprint.get('chapter_outline', []) if blueprint else []
        project_chapters = self.project.get('chapters', [])

        total_chapters = max(len(chapter_outlines), len(project_chapters))

        # 计算已完成章节数（有选中版本或状态为successful的章节）
        completed = 0
        for ch in project_chapters:
            # 后端状态是 'successful' 而不是 'completed'
            if ch.get('selected_version_id') or ch.get('generation_status') == 'successful':
                completed += 1

        self.blueprint_card.setProgress(completed, total_chapters)

    def _populate_chapters(self, chapter_outlines):
        """填充章节列表（分批加载，避免UI卡顿）

        合并章节大纲和实际章节数据：
        - 优先使用章节大纲信息（标题、摘要）
        - 补充实际章节的状态和字数
        - 对于没有大纲的手动创建章节，也会显示

        Args:
            chapter_outlines: 章节大纲列表
        """
        # 显示加载骨架屏
        if hasattr(self, 'chapters_loading') and self.chapters_loading:
            self.chapters_loading.show()
            self.chapters_loading.start()

        # 清除旧的卡片
        self._clear_chapters()

        # 检查chapters_layout是否存在（使用 is None 而非 not，因为空布局 bool() 返回 False）
        if self.chapters_layout is None:
            logger.error("chapters_layout为None，无法填充章节列表")
            return

        # 获取已有的章节数据
        project_chapters = self.project.get('chapters', [])
        chapters_map = {ch.get('chapter_number'): ch for ch in project_chapters}

        # 构建章节大纲映射
        outlines_map = {o.get('chapter_number'): o for o in chapter_outlines}

        # 判断是否为空白项目 - 使用辅助方法
        blueprint = self._get_blueprint()
        is_empty_project = not blueprint or not blueprint.get('one_sentence_summary')

        # 合并章节列表：大纲 + 实际章节（去重）
        all_chapter_numbers = set()
        all_chapter_numbers.update(outlines_map.keys())
        all_chapter_numbers.update(chapters_map.keys())

        # 如果既没有大纲也没有章节，显示空状态
        if not all_chapter_numbers:
            logger.warning("章节列表为空，显示空状态")
            self._show_empty_state()
            return

        logger.info(f"开始填充章节列表，共 {len(all_chapter_numbers)} 章（大纲{len(outlines_map)}，实际章节{len(chapters_map)}）")

        # 后端 generation_status 到前端 status 的映射
        status_mapping = {
            'not_generated': 'not_generated',
            'generating': 'generating',
            'evaluating': 'generating',  # 评审中也显示为生成中
            'selecting': 'generating',   # 选择中也显示为生成中
            'failed': 'failed',
            'evaluation_failed': 'failed',
            'waiting_for_confirm': 'pending',  # 等待确认：有版本但用户尚未选择
            'successful': 'completed',         # 成功：用户已确认选择版本
        }

        # 准备章节数据列表
        chapter_data_list = []
        for chapter_num in sorted(all_chapter_numbers):
            outline = outlines_map.get(chapter_num, {})
            chapter_info = chapters_map.get(chapter_num, {})

            # 标题：优先使用大纲标题，其次使用章节标题，最后使用默认标题
            title = outline.get('title') or chapter_info.get('title') or f'第{chapter_num}章'

            # 获取章节状态和字数
            word_count = chapter_info.get('word_count', 0)
            backend_status = chapter_info.get('generation_status', 'not_generated')
            status = status_mapping.get(backend_status, 'not_generated')

            # 对于空白项目中的已创建章节，如果有内容则标记为已完成
            if is_empty_project and chapter_info.get('content'):
                status = 'completed'

            chapter_data_list.append({
                'chapter_number': chapter_num,
                'title': title,
                'status': status,
                'word_count': word_count,
                'is_manual': not outline  # 标记是否为手动创建（无大纲）
            })

        # 找到最新的已创作章节（非 not_generated 状态的最大章节号）
        # 只有这个章节才能清空数据，保证小说创作的连贯性
        latest_created_chapter = None
        for chapter_data in reversed(chapter_data_list):
            if chapter_data['status'] != 'not_generated':
                latest_created_chapter = chapter_data['chapter_number']
                break

        # 为每个章节添加 can_clear_data 标志
        for chapter_data in chapter_data_list:
            chapter_data['can_clear_data'] = (
                chapter_data['chapter_number'] == latest_created_chapter
            )

        # 分批创建章节卡片（优化：增大批次大小，减少定时器调用）
        self._pending_chapter_data = chapter_data_list
        self._batch_index = 0
        self._batch_size = 10  # 每批创建10个卡片（优化：从3增加到10）
        self._create_next_batch()

    def _create_next_batch(self):
        """创建下一批章节卡片

        性能优化：
        - 使用组件池复用卡片，避免重复创建
        - 移除 processEvents() 调用，避免阻塞
        - 增加批次大小到10，减少定时器调用次数
        - 缩短批次间隔到5ms
        """
        from PyQt6.QtCore import QTimer

        if not hasattr(self, '_pending_chapter_data') or not self._pending_chapter_data:
            return

        start_idx = self._batch_index * self._batch_size
        end_idx = min(start_idx + self._batch_size, len(self._pending_chapter_data))

        if start_idx >= len(self._pending_chapter_data):
            # 所有卡片创建完成
            logger.info(f"章节列表填充完成，共 {len(self.chapter_cards)} 个卡片")
            self._pending_chapter_data = None
            return

        # 创建这一批卡片（使用组件池复用）
        for i in range(start_idx, end_idx):
            chapter_data = self._pending_chapter_data[i]

            # 从组件池获取卡片
            card = self._chapter_card_pool.acquire()
            card.update_data(chapter_data, is_selected=False)
            card.clicked.connect(self._on_chapter_card_clicked)
            card.editOutlineRequested.connect(self._on_edit_outline)
            card.regenerateOutlineRequested.connect(self._on_regenerate_outline)
            card.clearChapterDataRequested.connect(self._on_clear_chapter_data)
            card.hoverPrefetchRequested.connect(self._on_hover_prefetch)

            # 添加到布局（插入到stretch之前）
            self.chapters_layout.insertWidget(self.chapters_layout.count() - 1, card)
            card.show()  # 池中的组件被hide了，需要显示
            self.chapter_cards.append(card)

        # 继续创建下一批
        self._batch_index += 1
        if self._batch_index * self._batch_size < len(self._pending_chapter_data):
            # 使用 QTimer 延迟执行下一批，给UI线程喘息的机会
            QTimer.singleShot(5, self._create_next_batch)
        else:
            logger.info(f"章节列表填充完成，共 {len(self.chapter_cards)} 个卡片")
            self._pending_chapter_data = None
            # 隐藏加载骨架屏
            self._hide_chapters_loading()

    def _clear_chapters(self):
        """清除所有章节卡片（释放回组件池）"""
        # 检查chapters_layout是否存在（使用 is None 而非 not，因为空布局 bool() 返回 False）
        if self.chapters_layout is None:
            logger.warning("chapters_layout为None，无法清除章节卡片")
            self.chapter_cards.clear()
            return

        for card in self.chapter_cards:
            # 断开信号连接，避免复用时重复连接
            try:
                card.clicked.disconnect(self._on_chapter_card_clicked)
                card.editOutlineRequested.disconnect(self._on_edit_outline)
                card.regenerateOutlineRequested.disconnect(self._on_regenerate_outline)
                card.clearChapterDataRequested.disconnect(self._on_clear_chapter_data)
                card.hoverPrefetchRequested.disconnect(self._on_hover_prefetch)
            except (TypeError, RuntimeError):
                pass

            self.chapters_layout.removeWidget(card)
            # 释放回组件池而不是销毁
            self._chapter_card_pool.release(card)

        self.chapter_cards.clear()

        # 移除空状态（如果存在）
        if self.empty_state:
            self.chapters_layout.removeWidget(self.empty_state)
            self.empty_state.deleteLater()
            self.empty_state = None

    def _hide_chapters_loading(self):
        """隐藏章节列表加载骨架屏"""
        if hasattr(self, 'chapters_loading') and self.chapters_loading:
            self.chapters_loading.stop()
            self.chapters_loading.hide()

    def _show_empty_state(self):
        """显示空状态

        根据项目类型显示不同的空状态：
        - 空白项目（无蓝图）：显示"新增章节"按钮
        - 普通项目（有蓝图但无大纲）：显示"生成大纲"提示
        """
        # 隐藏加载骨架屏
        self._hide_chapters_loading()

        # 检查chapters_layout是否存在
        if self.chapters_layout is None:
            logger.warning("chapters_layout为None，无法显示空状态")
            return

        # 判断是否为空白项目（无蓝图或蓝图为空）- 使用辅助方法
        blueprint = self._get_blueprint()
        is_empty_project = not blueprint or not blueprint.get('one_sentence_summary')

        if is_empty_project:
            # 空白项目：允许直接创建章节
            self.empty_state = EmptyState(
                icon='✎',
                title='开始创作',
                description='点击下方按钮新增章节开始写作',
                action_text='新增章节',
                parent=self
            )
            self.empty_state.actionClicked.connect(self.createChapter.emit)
        else:
            # 普通项目：提示生成大纲
            self.empty_state = EmptyState(
                icon='*',
                title='还未生成章节大纲',
                description='点击"生成大纲"按钮开始创作',
                action_text='',
                parent=self
            )
            self.empty_state.actionClicked.connect(self.generateOutline.emit)

        self.chapters_layout.insertWidget(0, self.empty_state)

    def _on_chapter_card_clicked(self, chapter_number):
        """章节卡片被点击

        Args:
            chapter_number: 章节编号
        """
        from PyQt6.QtCore import QTimer

        # 如果点击的是当前已选中的章节，不需要任何操作
        if self.selected_chapter == chapter_number:
            return

        # 防抖：如果正在处理上一次点击，忽略这次
        if hasattr(self, '_click_processing') and self._click_processing:
            # 记录最新的点击，稍后处理
            self._pending_click_chapter = chapter_number
            return

        self._click_processing = True
        self._pending_click_chapter = None

        try:
            # 立即更新视觉状态（给用户即时反馈）
            self._update_selection_visual(chapter_number)

            # 发射信号（会触发章节加载，有节流机制）
            self.chapterSelected.emit(chapter_number)
        finally:
            # 短暂延迟后解除锁定，处理可能的pending点击
            QTimer.singleShot(50, self._finish_click_processing)

    def _update_selection_visual(self, chapter_number):
        """更新选中状态的视觉效果"""
        # 暂停UI更新以批量处理
        self.setUpdatesEnabled(False)
        try:
            # 只更新需要变化的卡片（旧选中和新选中）
            for card in self.chapter_cards:
                card_num = card.chapter_data.get('chapter_number')
                if card_num == self.selected_chapter:
                    # 取消旧的选中状态
                    card.setSelected(False)
                elif card_num == chapter_number:
                    # 设置新的选中状态
                    card.setSelected(True)
        finally:
            self.setUpdatesEnabled(True)

        self.selected_chapter = chapter_number

    def _finish_click_processing(self):
        """完成点击处理，检查是否有pending的点击"""
        self._click_processing = False

        # 如果有pending的点击，处理它
        pending = getattr(self, '_pending_click_chapter', None)
        if pending is not None and pending != self.selected_chapter:
            self._pending_click_chapter = None
            self._on_chapter_card_clicked(pending)

    def _on_hover_prefetch(self, chapter_number):
        """处理悬停预取请求

        当鼠标悬停在章节卡片上300ms后触发，后台预取该章节数据。
        这样当用户真正点击时，数据可能已经在缓存中了。

        Args:
            chapter_number: 章节编号
        """
        from utils.chapter_cache import get_chapter_cache

        project_id = self.project.get('id')
        if not project_id:
            return

        cache = get_chapter_cache()
        cache.prefetch_single(
            project_id,
            chapter_number,
            self.api_client.get_chapter
        )

    def _on_edit_outline(self, chapter_number):
        """处理编辑大纲请求"""
        # 查找当前章节的大纲数据 - 使用辅助方法
        current_outline = None
        blueprint = self._get_blueprint()
        chapter_outlines = blueprint.get('chapter_outline', [])
        
        for outline in chapter_outlines:
            if outline.get('chapter_number') == chapter_number:
                current_outline = outline
                break
        
        if not current_outline:
            MessageService.show_error(self, "无法找到章节大纲数据", "错误")
            return

        # 显示编辑对话框
        title, summary, ok = OutlineEditDialog.getOutlineStatic(
            self,
            chapter_number,
            current_outline.get('title', ''),
            current_outline.get('summary', '')
        )

        if ok:
            try:
                project_id = self.project.get('id')
                # 调用API更新
                updated_project = self.api_client.update_chapter_outline(
                    project_id,
                    chapter_number,
                    title,
                    summary
                )
                
                MessageService.show_success(self, "大纲已更新")
                
                # 更新本地数据并刷新显示
                self.setProject(updated_project)
                
            except Exception as e:
                MessageService.show_error(self, f"更新失败: {str(e)}", "错误")

    def _on_regenerate_outline(self, chapter_number):
        """处理重新生成大纲请求"""
        if not confirm(
            self,
            f"确定要重新生成第 {chapter_number} 章的大纲吗？\n这将会覆盖当前的标题和摘要。",
            "确认重新生成"
        ):
            return

        try:
            project_id = self.project.get('id')
            # 调用API重新生成（不级联删除）
            updated_project = self.api_client.regenerate_chapter_outline(
                project_id,
                chapter_number,
                cascade_delete=False
            )
            
            MessageService.show_success(self, "大纲已重新生成")
            
            # 更新本地数据并刷新显示
            self.setProject(updated_project)
            
        except Exception as e:
            MessageService.show_error(self, f"重生成失败: {str(e)}", "错误")

    def _on_clear_chapter_data(self, chapter_number):
        """处理清空章节数据请求"""
        if not confirm(
            self,
            f"确定要清空第 {chapter_number} 章的数据吗？\n\n"
            f"此操作将删除：\n"
            f"  - 所有生成的版本和内容\n"
            f"  - 摘要和分析数据\n"
            f"  - 漫画分镜和已生成图片\n\n"
            f"章节大纲将保留不变。\n此操作不可恢复！",
            "确认清空章节数据"
        ):
            return

        try:
            project_id = self.project.get('id')
            # 调用API重置章节
            updated_project = self.api_client.reset_chapter(
                project_id,
                chapter_number
            )

            MessageService.show_success(self, f"第 {chapter_number} 章数据已清空")

            # 更新本地数据并刷新显示
            self.setProject(updated_project)

        except Exception as e:
            MessageService.show_error(self, f"清空失败: {str(e)}", "错误")

    def setGeneratingChapter(self, chapter_num):
        """设置正在生成的章节

        Args:
            chapter_num: 章节编号
        """
        self.generating_chapter = chapter_num

        # 更新对应章节卡片的状态
        for card in self.chapter_cards:
            if card.chapter_data.get('chapter_number') == chapter_num:
                card.updateStatus('generating')
                break

    def setChapterGenerating(self, chapter_num: int, is_generating: bool):
        """设置章节的生成状态

        Args:
            chapter_num: 章节编号
            is_generating: 是否正在生成
        """
        if is_generating:
            self.setGeneratingChapter(chapter_num)
        else:
            self.clearGeneratingState()

    def clearGeneratingState(self):
        """清除生成中状态"""
        if self.generating_chapter:
            # 恢复章节状态（假设生成完成后会重新加载项目数据）
            for card in self.chapter_cards:
                if card.chapter_data.get('chapter_number') == self.generating_chapter:
                    # 这里只是清除生成中状态，实际状态会在reload时更新
                    card.updateStatus('not_generated')
                    break

        # 清除标记
        self.generating_chapter = None

    def _load_protagonist_portrait(self):
        """加载主角立绘和信息"""
        if not self.project or not self.blueprint_card:
            logger.debug("无法加载立绘：project或blueprint_card不存在")
            return

        project_id = self.project.get('id')
        if not project_id:
            logger.debug("无法加载立绘：project_id不存在")
            return

        # 使用辅助函数提取主角名称和身份
        protagonist_name = extract_protagonist_name(self.project) or "主角"
        protagonist_identity = self._extract_protagonist_identity()
        logger.info(f"尝试加载主角立绘: {protagonist_name}, 身份: {protagonist_identity}")

        # 加载主角档案同步状态
        self._load_protagonist_sync_status(project_id, protagonist_name)

        # 尝试获取主角立绘
        try:
            # 获取已激活的立绘
            result = self.api_client.get_active_portraits(project_id)
            portraits = result.get('portraits', [])
            logger.info(f"获取到 {len(portraits)} 个激活的立绘")

            if portraits:
                # 找到主角的立绘
                for portrait in portraits:
                    char_name = portrait.get('character_name')
                    logger.debug(f"检查立绘角色: {char_name}")
                    if char_name == protagonist_name:
                        image_path = portrait.get('image_path')
                        if image_path:
                            # 构建完整URL并加载图片
                            image_url = self.api_client.get_portrait_image_url(image_path)
                            logger.info(f"找到主角立绘，URL: {image_url}")
                            self._load_portrait_image(image_url, protagonist_name, protagonist_identity)
                            return

                # 如果没有找到主角的，使用第一个立绘
                first_portrait = portraits[0]
                image_path = first_portrait.get('image_path')
                char_name = first_portrait.get('character_name', protagonist_name)
                if image_path:
                    image_url = self.api_client.get_portrait_image_url(image_path)
                    logger.info(f"未找到主角立绘，使用第一个立绘: {char_name}, URL: {image_url}")
                    self._load_portrait_image(image_url, char_name, protagonist_identity)
                    return

            # 没有立绘，显示占位符
            logger.info("没有激活的立绘，显示占位符")
            self.blueprint_card.setPortraitPlaceholder(protagonist_name, protagonist_identity)

        except Exception as e:
            logger.warning(f"加载主角立绘失败: {e}")
            self.blueprint_card.setPortraitPlaceholder(protagonist_name, protagonist_identity)

    def _extract_protagonist_identity(self) -> str:
        """从蓝图中提取主角身份"""
        blueprint = self._get_blueprint()
        if not blueprint:
            return ""

        characters = blueprint.get('characters', [])
        for char in characters:
            # 检查是否是主角
            identity = char.get('identity', '')
            if '主角' in identity:
                return identity
            if char.get('is_protagonist') or char.get('role') == 'protagonist':
                return identity

        return ""

    def _load_protagonist_sync_status(self, project_id: str, protagonist_name: str):
        """加载主角档案同步状态 - 简化逻辑"""
        try:
            profiles = self.api_client.get_protagonist_profiles(project_id)

            if not profiles:
                # 没有任何档案
                logger.info("没有主角档案，显示'尚未创建档案'")
                self.blueprint_card.setSyncStatus(-1)
                return

            # 优先查找匹配的角色
            for profile in profiles:
                if profile.get('character_name') == protagonist_name:
                    synced_chapter = profile.get('last_synced_chapter', 0)
                    logger.info(f"找到匹配档案: {protagonist_name}, 同步章节: {synced_chapter}")
                    self.blueprint_card.setSyncStatus(synced_chapter)
                    return

            # 没有匹配的，使用第一个档案
            first_profile = profiles[0]
            synced_chapter = first_profile.get('last_synced_chapter', 0)
            logger.info(f"使用第一个档案: {first_profile.get('character_name')}, 同步章节: {synced_chapter}")
            self.blueprint_card.setSyncStatus(synced_chapter)

        except Exception as e:
            logger.warning(f"加载主角同步状态失败: {e}")
            self.blueprint_card.setSyncStatus(-1)

    def _load_portrait_image(self, image_url: str, name: str, identity: str = ""):
        """从URL异步加载立绘图片

        Args:
            image_url: 图片URL
            name: 角色名称
            identity: 角色身份
        """
        from PyQt6.QtGui import QPixmap

        def do_fetch():
            import requests
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                return response.content
            return None

        def on_success(image_data):
            if image_data:
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                if not pixmap.isNull():
                    logger.info(f"立绘图片加载成功: {name}, 尺寸: {pixmap.width()}x{pixmap.height()}")
                    self.blueprint_card.setPortrait(pixmap, name, identity)
                    return
                else:
                    logger.warning("加载的图片数据无效（QPixmap为空）")
            # 加载失败，显示占位符
            self.blueprint_card.setPortraitPlaceholder(name, identity)

        def on_error(error):
            logger.warning(f"加载立绘图片失败: {error}")
            self.blueprint_card.setPortraitPlaceholder(name, identity)

        logger.debug(f"开始异步加载立绘图片: {image_url}")
        self._portrait_worker = AsyncWorker(do_fetch)
        self._portrait_worker.success.connect(on_success)
        self._portrait_worker.error.connect(on_error)
        self._portrait_worker.start()

    def _on_view_profile_requested(self):
        """处理查看主角档案请求"""
        logger.info("请求查看主角档案")
        self.viewProtagonistProfile.emit()

