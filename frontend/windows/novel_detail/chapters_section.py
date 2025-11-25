"""
已生成章节 Section - 现代化设计

双面板布局：左侧章节列表 + 右侧章节详情（正文、版本、评审）
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QListWidget, QListWidgetItem, QStackedWidget, QTabWidget, QScrollArea, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from api.client import ArborisAPIClient
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.error_handler import handle_errors
from utils.message_service import MessageService
from utils.formatters import get_chapter_status_text, get_status_badge_style, count_chinese_characters
from utils.dpi_utils import dp, sp


class ChaptersSection(ThemeAwareWidget):
    """章节内容组件 - 现代化双面板设计

    双面板布局：左侧章节列表 + 右侧章节详情（3个标签页）
    """

    def __init__(self, chapters=None, parent=None):
        self.chapters = chapters or []
        self.api_client = ArborisAPIClient()
        self.selected_chapter = None
        self.chapter_cache = {}
        self.project_id = ''

        # 保存UI组件引用
        self.chapter_list_widget = None
        self.count_label = None
        self.list_container = None
        self.detail_container = None
        self.detail_stack = None
        self.empty_state = None

        super().__init__(parent)
        self.setupUI()

    def setProjectId(self, project_id):
        """设置项目ID"""
        self.project_id = project_id

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧章节列表
        self._createChapterList(main_layout)

        # 右侧章节详情
        self._createChapterDetail(main_layout)

    def _createChapterList(self, layout):
        """创建左侧章节列表"""
        self.list_container = QFrame()
        self.list_container.setObjectName("chapter_list_container")
        self.list_container.setFixedWidth(dp(288))

        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # 列表标题
        header = QWidget()
        header.setObjectName("chapter_list_header")
        header.setFixedHeight(dp(60))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(20), 0, dp(20), 0)
        header_layout.setSpacing(dp(8))

        # 图标
        icon = QLabel("\U0001F4D6")  # 书本图标
        icon.setStyleSheet(f"font-size: {sp(18)}px;")
        header_layout.addWidget(icon)

        title = QLabel("章节")
        title.setObjectName("list_title")
        header_layout.addWidget(title, stretch=1)

        self.count_label = QLabel(f"{len(self.chapters)} 篇")
        self.count_label.setObjectName("count_label")
        header_layout.addWidget(self.count_label)

        list_layout.addWidget(header)

        # 章节列表
        self.chapter_list_widget = QListWidget()
        self.chapter_list_widget.setObjectName("chapter_list")

        for idx, chapter in enumerate(self.chapters):
            item = QListWidgetItem()
            widget = self._createChapterListItem(chapter, idx)
            item.setSizeHint(widget.sizeHint())
            self.chapter_list_widget.addItem(item)
            self.chapter_list_widget.setItemWidget(item, widget)

        self.chapter_list_widget.currentRowChanged.connect(self._onChapterSelected)
        list_layout.addWidget(self.chapter_list_widget)

        layout.addWidget(self.list_container)

    def _createChapterListItem(self, chapter, index):
        """创建章节列表项"""
        widget = QWidget()
        widget.setObjectName("chapter_list_item")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(6))

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(dp(8))

        # 章节编号徽章
        num_badge = QLabel(str(index + 1))
        num_badge.setObjectName("chapter_num_badge")
        num_badge.setFixedSize(dp(28), dp(28))
        num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(num_badge)

        # 章节标题
        title = QLabel(chapter.get('title', f"第{chapter.get('chapter_number', '')}章"))
        title.setObjectName("chapter_item_title")
        title_layout.addWidget(title, stretch=1)

        layout.addLayout(title_layout)

        # 摘要（如果有）
        if chapter.get('summary'):
            summary = QLabel(chapter['summary'])
            summary.setObjectName("chapter_item_summary")
            summary.setWordWrap(True)
            summary.setMaximumHeight(dp(40))
            layout.addWidget(summary)

        return widget

    def _createChapterDetail(self, layout):
        """创建右侧章节详情"""
        self.detail_container = QWidget()
        self.detail_container.setObjectName("chapter_detail_container")
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        # 空状态提示
        self.empty_state = QFrame()
        self.empty_state.setObjectName("empty_state")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(dp(12))

        empty_icon = QLabel("\U0001F4D6")  # 书本图标
        empty_icon.setObjectName("empty_icon")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_text = QLabel("请选择章节查看详细内容")
        empty_text.setObjectName("empty_text")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)

        empty_hint = QLabel("从左侧列表选择一个章节")
        empty_hint.setObjectName("empty_hint")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_hint)

        # 详情区域（使用堆叠布局）
        self.detail_stack = QStackedWidget()
        self.detail_stack.addWidget(self.empty_state)

        detail_layout.addWidget(self.detail_stack)
        layout.addWidget(self.detail_container, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 左侧列表容器样式
        if self.list_container:
            self.list_container.setStyleSheet(f"""
                #chapter_list_container {{
                    background-color: {theme_manager.BG_SECONDARY};
                    border-right: 1px solid {theme_manager.BORDER_LIGHT};
                }}
                #chapter_list_header {{
                    background-color: transparent;
                    border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
                }}
                #list_title {{
                    font-size: {sp(15)}px;
                    font-weight: 600;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                #count_label {{
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                    background-color: {theme_manager.BG_TERTIARY};
                    padding: {dp(4)}px {dp(10)}px;
                    border-radius: {dp(10)}px;
                }}
                #chapter_list {{
                    background-color: transparent;
                    border: none;
                    outline: none;
                }}
                #chapter_list::item {{
                    border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
                    padding: 0;
                }}
                #chapter_list::item:selected {{
                    background-color: {theme_manager.ACCENT_PALE};
                }}
                #chapter_list::item:hover {{
                    background-color: {theme_manager.BG_CARD};
                }}
                #chapter_num_badge {{
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border-radius: {dp(14)}px;
                    font-size: {sp(12)}px;
                    font-weight: 700;
                }}
                #chapter_item_title {{
                    font-size: {sp(14)}px;
                    font-weight: 500;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                #chapter_item_summary {{
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                    padding-left: {dp(36)}px;
                }}
            """)

        # 右侧详情区域样式
        if self.detail_container:
            self.detail_container.setStyleSheet(f"""
                #chapter_detail_container {{
                    background-color: {theme_manager.BG_PRIMARY};
                }}
                #empty_state {{
                    background-color: {theme_manager.BG_PRIMARY};
                }}
                #empty_icon {{
                    font-size: {sp(64)}px;
                }}
                #empty_text {{
                    font-size: {sp(16)}px;
                    font-weight: 600;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
                #empty_hint {{
                    font-size: {sp(13)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                }}
            """)

    def _onChapterSelected(self, row):
        """章节被选中"""
        if row < 0 or row >= len(self.chapters):
            return

        chapter = self.chapters[row]
        chapter_number = chapter.get('chapter_number')

        # 加载章节详情
        self._loadChapterDetail(chapter_number)

    @handle_errors("加载章节详情")
    def _loadChapterDetail(self, chapter_number):
        """加载章节详情"""
        # 检查缓存
        if chapter_number in self.chapter_cache:
            self._displayChapterDetail(self.chapter_cache[chapter_number])
            return

        # 从API加载
        if not self.project_id:
            MessageService.show_warning(self, "未设置项目ID", "提示")
            return

        detail = self.api_client.get_chapter(self.project_id, chapter_number)
        self.chapter_cache[chapter_number] = detail
        self._displayChapterDetail(detail)

    def _displayChapterDetail(self, detail):
        """显示章节详情"""
        # 移除旧的详情widget
        while self.detail_stack.count() > 1:
            widget = self.detail_stack.widget(1)
            self.detail_stack.removeWidget(widget)
            widget.deleteLater()

        # 创建新的详情widget
        detail_widget = self._createChapterDetailWidget(detail)
        self.detail_stack.addWidget(detail_widget)
        self.detail_stack.setCurrentWidget(detail_widget)

    def _createChapterDetailWidget(self, detail):
        """创建章节详情widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        layout.setSpacing(dp(16))

        # Header：标题、字数、状态
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-left: 4px solid {theme_manager.PRIMARY};
                padding: {dp(16)}px;
                border-radius: {dp(12)}px;
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(dp(12))

        title_row = QHBoxLayout()
        title_row.setSpacing(dp(12))

        # 图标
        icon = QLabel("\U0001F4DD")  # 备忘录图标
        icon.setStyleSheet(f"font-size: {sp(20)}px;")
        title_row.addWidget(icon)

        title = QLabel(detail.get('title', f"第{detail.get('chapter_number', '')}章"))
        title.setStyleSheet(f"font-size: {sp(20)}px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};")
        title_row.addWidget(title, stretch=1)

        # 状态标签
        status = detail.get('generation_status', 'not_generated')
        status_badge = QLabel(get_chapter_status_text(status))
        status_badge.setStyleSheet(f"""
            {get_status_badge_style(status)}
            padding: {dp(6)}px {dp(14)}px;
            border-radius: {dp(12)}px;
            font-size: {sp(11)}px;
            font-weight: 600;
        """)
        title_row.addWidget(status_badge)

        header_layout.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(dp(16))

        chapter_num = QLabel(f"\U0001F4D1 第 {detail.get('chapter_number', '')} 章")  # 书签图标
        chapter_num.setStyleSheet(f"font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};")
        meta_row.addWidget(chapter_num)

        word_count = count_chinese_characters(detail.get('content'))
        word_label = QLabel(f"\u270F\uFE0F {word_count} 字")  # 铅笔图标
        word_label.setStyleSheet(f"font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};")
        meta_row.addWidget(word_label)

        meta_row.addStretch()

        # 导出按钮
        export_btn = QPushButton("\U0001F4E4 导出TXT")  # 导出图标
        export_btn.setEnabled(bool(detail.get('content')))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BG_SECONDARY};
            }}
        """)
        export_btn.clicked.connect(lambda: self._exportChapter(detail))
        meta_row.addWidget(export_btn)

        header_layout.addLayout(meta_row)
        layout.addWidget(header)

        # TabWidget：正文、版本、评审
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(theme_manager.tabs())

        # Tab 1: 正文
        content_tab = self._createContentTab(detail)
        tab_widget.addTab(content_tab, "\U0001F4C4 正文")  # 文档图标

        # Tab 2: 版本历史
        versions_tab = self._createVersionsTab(detail)
        tab_widget.addTab(versions_tab, f"\U0001F504 版本 ({detail.get('version_count', 0)})")  # 刷新图标

        # Tab 3: 评审反馈
        reviews_tab = self._createReviewsTab(detail)
        tab_widget.addTab(reviews_tab, "\U0001F4AC 评审")  # 对话图标

        layout.addWidget(tab_widget, stretch=1)

        return widget

    def _createContentTab(self, detail):
        """创建正文标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(theme_manager.scrollbar())

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))

        content = detail.get('content', '暂无内容')
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_label.setStyleSheet(f"""
            font-size: {sp(15)}px;
            color: {theme_manager.TEXT_PRIMARY};
            line-height: 1.8;
        """)
        content_layout.addWidget(content_label)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        return scroll

    def _createVersionsTab(self, detail):
        """创建版本历史标签页"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_SECONDARY};
                border-radius: {dp(12)}px;
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(12))

        icon = QLabel("\U0001F4C1")  # 文件夹图标
        icon.setStyleSheet(f"font-size: {sp(48)}px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        label = QLabel("版本历史功能待实现")
        label.setStyleSheet(f"font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        hint = QLabel("敬请期待后续更新")
        hint.setStyleSheet(f"font-size: {sp(12)}px; color: {theme_manager.TEXT_TERTIARY};")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        return widget

    def _createReviewsTab(self, detail):
        """创建评审标签页"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_SECONDARY};
                border-radius: {dp(12)}px;
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(12))

        icon = QLabel("\U0001F50D")  # 放大镜图标
        icon.setStyleSheet(f"font-size: {sp(48)}px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        label = QLabel("评审功能待实现")
        label.setStyleSheet(f"font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        hint = QLabel("敬请期待后续更新")
        hint.setStyleSheet(f"font-size: {sp(12)}px; color: {theme_manager.TEXT_TERTIARY};")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        return widget

    def _exportChapter(self, detail):
        """导出章节为TXT文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出章节",
            f"第{detail.get('chapter_number', '')}章.txt",
            "文本文件 (*.txt)"
        )

        if filename:
            @handle_errors("导出章节")
            def _export():
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"{detail.get('title', '')}\n\n")
                    f.write(detail.get('content', ''))
                MessageService.show_operation_success(self, "章节导出")

            _export()

    def updateData(self, new_chapters):
        """更新章节数据并刷新显示"""
        # 保存当前选中的章节编号
        selected_chapter_number = None
        if self.selected_chapter:
            selected_chapter_number = self.selected_chapter.get('chapter_number')

        # 更新数据
        self.chapters = new_chapters
        self.chapter_cache.clear()

        # 更新章节数量显示
        if self.count_label:
            self.count_label.setText(f"{len(self.chapters)} 篇")

        # 清空并重建章节列表
        if self.chapter_list_widget:
            self.chapter_list_widget.clear()

            for idx, chapter in enumerate(self.chapters):
                item = QListWidgetItem()
                widget = self._createChapterListItem(chapter, idx)
                item.setSizeHint(widget.sizeHint())
                self.chapter_list_widget.addItem(item)
                self.chapter_list_widget.setItemWidget(item, widget)

            # 重新应用样式
            self._apply_theme()

            # 尝试恢复选中状态
            if selected_chapter_number:
                for idx, chapter in enumerate(self.chapters):
                    if chapter.get('chapter_number') == selected_chapter_number:
                        self.chapter_list_widget.setCurrentRow(idx)
                        break
            elif self.chapters:
                # 如果之前没有选中或找不到，选中第一个
                self.chapter_list_widget.setCurrentRow(0)
