"""
写作台左侧章节列表

功能：蓝图预览、章节大纲列表、章节选择
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QScrollArea, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from components.empty_state import EmptyState
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.formatters import count_chinese_characters

from .chapter_card import ChapterCard

logger = logging.getLogger(__name__)


class WDSidebar(ThemeAwareFrame):
    """左侧章节列表 - 禅意风格"""

    chapterSelected = pyqtSignal(int)  # chapter_number
    generateChapter = pyqtSignal(int)
    generateOutline = pyqtSignal()

    def __init__(self, project=None, parent=None):
        self.project = project or {}
        self.selected_chapter = None
        self.generating_chapter = None
        self.chapter_cards = []  # 存储所有章节卡片

        # 保存组件引用
        self.bp_style = None
        self.bp_summary = None
        self.chapters_container = None  # 章节卡片容器
        self.empty_state = None
        self.outline_btn = None

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
        blueprint_card = QFrame()
        blueprint_card.setObjectName("blueprint_card")
        blueprint_layout = QVBoxLayout(blueprint_card)
        blueprint_layout.setContentsMargins(dp(14), dp(14), dp(14), dp(14))  # 从20减少到14
        blueprint_layout.setSpacing(dp(10))  # 从12减少到10

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

        # 故事概要卡片 - 紧凑版
        summary_card = QFrame()
        summary_card.setObjectName("summary_card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(dp(10), dp(10), dp(10), dp(10))  # 从14减少到10
        summary_layout.setSpacing(dp(4))  # 从6减少到4

        summary_label = QLabel("故事概要")
        summary_label.setObjectName("summary_label")
        summary_layout.addWidget(summary_label)

        self.bp_summary = QLabel("暂无概要")
        self.bp_summary.setObjectName("bp_summary")
        self.bp_summary.setWordWrap(True)
        summary_layout.addWidget(self.bp_summary)

        # 为摘要卡片添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(dp(12))
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, dp(2))
        summary_card.setGraphicsEffect(shadow)

        blueprint_layout.addWidget(summary_card)
        layout.addWidget(blueprint_card)

        # 章节列表标题
        list_header = QWidget()
        list_header.setObjectName("list_header")
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 0, 0, 0)
        list_header_layout.setSpacing(dp(12))

        chapters_title = QLabel("章节列表")
        chapters_title.setObjectName("chapters_title")
        list_header_layout.addWidget(chapters_title, stretch=1)

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
        self.chapters_layout.setSpacing(dp(6))  # 从8减少到6
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
        # Sidebar背景
        self.setStyleSheet(f"""
            WDSidebar {{
                background-color: transparent;
            }}
        """)

        # 蓝图卡片 - 使用渐变背景
        if blueprint_card := self.findChild(QFrame, "blueprint_card"):
            gradient = ModernEffects.linear_gradient(
                theme_manager.PRIMARY_GRADIENT,
                135
            )
            blueprint_card.setStyleSheet(f"""
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
                font-size: {theme_manager.FONT_SIZE_LG};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 风格标签
        if self.bp_style:
            self.bp_style.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_SM};
                color: rgba(255, 255, 255, 0.9);
                background-color: rgba(255, 255, 255, 0.15);
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {theme_manager.RADIUS_SM};
            """)

        # 摘要卡片 - 白色卡片风格
        if summary_card := self.findChild(QFrame, "summary_card"):
            summary_card.setStyleSheet(f"""
                QFrame#summary_card {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)

        # 摘要标签
        if summary_label := self.findChild(QLabel, "summary_label"):
            summary_label.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_XS};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_SECONDARY};
                text-transform: uppercase;
                letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
            """)

        # 摘要内容
        if self.bp_summary:
            self.bp_summary.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_PRIMARY};
                line-height: {theme_manager.LINE_HEIGHT_RELAXED};
            """)

        # 列表标题区
        if list_header := self.findChild(QWidget, "list_header"):
            list_header.setStyleSheet("background-color: transparent;")

        # 章节列表标题
        if chapters_title := self.findChild(QLabel, "chapters_title"):
            chapters_title.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_LG};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        # 生成大纲按钮
        if self.outline_btn:
            self.outline_btn.setStyleSheet(ButtonStyles.primary('SM'))

    def setProject(self, project):
        """设置项目数据"""
        self.project = project

        logger.info(f"WDSidebar.setProject被调用")
        logger.info(f"项目数据键: {list(project.keys()) if isinstance(project, dict) else 'NOT A DICT'}")

        # 更新蓝图预览
        blueprint = project.get('blueprint', {})
        logger.info(f"blueprint存在: {bool(blueprint)}")
        if blueprint:
            logger.info(f"blueprint键: {list(blueprint.keys()) if isinstance(blueprint, dict) else 'NOT A DICT'}")
            style = blueprint.get('style', '未设定风格')
            summary = blueprint.get('one_sentence_summary', '暂无概要')

            if self.bp_style:
                self.bp_style.setText(style)
            if self.bp_summary:
                self.bp_summary.setText(summary)

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
        """填充章节列表

        Args:
            chapter_outlines: 章节大纲列表
        """
        # 清除旧的卡片
        self._clear_chapters()

        if not chapter_outlines:
            logger.warning("chapter_outline为空，显示空状态")
            self._show_empty_state()
            return

        logger.info(f"开始填充章节列表，共 {len(chapter_outlines)} 章")

        # 获取已完成章节的信息（用于显示字数）
        project_chapters = self.project.get('chapters', [])
        chapters_map = {ch.get('chapter_number'): ch for ch in project_chapters}

        # 创建章节卡片
        for idx, outline in enumerate(chapter_outlines):
            chapter_num = outline.get('chapter_number', idx + 1)
            title = outline.get('title', f'第{chapter_num}章')

            # 获取章节状态和字数
            chapter_info = chapters_map.get(chapter_num, {})
            content = chapter_info.get('content', '')
            word_count = count_chinese_characters(content) if content else 0

            # 确定状态
            if content:
                status = 'completed'
            else:
                status = 'not_generated'

            chapter_data = {
                'chapter_number': chapter_num,
                'title': title,
                'status': status,
                'word_count': word_count
            }

            # 创建卡片
            card = ChapterCard(chapter_data, is_selected=False)
            card.clicked.connect(self._on_chapter_card_clicked)

            # 添加到布局（插入到stretch之前）
            self.chapters_layout.insertWidget(self.chapters_layout.count() - 1, card)
            self.chapter_cards.append(card)

            logger.info(f"添加章节卡片: {chapter_num}. {title} - {status}")

        logger.info(f"章节列表填充完成，共 {len(self.chapter_cards)} 个卡片")

    def _clear_chapters(self):
        """清除所有章节卡片"""
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
        """显示空状态"""
        self.empty_state = EmptyState(
            icon='📖',
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

