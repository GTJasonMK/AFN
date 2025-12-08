"""
已完成章节 Section - 简洁设计

只显示已选择版本的章节，双面板布局：左侧章节列表 + 右侧正文内容
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QListWidget, QListWidgetItem, QStackedWidget, QScrollArea, QFileDialog, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt
from api.client import ArborisAPIClient
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.error_handler import handle_errors
from utils.message_service import MessageService
from utils.formatters import count_chinese_characters, format_word_count
from utils.dpi_utils import dp, sp


class ChaptersSection(ThemeAwareWidget):
    """已完成章节组件 - 简洁双面板设计

    只显示已选择版本（有正文）的章节
    双面板布局：左侧章节列表 + 右侧正文内容
    """

    dataChanged = pyqtSignal()  # 数据变动信号

    def __init__(self, chapters=None, parent=None):
        self.all_chapters = chapters or []
        self.completed_chapters = []  # 过滤后的已完成章节
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
        self.no_chapters_state = None

        super().__init__(parent)
        self._filter_completed_chapters()
        self.setupUI()

    def _filter_completed_chapters(self):
        """过滤出已完成的章节（已选择版本或有正文）"""
        self.completed_chapters = [
            ch for ch in self.all_chapters
            if ch.get('selected_version') is not None or ch.get('content')
        ]

    def setProjectId(self, project_id):
        """设置项目ID"""
        self.project_id = project_id

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 如果没有已完成章节，显示空状态
        if not self.completed_chapters:
            self._createNoChaptersState(main_layout)
        else:
            # 左侧章节列表
            self._createChapterList(main_layout)
            # 右侧章节详情
            self._createChapterDetail(main_layout)

    def _createNoChaptersState(self, layout):
        """创建无已完成章节的空状态"""
        self.no_chapters_state = QFrame()
        self.no_chapters_state.setObjectName("no_chapters_state")
        no_chapters_layout = QVBoxLayout(self.no_chapters_state)
        no_chapters_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_chapters_layout.setSpacing(dp(16))

        icon = QLabel("*")  # 写作图标
        icon.setObjectName("empty_icon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_chapters_layout.addWidget(icon)

        title = QLabel("暂无已完成章节")
        title.setObjectName("empty_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_chapters_layout.addWidget(title)

        hint = QLabel("在写作台生成章节并选择版本后，章节将显示在这里")
        hint.setObjectName("empty_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        no_chapters_layout.addWidget(hint)

        layout.addWidget(self.no_chapters_state)

    def _createChapterList(self, layout):
        """创建左侧章节列表"""
        self.list_container = QFrame()
        self.list_container.setObjectName("chapter_list_container")
        self.list_container.setFixedWidth(dp(280))

        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # 列表标题
        header = QWidget()
        header.setObjectName("chapter_list_header")
        header.setFixedHeight(dp(56))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(20), 0, dp(20), 0)
        header_layout.setSpacing(dp(8))

        title = QLabel("已完成章节")
        title.setObjectName("list_title")
        header_layout.addWidget(title, stretch=1)

        self.count_label = QLabel(f"{len(self.completed_chapters)} 章")
        self.count_label.setObjectName("count_label")
        header_layout.addWidget(self.count_label)
        
        # 导入按钮
        import_btn = QPushButton("导入")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setObjectName("import_btn")
        import_btn.clicked.connect(self._onImportChapter)
        header_layout.addWidget(import_btn)

        list_layout.addWidget(header)

        # 章节列表
        self.chapter_list_widget = QListWidget()
        self.chapter_list_widget.setObjectName("chapter_list")

        for idx, chapter in enumerate(self.completed_chapters):
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
        layout.setSpacing(dp(4))

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(dp(10))

        # 章节编号徽章
        chapter_num = chapter.get('chapter_number', index + 1)
        num_badge = QLabel(str(chapter_num))
        num_badge.setObjectName("chapter_num_badge")
        num_badge.setFixedSize(dp(28), dp(28))
        num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(num_badge)

        # 章节标题
        title = QLabel(chapter.get('title', f"第{chapter_num}章"))
        title.setObjectName("chapter_item_title")
        title.setWordWrap(False)
        title_layout.addWidget(title, stretch=1)

        layout.addLayout(title_layout)

        # 字数统计
        word_count = chapter.get('word_count', 0)
        if word_count > 0:
            word_label = QLabel(format_word_count(word_count))
            word_label.setObjectName("chapter_item_word_count")
            layout.addWidget(word_label)

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

        empty_icon = QLabel("*")  # 书本图标
        empty_icon.setObjectName("empty_icon")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_text = QLabel("选择章节查看正文")
        empty_text.setObjectName("empty_text")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)

        # 详情区域（使用堆叠布局）
        self.detail_stack = QStackedWidget()
        self.detail_stack.addWidget(self.empty_state)

        detail_layout.addWidget(self.detail_stack)
        layout.addWidget(self.detail_container, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 无章节状态样式
        if self.no_chapters_state:
            self.no_chapters_state.setStyleSheet(f"""
                #no_chapters_state {{
                    background-color: {theme_manager.BG_PRIMARY};
                }}
                #empty_icon {{
                    font-size: {sp(56)}px;
                }}
                #empty_title {{
                    font-family: {ui_font};
                    font-size: {sp(18)}px;
                    font-weight: 600;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
                #empty_hint {{
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                    max-width: {dp(300)}px;
                }}
            """)

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
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: 600;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                #count_label {{
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                    background-color: {theme_manager.BG_TERTIARY};
                    padding: {dp(4)}px {dp(10)}px;
                    border-radius: {dp(10)}px;
                }}
                #import_btn {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(6)}px;
                    padding: {dp(2)}px {dp(8)}px;
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                }}
                #import_btn:hover {{
                    background-color: {theme_manager.PRIMARY_PALE};
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
                    background-color: {theme_manager.PRIMARY_PALE};
                }}
                #chapter_list::item:hover {{
                    background-color: {theme_manager.BG_CARD};
                }}
                #chapter_num_badge {{
                    background-color: {theme_manager.SUCCESS};
                    color: {theme_manager.BUTTON_TEXT};
                    border-radius: {dp(14)}px;
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    font-weight: 700;
                }}
                #chapter_item_title {{
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    font-weight: 500;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                #chapter_item_word_count {{
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {theme_manager.TEXT_TERTIARY};
                    padding-left: {dp(38)}px;
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
                    font-size: {sp(56)}px;
                }}
                #empty_text {{
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: 500;
                    color: {theme_manager.TEXT_TERTIARY};
                }}
            """)

        # 重建当前显示的章节详情以应用新主题
        if self.detail_stack and self.detail_stack.count() > 1:
            # 有显示中的章节详情（不是空状态）
            current_row = self.chapter_list_widget.currentRow() if self.chapter_list_widget else -1
            if current_row >= 0 and current_row < len(self.completed_chapters):
                chapter = self.completed_chapters[current_row]
                chapter_number = chapter.get('chapter_number')
                if chapter_number in self.chapter_cache:
                    # 重新显示章节详情
                    self._displayChapterDetail(self.chapter_cache[chapter_number])

    def _onChapterSelected(self, row):
        """章节被选中"""
        if row < 0 or row >= len(self.completed_chapters):
            return

        chapter = self.completed_chapters[row]
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
        """创建章节详情widget - 只显示正文"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(24), dp(20), dp(24), dp(20))
        layout.setSpacing(dp(16))

        # Header：标题和字数
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-left: 4px solid {theme_manager.SUCCESS};
                border-radius: {dp(10)}px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(16), dp(14), dp(16), dp(14))
        header_layout.setSpacing(dp(16))

        # 章节标题
        chapter_num = detail.get('chapter_number', '')
        title = QLabel(f"第{chapter_num}章  {detail.get('title', '')}")
        title.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(18)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title, stretch=1)

        # 字数统计
        content = detail.get('content', '')
        word_count = count_chinese_characters(content)
        word_label = QLabel(f"{word_count} 字")
        word_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
            background-color: {theme_manager.BG_TERTIARY};
            padding: {dp(6)}px {dp(12)}px;
            border-radius: {dp(12)}px;
        """)
        header_layout.addWidget(word_label)

        # 导出按钮
        export_btn = QPushButton("导出")
        export_btn.setEnabled(bool(content))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(6)}px {dp(14)}px;
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
        header_layout.addWidget(export_btn)

        layout.addWidget(header)

        # 正文内容区域
        content_container = QFrame()
        content_container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(10)}px;
            }}
        """)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {theme_manager.BG_CARD};")
        text_layout = QVBoxLayout(content_widget)
        text_layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))

        # 使用QTextEdit显示正文（只读模式，支持更好的文本排版）
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setPlainText(content if content else "暂无内容")
        content_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-family: {serif_font};
                font-size: {sp(15)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.9;
            }}
        """)
        content_text.setMinimumHeight(dp(400))
        text_layout.addWidget(content_text)

        scroll.setWidget(content_widget)
        content_layout.addWidget(scroll)

        layout.addWidget(content_container, stretch=1)

        return widget

    def _exportChapter(self, detail):
        """导出章节为TXT文件"""
        chapter_num = detail.get('chapter_number', '')
        title = detail.get('title', f'第{chapter_num}章')

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出章节",
            f"第{chapter_num}章_{title}.txt",
            "文本文件 (*.txt)"
        )

        if filename:
            @handle_errors("导出章节")
            def _export():
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"第{chapter_num}章  {title}\n\n")
                    f.write(detail.get('content', ''))
                MessageService.show_operation_success(self, "章节导出")

            _export()

    def _onImportChapter(self):
        """导入章节"""
        if not self.project_id:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入章节文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if not file_path:
            return

        # 询问章节号
        from components.dialogs import IntInputDialog, InputDialog
        default_num = len(self.all_chapters) + 1
        chapter_num, ok = IntInputDialog.getInt(
            self, "导入章节", "请输入章节号:", 
            value=default_num, 
            min_value=1
        )
        if not ok:
            return

        # 询问标题
        import os
        default_title = os.path.splitext(os.path.basename(file_path))[0]
        title, ok = InputDialog.getText(
            self, "导入章节", "请输入章节标题:", text=default_title
        )
        if not ok:
            return

        # 读取内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            MessageService.show_error(self, f"读取文件失败: {e}")
            return

        # 调用API
        @handle_errors("导入章节")
        def _do_import():
            self.api_client.import_chapter(self.project_id, chapter_num, title, content)
            MessageService.show_success(self, "导入成功")
            self.dataChanged.emit()

        _do_import()

    def updateData(self, new_chapters):
        """更新章节数据并刷新显示"""
        self.all_chapters = new_chapters
        self._filter_completed_chapters()

        # 清空缓存
        self.chapter_cache.clear()

        # 如果布局已存在，需要重建
        if self.layout():
            # 清空现有布局
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 重置组件引用
            self.chapter_list_widget = None
            self.count_label = None
            self.list_container = None
            self.detail_container = None
            self.detail_stack = None
            self.empty_state = None
            self.no_chapters_state = None

            # 重建UI
            if not self.completed_chapters:
                self._createNoChaptersState(self.layout())
            else:
                self._createChapterList(self.layout())
                self._createChapterDetail(self.layout())

            # 重新应用样式
            self._apply_theme()

            # 如果有章节，默认选中第一个
            if self.completed_chapters and self.chapter_list_widget:
                self.chapter_list_widget.setCurrentRow(0)
