"""
写作台左侧章节列表

功能：蓝图预览、章节大纲列表、章节选择
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from components.empty_state import EmptyState
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService, confirm
from api.manager import APIClientManager
from .chapter_card import ChapterCard
from .outline_edit_dialog import OutlineEditDialog

logger = logging.getLogger(__name__)


class WDSidebar(ThemeAwareFrame):
    """左侧章节列表 - 禅意风格"""

    chapterSelected = pyqtSignal(int)  # chapter_number
    generateChapter = pyqtSignal(int)
    generateOutline = pyqtSignal()
    createChapter = pyqtSignal()  # 手动新增章节（用于空白项目）

    def __init__(self, project=None, parent=None):
        self.project = project or {}
        self.selected_chapter = None
        self.generating_chapter = None
        self.chapter_cards = []  # 存储所有章节卡片
        self.api_client = APIClientManager.get_client()  # 使用单例客户端

        # 保存组件引用
        self.bp_style = None
        self.bp_summary = None
        self.expand_btn = None  # 展开/收起按钮
        self.summary_card = None  # 故事概要卡片
        self.blueprint_card = None  # 蓝图卡片（用于展开时更新布局）
        self._summary_expanded = False  # 概要展开状态
        self._summary_max_collapsed_height = dp(100)  # 收起状态最大高度
        self.chapters_container = None  # 章节卡片容器
        self.empty_state = None
        self.outline_btn = None
        self.add_chapter_btn = None  # 新增章节按钮

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        logger.info("WDSidebar._create_ui_structure 开始执行")
        self.setFixedWidth(dp(280))  # 从340减少到280，节省60px横向空间

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 从16减少到12
        layout.setSpacing(dp(12))  # 从16减少到12

        # 蓝图预览卡片 - 紧凑版渐变背景
        self.blueprint_card = QFrame()
        self.blueprint_card.setObjectName("blueprint_card")
        blueprint_layout = QVBoxLayout(self.blueprint_card)
        blueprint_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))  # 修正：14不符合8pt网格
        blueprint_layout.setSpacing(dp(12))  # 修正：10不符合8pt网格

        # 蓝图标题行
        bp_header = QHBoxLayout()
        bp_header.setSpacing(dp(12))

        bp_icon = QLabel("◐")
        bp_icon.setObjectName("bp_icon")
        bp_header.addWidget(bp_icon)

        bp_title_widget = QWidget()
        bp_title_layout = QVBoxLayout(bp_title_widget)
        bp_title_layout.setContentsMargins(0, 0, 0, 0)
        bp_title_layout.setSpacing(dp(4))

        bp_title = QLabel("故事蓝图")
        bp_title.setObjectName("bp_title")
        bp_title_layout.addWidget(bp_title)

        self.bp_style = QLabel("未设定风格")
        self.bp_style.setObjectName("bp_style")
        bp_title_layout.addWidget(self.bp_style)

        bp_header.addWidget(bp_title_widget, stretch=1)
        blueprint_layout.addLayout(bp_header)

        # 故事概要卡片 - 紧凑版（支持展开/收起）
        self.summary_card = QFrame()
        self.summary_card.setObjectName("summary_card")
        # 设置大小策略，允许垂直方向随内容变化（Preferred允许扩展）
        self.summary_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))  # 修正：10不符合8pt网格
        summary_layout.setSpacing(dp(4))

        # 概要标题行（标题 + 展开/收起按钮）
        summary_header = QHBoxLayout()
        summary_header.setContentsMargins(0, 0, 0, 0)

        summary_label = QLabel("故事概要")
        summary_label.setObjectName("summary_label")
        summary_header.addWidget(summary_label)

        summary_header.addStretch()

        # 展开/收起按钮
        self.expand_btn = QPushButton("展开")
        self.expand_btn.setObjectName("expand_btn")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setFixedHeight(dp(32))  # 修正：20px不符合触控目标最小值32px
        self.expand_btn.clicked.connect(self._toggle_summary_expand)
        summary_header.addWidget(self.expand_btn)

        summary_layout.addLayout(summary_header)

        self.bp_summary = QLabel("暂无概要")
        self.bp_summary.setObjectName("bp_summary")
        self.bp_summary.setWordWrap(True)
        # 设置文本交互标志以支持选择
        self.bp_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # 收起状态时限制最大高度
        self.bp_summary.setMaximumHeight(self._summary_max_collapsed_height)
        summary_layout.addWidget(self.bp_summary)

        # 记录展开状态
        self._summary_expanded = False

        # 为摘要卡片添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(dp(12))
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, dp(2))
        self.summary_card.setGraphicsEffect(shadow)

        blueprint_layout.addWidget(self.summary_card)
        layout.addWidget(self.blueprint_card)

        # 章节列表标题
        list_header = QWidget()
        list_header.setObjectName("list_header")
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 0, 0, 0)
        list_header_layout.setSpacing(dp(8))

        chapters_title = QLabel("章节列表")
        chapters_title.setObjectName("chapters_title")
        list_header_layout.addWidget(chapters_title, stretch=1)

        # 新增章节按钮（用于空白项目或手动添加）
        self.add_chapter_btn = QPushButton("+")
        self.add_chapter_btn.setObjectName("add_chapter_btn")
        self.add_chapter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_chapter_btn.setToolTip("新增章节")
        self.add_chapter_btn.setFixedSize(dp(32), dp(32))
        self.add_chapter_btn.clicked.connect(self.createChapter.emit)
        list_header_layout.addWidget(self.add_chapter_btn)

        # 生成大纲按钮
        self.outline_btn = QPushButton("生成大纲")
        self.outline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.outline_btn.clicked.connect(self.generateOutline.emit)
        list_header_layout.addWidget(self.outline_btn)

        layout.addWidget(list_header)

        # 章节列表容器（使用滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(theme_manager.scrollbar())

        # 章节容器widget
        self.chapters_container = QWidget()
        self.chapters_layout = QVBoxLayout(self.chapters_container)
        self.chapters_layout.setContentsMargins(0, 0, 0, 0)
        self.chapters_layout.setSpacing(dp(8))  # 修正：6不符合8pt网格
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
        """应用主题样式（可多次调用）"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # Sidebar背景
        self.setStyleSheet(f"""
            WDSidebar {{
                background-color: transparent;
            }}
        """)

        # 蓝图卡片 - 使用渐变背景
        if self.blueprint_card:
            gradient = ModernEffects.linear_gradient(
                theme_manager.PRIMARY_GRADIENT,
                135
            )
            self.blueprint_card.setStyleSheet(f"""
                QFrame#blueprint_card {{
                    background: {gradient};
                    border-radius: {theme_manager.RADIUS_LG};
                    border: none;
                }}
            """)

        # 蓝图图标
        if bp_icon := self.findChild(QLabel, "bp_icon"):
            bp_icon.setStyleSheet(f"""
                font-size: {sp(28)}px;
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 蓝图标题
        if bp_title := self.findChild(QLabel, "bp_title"):
            bp_title.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_LG};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 风格标签
        if self.bp_style:
            self.bp_style.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: rgba(255, 255, 255, 0.9);
                background-color: rgba(255, 255, 255, 0.15);
                padding: {dp(4)}px {dp(8)}px;  /* 修正：10不符合8pt网格 */
                border-radius: {theme_manager.RADIUS_SM};
            """)

        # 摘要卡片 - 白色卡片风格
        if self.summary_card:
            self.summary_card.setStyleSheet(f"""
                QFrame#summary_card {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)

        # 摘要标签
        if summary_label := self.findChild(QLabel, "summary_label"):
            summary_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_SECONDARY};
                text-transform: uppercase;
                letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
            """)

        # 摘要内容
        if self.bp_summary:
            self.bp_summary.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_PRIMARY};
                line-height: {theme_manager.LINE_HEIGHT_RELAXED};
            """)

        # 展开/收起按钮
        if self.expand_btn:
            self.expand_btn.setStyleSheet(f"""
                QPushButton#expand_btn {{
                    font-family: {ui_font};
                    background: transparent;
                    border: none;
                    color: {theme_manager.PRIMARY};
                    font-size: {theme_manager.FONT_SIZE_XS};
                    padding: 0 {dp(4)}px;
                }}
                QPushButton#expand_btn:hover {{
                    color: {theme_manager.TEXT_PRIMARY};
                    text-decoration: underline;
                }}
            """)

        # 列表标题区
        if list_header := self.findChild(QWidget, "list_header"):
            list_header.setStyleSheet("background-color: transparent;")

        # 章节列表标题
        if chapters_title := self.findChild(QLabel, "chapters_title"):
            chapters_title.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_LG};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        # 生成大纲按钮
        if self.outline_btn:
            self.outline_btn.setStyleSheet(ButtonStyles.primary('SM'))

        # 新增章节按钮 - 圆形按钮
        if self.add_chapter_btn:
            self.add_chapter_btn.setStyleSheet(f"""
                QPushButton#add_chapter_btn {{
                    background-color: {theme_manager.BG_SECONDARY};
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(16)}px;
                    font-size: {sp(16)}px;
                    font-weight: bold;
                }}
                QPushButton#add_chapter_btn:hover {{
                    background-color: {theme_manager.PRIMARY_PALE};
                }}
                QPushButton#add_chapter_btn:pressed {{
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                }}
            """)

    def setProject(self, project):
        """设置项目数据"""
        self.project = project

        logger.info(f"WDSidebar.setProject被调用")
        logger.info(f"项目数据键: {list(project.keys()) if isinstance(project, dict) else 'NOT A DICT'}")

        # 更新蓝图预览
        blueprint = project.get('blueprint', {})
        logger.info(f"blueprint存在: {bool(blueprint)}")

        # 判断是否为空白项目
        is_empty_project = not blueprint or not blueprint.get('one_sentence_summary')

        if blueprint:
            logger.info(f"blueprint键: {list(blueprint.keys()) if isinstance(blueprint, dict) else 'NOT A DICT'}")
            style = blueprint.get('style', '未设定风格')
            summary = blueprint.get('one_sentence_summary', '暂无概要')

            if self.bp_style:
                self.bp_style.setText(style)
            if self.bp_summary:
                self.bp_summary.setText(summary)
        else:
            # 空白项目：显示提示信息
            if self.bp_style:
                self.bp_style.setText("自由创作模式")
            if self.bp_summary:
                self.bp_summary.setText("可直接创建章节开始写作，无需生成蓝图和大纲")

        # 根据项目类型调整按钮显示
        if self.outline_btn:
            # 空白项目隐藏生成大纲按钮
            self.outline_btn.setVisible(not is_empty_project)
        if self.add_chapter_btn:
            # 新增章节按钮始终显示（空白项目更需要）
            self.add_chapter_btn.setVisible(True)

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

    def _populate_chapters(self, chapter_outlines):
        """填充章节列表（分批加载，避免UI卡顿）

        合并章节大纲和实际章节数据：
        - 优先使用章节大纲信息（标题、摘要）
        - 补充实际章节的状态和字数
        - 对于没有大纲的手动创建章节，也会显示

        Args:
            chapter_outlines: 章节大纲列表
        """
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

        # 判断是否为空白项目
        blueprint = self.project.get('blueprint', {})
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

        # 分批创建章节卡片（减小批次，更频繁让出事件循环）
        self._pending_chapter_data = chapter_data_list
        self._batch_index = 0
        self._batch_size = 3  # 每批只创建3个卡片，确保动画流畅
        self._create_next_batch()

    def _create_next_batch(self):
        """创建下一批章节卡片"""
        from PyQt6.QtWidgets import QApplication
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

        # 创建这一批卡片（每创建一个就让出事件循环）
        for i in range(start_idx, end_idx):
            chapter_data = self._pending_chapter_data[i]

            # 创建卡片
            card = ChapterCard(chapter_data, is_selected=False)
            card.clicked.connect(self._on_chapter_card_clicked)
            card.editOutlineRequested.connect(self._on_edit_outline)
            card.regenerateOutlineRequested.connect(self._on_regenerate_outline)

            # 添加到布局（插入到stretch之前）
            self.chapters_layout.insertWidget(self.chapters_layout.count() - 1, card)
            self.chapter_cards.append(card)

            # 每创建一个卡片就让出事件循环，确保动画流畅
            QApplication.processEvents()

        # 继续创建下一批
        self._batch_index += 1
        if self._batch_index * self._batch_size < len(self._pending_chapter_data):
            # 使用 QTimer 延迟执行下一批，给UI线程喘息的机会
            QTimer.singleShot(1, self._create_next_batch)
        else:
            logger.info(f"章节列表填充完成，共 {len(self.chapter_cards)} 个卡片")
            self._pending_chapter_data = None

    def _clear_chapters(self):
        """清除所有章节卡片"""
        # 检查chapters_layout是否存在（使用 is None 而非 not，因为空布局 bool() 返回 False）
        if self.chapters_layout is None:
            logger.warning("chapters_layout为None，无法清除章节卡片")
            self.chapter_cards.clear()
            return

        for card in self.chapter_cards:
            self.chapters_layout.removeWidget(card)
            card.deleteLater()
        self.chapter_cards.clear()

        # 移除空状态（如果存在）
        if self.empty_state:
            self.chapters_layout.removeWidget(self.empty_state)
            self.empty_state.deleteLater()
            self.empty_state = None

    def _show_empty_state(self):
        """显示空状态

        根据项目类型显示不同的空状态：
        - 空白项目（无蓝图）：显示"新增章节"按钮
        - 普通项目（有蓝图但无大纲）：显示"生成大纲"提示
        """
        # 检查chapters_layout是否存在
        if self.chapters_layout is None:
            logger.warning("chapters_layout为None，无法显示空状态")
            return

        # 判断是否为空白项目（无蓝图或蓝图为空）
        blueprint = self.project.get('blueprint', {})
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
        logger.info(f"章节卡片被点击: {chapter_number}")

        # 更新选中状态
        for card in self.chapter_cards:
            is_selected = card.chapter_data.get('chapter_number') == chapter_number
            card.setSelected(is_selected)

        self.selected_chapter = chapter_number
        self.chapterSelected.emit(chapter_number)

    def _on_edit_outline(self, chapter_number):
        """处理编辑大纲请求"""
        # 查找当前章节的大纲数据
        current_outline = None
        blueprint = self.project.get('blueprint', {})
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

    def _toggle_summary_expand(self):
        """切换故事概要的展开/收起状态"""
        self._summary_expanded = not self._summary_expanded
        logger.info(f"切换概要展开状态: expanded={self._summary_expanded}")

        if self._summary_expanded:
            # 展开状态：计算文本实际需要的高度
            available_width = self.bp_summary.width()
            if available_width <= 0:
                available_width = self.summary_card.width() - dp(20)  # 减去padding
            if available_width <= 0:
                available_width = dp(200)  # 默认宽度

            # 获取文本实际需要的高度
            font_metrics = self.bp_summary.fontMetrics()
            text = self.bp_summary.text()
            # 使用boundingRect计算多行文本高度
            text_rect = font_metrics.boundingRect(
                0, 0, available_width, 0,
                Qt.TextFlag.TextWordWrap, text
            )
            needed_height = text_rect.height() + dp(10)  # 加一点padding
            logger.info(f"计算展开高度: width={available_width}, needed_height={needed_height}")

            # 展开：移除固定高度限制，让文本自然展开
            self.bp_summary.setMinimumHeight(needed_height)
            self.bp_summary.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.expand_btn.setText("收起")
        else:
            # 收起状态：设置最大高度限制
            logger.info(f"设置收起高度: max={self._summary_max_collapsed_height}")
            self.bp_summary.setMinimumHeight(0)
            self.bp_summary.setMaximumHeight(self._summary_max_collapsed_height)
            self.expand_btn.setText("展开")

        # 强制更新所有相关布局
        self.bp_summary.adjustSize()
        self.bp_summary.updateGeometry()

        if self.summary_card:
            self.summary_card.adjustSize()
            self.summary_card.updateGeometry()
            if self.summary_card.layout():
                self.summary_card.layout().invalidate()
                self.summary_card.layout().activate()

        if self.blueprint_card:
            self.blueprint_card.adjustSize()
            self.blueprint_card.updateGeometry()
            if self.blueprint_card.layout():
                self.blueprint_card.layout().invalidate()
                self.blueprint_card.layout().activate()

        if self.layout():
            self.layout().invalidate()
            self.layout().activate()

        self.adjustSize()
        self.updateGeometry()
        self.update()

