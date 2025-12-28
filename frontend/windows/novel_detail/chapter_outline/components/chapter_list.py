"""
章节大纲列表组件

显示章节大纲列表，包含滚动区域和操作按钮
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.component_pool import ComponentPool, reset_chapter_outline_card
from .chapter_card import ChapterOutlineCard

logger = logging.getLogger(__name__)


class ChapterOutlineList(QWidget):
    """章节大纲列表 - 包含滚动区域和操作按钮"""

    editAllClicked = pyqtSignal()
    flexibleGenerateClicked = pyqtSignal()
    deleteLastClicked = pyqtSignal()
    regenerateChapterClicked = pyqtSignal(int)  # 章节号

    def __init__(
        self,
        outlines: list,
        total_chapters: int = 0,
        editable: bool = True,
        show_header: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.outlines = outlines or []
        self.total_chapters = total_chapters
        self.editable = editable
        self.show_header = show_header
        self.chapter_cards = []

        # 组件池：复用章节大纲卡片
        self._card_pool = ComponentPool(
            ChapterOutlineCard,
            max_size=100,
            factory_kwargs={'chapter': {}, 'editable': self.editable},
            reset_callback=reset_chapter_outline_card
        )

        logger.info(
            f"ChapterOutlineList初始化: "
            f"outlines数量={len(self.outlines)}, "
            f"total_chapters={self.total_chapters}, "
            f"show_header={self.show_header}"
        )

        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(dp(16))

        # 头部区域
        if self.show_header:
            self._create_header()

        # 章节列表滚动区域
        self._create_scroll_area()

        # 底部操作按钮
        if self.editable:
            self._create_action_bar()

    def _create_header(self):
        """创建头部区域"""
        header = QHBoxLayout()

        self.title_label = QLabel("章节大纲")
        header.addWidget(self.title_label, stretch=1)

        self.progress_label = QLabel(f"已生成 {len(self.outlines)} / {self.total_chapters} 章")
        header.addWidget(self.progress_label)

        if self.editable and len(self.outlines) > 0:
            self.edit_btn = QPushButton("编辑全部大纲")
            self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.edit_btn.clicked.connect(self.editAllClicked.emit)
            header.addWidget(self.edit_btn)

        self._layout.addLayout(header)

    def _create_scroll_area(self):
        """创建滚动区域"""
        # 始终创建滚动区域，即使初始时没有数据
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(dp(16))

        logger.info(f"创建滚动区域，当前outlines数量: {len(self.outlines)}")

        # 创建章节卡片（如果有数据）- 使用组件池
        if self.outlines:
            logger.info(f"开始创建 {len(self.outlines)} 个章节卡片")
            for idx, chapter in enumerate(self.outlines):
                chapter_number = chapter.get('chapter_number', idx + 1)
                logger.info(f"创建章节卡片: 第{chapter_number}章 - {chapter.get('title', '无标题')}")
                # 从池中获取卡片
                card = self._card_pool.acquire()
                card.update_data(chapter)
                card.regenerateClicked.connect(self.regenerateChapterClicked.emit)
                self.chapter_cards.append(card)
                self.scroll_layout.addWidget(card)
                card.show()  # 池中的组件被hide了，需要显示
            logger.info(f"章节卡片创建完成，共 {len(self.chapter_cards)} 个")
        else:
            logger.warning("outlines为空，不创建章节卡片")

        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        self._layout.addWidget(self.scroll, stretch=1)

    def _create_action_bar(self):
        """创建底部操作按钮栏"""
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(dp(12))

        # 灵活生成按钮
        if len(self.outlines) < self.total_chapters:
            self.generate_btn = QPushButton("灵活生成章节大纲")
            self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.generate_btn.clicked.connect(self.flexibleGenerateClicked.emit)
            actions_layout.addWidget(self.generate_btn)

        # 删除按钮
        if len(self.outlines) > 0:
            self.delete_btn = QPushButton("删除最后N章")
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.clicked.connect(self.deleteLastClicked.emit)
            actions_layout.addWidget(self.delete_btn)

        actions_layout.addStretch()
        self._layout.addLayout(actions_layout)

    def _apply_style(self):
        """应用样式"""
        # 标题样式
        if self.show_header:
            self.title_label.setStyleSheet(
                f"font-size: {sp(20)}px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};"
            )
            self.progress_label.setStyleSheet(
                f"font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY};"
            )
            if self.editable and len(self.outlines) > 0 and hasattr(self, 'edit_btn'):
                self.edit_btn.setStyleSheet(theme_manager.button_secondary())

        # 滚动区域样式
        if hasattr(self, 'scroll'):
            self.scroll.setStyleSheet(f"{theme_manager.scrollbar()}")

        # 操作按钮样式
        if self.editable:
            if hasattr(self, 'generate_btn'):
                self.generate_btn.setStyleSheet(ButtonStyles.primary())
            if hasattr(self, 'delete_btn'):
                self.delete_btn.setStyleSheet(ButtonStyles.outline_danger())

        # 更新所有章节卡片样式
        for card in self.chapter_cards:
            card.update_theme()

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_data(self, outlines: list, total_chapters: int):
        """更新数据"""
        self.outlines = outlines or []
        self.total_chapters = total_chapters

        # 更新进度标签
        if self.show_header and hasattr(self, 'progress_label'):
            self.progress_label.setText(f"已生成 {len(self.outlines)} / {self.total_chapters} 章")

        # 释放旧的章节卡片回池
        if hasattr(self, 'scroll_layout'):
            for card in self.chapter_cards:
                try:
                    card.regenerateClicked.disconnect(self.regenerateChapterClicked.emit)
                except (TypeError, RuntimeError):
                    pass
                self.scroll_layout.removeWidget(card)
                self._card_pool.release(card)

            # 清空其他widget（如stretch）
            while self.scroll_layout.count():
                item = self.scroll_layout.takeAt(0)
                if item.widget() and item.widget() not in self.chapter_cards:
                    item.widget().deleteLater()

        self.chapter_cards.clear()

        # 重建章节卡片 - 使用组件池
        if self.outlines and hasattr(self, 'scroll_layout'):
            for chapter in self.outlines:
                card = self._card_pool.acquire()
                card.update_data(chapter)
                card.regenerateClicked.connect(self.regenerateChapterClicked.emit)
                self.chapter_cards.append(card)
                self.scroll_layout.addWidget(card)
                card.show()  # 池中的组件被hide了，需要显示
            self.scroll_layout.addStretch()

        self._apply_style()

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
