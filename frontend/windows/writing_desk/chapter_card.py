"""
章节卡片组件 - 现代化设计

用于写作台侧边栏的章节列表项
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QCursor, QAction
from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.formatters import format_word_count


class ChapterCard(ThemeAwareWidget):
    """章节卡片组件 - 现代化设计

    显示章节信息：编号、标题、状态、字数
    支持选中状态、悬停效果和右键菜单
    """

    clicked = pyqtSignal(int)  # chapter_number
    editOutlineRequested = pyqtSignal(int)  # chapter_number
    regenerateOutlineRequested = pyqtSignal(int)  # chapter_number

    def __init__(self, chapter_data, is_selected=False, parent=None):
        """初始化章节卡片

        Args:
            chapter_data: 章节数据字典
            is_selected: 是否选中
        """
        self.chapter_data = chapter_data
        self.is_selected = is_selected
        self._is_hovered = False

        # 组件引用
        self.container = None
        self.status_icon = None
        self.number_label = None
        self.title_label = None
        self.meta_label = None

        super().__init__(parent)
        self.setupUI()

        # 启用鼠标追踪以支持悬停效果
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 卡片容器 - 紧凑版
        self.container = QFrame()
        self.container.setObjectName("chapter_card_container")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        container_layout.setSpacing(dp(10))

        # 左侧：状态图标 - 紧凑版
        self.status_icon = QLabel(self._get_status_icon())
        self.status_icon.setFixedSize(dp(20), dp(20))
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.status_icon)

        # 中间：章节信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(2))

        # 章节标题行（编号 + 标题）
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(4))

        chapter_number = self.chapter_data.get('chapter_number', 0)
        self.number_label = QLabel(f"{chapter_number}.")
        self.number_label.setObjectName("chapter_number")
        title_row.addWidget(self.number_label)

        title = self.chapter_data.get('title', f'第{chapter_number}章')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("chapter_title")
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, stretch=1)

        info_layout.addLayout(title_row)

        # 元信息行（字数 + 状态）
        self.meta_label = QLabel(self._get_meta_text())
        self.meta_label.setObjectName("chapter_meta")
        info_layout.addWidget(self.meta_label)

        container_layout.addWidget(info_widget, stretch=1)

        layout.addWidget(self.container)

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 根据选中状态和悬停状态设置卡片样式
        if self.is_selected:
            # 选中状态：渐变边框 + 高亮背景
            border_color = theme_manager.PRIMARY
            bg_color = theme_manager.ACCENT_PALE if not theme_manager.is_dark_mode() else theme_manager.BG_CARD_HOVER

            self.container.setStyleSheet(f"""
                QFrame#chapter_card_container {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)
        elif self._is_hovered:
            # 悬停状态：浅色背景
            self.container.setStyleSheet(f"""
                QFrame#chapter_card_container {{
                    background-color: {theme_manager.BG_CARD_HOVER};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)
        else:
            # 普通状态：透明背景 + 浅边框
            self.container.setStyleSheet(f"""
                QFrame#chapter_card_container {{
                    background-color: transparent;
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)

        # 状态图标样式
        if self.status_icon:
            status = self.chapter_data.get('status', 'not_generated')
            if status == 'generating':
                color = theme_manager.WARNING
            elif status == 'completed':
                color = theme_manager.SUCCESS
            elif status == 'failed':
                color = theme_manager.ERROR
            else:
                color = theme_manager.TEXT_TERTIARY

            self.status_icon.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(16)}px;
                color: {color};
            """)

        # 章节编号
        if self.number_label:
            self.number_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.PRIMARY};
            """)

        # 章节标题
        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_BASE};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {theme_manager.TEXT_PRIMARY};
            """)

        # 元信息
        if self.meta_label:
            self.meta_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                color: {theme_manager.TEXT_SECONDARY};
            """)

    def _get_status_icon(self):
        """根据状态获取图标"""
        status = self.chapter_data.get('status', 'not_generated')
        icons = {
            'completed': '✓',
            'generating': '🔄',
            'failed': '✗',
            'not_generated': '○'
        }
        return icons.get(status, '○')

    def _get_meta_text(self):
        """获取元信息文本"""
        status = self.chapter_data.get('status', 'not_generated')
        word_count = self.chapter_data.get('word_count', 0)

        status_texts = {
            'completed': '已完成',
            'generating': '生成中...',
            'failed': '生成失败',
            'not_generated': '未生成'
        }

        status_text = status_texts.get(status, '未生成')

        if status == 'completed' and word_count > 0:
            return f"{format_word_count(word_count)} • {status_text}"
        else:
            return status_text

    def setSelected(self, selected):
        """设置选中状态"""
        if self.is_selected != selected:
            self.is_selected = selected
            self._apply_theme()

    def updateStatus(self, status, word_count=None):
        """更新章节状态

        Args:
            status: 新状态
            word_count: 字数（可选）
        """
        self.chapter_data['status'] = status
        if word_count is not None:
            self.chapter_data['word_count'] = word_count

        # 更新UI
        if self.status_icon:
            self.status_icon.setText(self._get_status_icon())
        if self.meta_label:
            self.meta_label.setText(self._get_meta_text())

        self._apply_theme()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            chapter_number = self.chapter_data.get('chapter_number', 0)
            self.clicked.emit(chapter_number)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        serif_font = theme_manager.serif_font()

        # 设置菜单样式
        menu.setStyleSheet(f"""
            QMenu {{
                font-family: {serif_font};
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
                padding: {dp(4)}px;
            }}
            QMenu::item {{
                padding: {dp(6)}px {dp(24)}px;
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(13)}px;
                border-radius: {dp(4)}px;
            }}
            QMenu::item:selected {{
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
            }}
        """)

        # 添加动作
        edit_action = QAction("编辑大纲", self)
        edit_action.triggered.connect(
            lambda: self.editOutlineRequested.emit(self.chapter_data.get('chapter_number', 0))
        )
        menu.addAction(edit_action)

        regenerate_action = QAction("重新生成大纲", self)
        regenerate_action.triggered.connect(
            lambda: self.regenerateOutlineRequested.emit(self.chapter_data.get('chapter_number', 0))
        )
        menu.addAction(regenerate_action)

        menu.exec(event.globalPos())

    def enterEvent(self, event):
        """鼠标进入事件"""
        if not self.is_selected:
            self._is_hovered = True
            self._apply_theme()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self._apply_theme()
        super().leaveEvent(event)
