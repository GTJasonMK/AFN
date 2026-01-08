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
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens
from utils.dpi_utils import dp, sp
from utils.formatters import format_word_count


class ChapterCard(TransparencyAwareMixin, ThemeAwareWidget):
    """章节卡片组件 - 现代化设计

    显示章节信息：编号、标题、状态、字数
    支持选中状态、悬停效果和右键菜单
    使用 TransparencyAwareMixin 提供透明度控制能力。

    性能优化：
    - 悬停预取：鼠标悬停300ms后触发预取信号
    """

    # 透明度组件标识符 - 作为卡片组件
    _transparency_component_id = "card"

    clicked = pyqtSignal(int)  # chapter_number
    editOutlineRequested = pyqtSignal(int)  # chapter_number
    regenerateOutlineRequested = pyqtSignal(int)  # chapter_number
    clearChapterDataRequested = pyqtSignal(int)  # chapter_number - 清空章节数据
    hoverPrefetchRequested = pyqtSignal(int)  # 悬停预取请求，参数为chapter_number

    def __init__(self, chapter_data, is_selected=False, parent=None):
        """初始化章节卡片

        Args:
            chapter_data: 章节数据字典
            is_selected: 是否选中
        """
        self.chapter_data = chapter_data
        self.is_selected = is_selected
        self._is_hovered = False

        # 悬停预取定时器
        self._hover_prefetch_timer = None
        self._hover_prefetch_delay = 300  # 悬停300ms后触发预取

        # 组件引用
        self.container = None
        self.status_icon = None
        self.number_label = None
        self.title_label = None
        self.meta_label = None

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
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
        """应用主题样式 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 根据选中状态和悬停状态设置卡片样式
        if self.is_selected:
            # 选中状态：渐变边框 + 高亮背景
            border_color = theme_manager.PRIMARY

            if self._transparency_enabled:
                # 透明模式：半透明高亮背景
                bg_color = theme_manager.ACCENT_PALE if not theme_manager.is_dark_mode() else theme_manager.BG_CARD_HOVER
                bg_rgba = self._hex_to_rgba(bg_color, self._current_opacity * 0.8)
                self.container.setStyleSheet(f"""
                    QFrame#chapter_card_container {{
                        background-color: {bg_rgba};
                        border: 2px solid {border_color};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)
            else:
                bg_color = theme_manager.ACCENT_PALE if not theme_manager.is_dark_mode() else theme_manager.BG_CARD_HOVER
                self.container.setStyleSheet(f"""
                    QFrame#chapter_card_container {{
                        background-color: {bg_color};
                        border: 2px solid {border_color};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)

        elif self._is_hovered:
            # 悬停状态
            if self._transparency_enabled:
                # 透明模式：轻微半透明背景
                bg_rgba = self._hex_to_rgba(theme_manager.BG_CARD_HOVER, self._current_opacity * 0.5)
                border_rgba = self._hex_to_rgba(theme_manager.BORDER_DEFAULT, OpacityTokens.BORDER_STRONG)
                self.container.setStyleSheet(f"""
                    QFrame#chapter_card_container {{
                        background-color: {bg_rgba};
                        border: 1px solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)
            else:
                self.container.setStyleSheet(f"""
                    QFrame#chapter_card_container {{
                        background-color: {theme_manager.BG_CARD_HOVER};
                        border: 1px solid {theme_manager.BORDER_DEFAULT};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)
        else:
            # 普通状态
            if self._transparency_enabled:
                # 透明模式：完全透明背景，只保留边框
                border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_MEDIUM)
                self.container.setStyleSheet(f"""
                    QFrame#chapter_card_container {{
                        background-color: transparent;
                        border: 1px solid {border_rgba};
                        border-radius: {theme_manager.RADIUS_MD};
                    }}
                """)
                self._make_widget_transparent(self.container)
            else:
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
            elif status == 'pending':
                color = theme_manager.PRIMARY  # 待确认使用主题色，提示用户需要操作
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
            'completed': '+',      # 已确认版本
            'pending': '*',        # 待确认（有版本但未选择）
            'generating': '~',     # 生成中
            'failed': 'x',         # 生成失败
            'not_generated': 'o'   # 未生成
        }
        return icons.get(status, 'o')

    def _get_meta_text(self):
        """获取元信息文本"""
        status = self.chapter_data.get('status', 'not_generated')
        word_count = self.chapter_data.get('word_count', 0)

        status_texts = {
            'completed': '已完成',
            'pending': '待确认',
            'generating': '生成中...',
            'failed': '生成失败',
            'not_generated': '未生成'
        }

        status_text = status_texts.get(status, '未生成')

        if status in ('completed', 'pending') and word_count > 0:
            return f"{format_word_count(word_count)} - {status_text}"
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

    def update_data(self, chapter_data: dict, is_selected: bool = False):
        """更新章节数据（用于对象池复用）

        Args:
            chapter_data: 新的章节数据
            is_selected: 是否选中
        """
        self.chapter_data = chapter_data
        self.is_selected = is_selected
        self._is_hovered = False

        # 更新UI内容
        chapter_number = chapter_data.get('chapter_number', 0)
        title = chapter_data.get('title', f'第{chapter_number}章')

        if self.number_label:
            self.number_label.setText(f"{chapter_number}.")
        if self.title_label:
            self.title_label.setText(title)
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

        # 只有已生成内容的章节才显示"清空章节数据"选项
        # 且只有最新的已创作章节才能清空（保证小说连贯性）
        can_clear = self.chapter_data.get('can_clear_data', False)
        if can_clear:
            menu.addSeparator()
            clear_action = QAction("清空章节数据", self)
            clear_action.triggered.connect(
                lambda: self.clearChapterDataRequested.emit(self.chapter_data.get('chapter_number', 0))
            )
            menu.addAction(clear_action)

        menu.exec(event.globalPos())

    def enterEvent(self, event):
        """鼠标进入事件"""
        from PyQt6.QtCore import QTimer

        if not self.is_selected:
            self._is_hovered = True
            self._apply_theme()

        # 启动悬停预取定时器
        chapter_number = self.chapter_data.get('chapter_number')
        if chapter_number:
            if self._hover_prefetch_timer is None:
                self._hover_prefetch_timer = QTimer()
                self._hover_prefetch_timer.setSingleShot(True)
                self._hover_prefetch_timer.timeout.connect(self._emit_hover_prefetch)

            self._hover_prefetch_timer.start(self._hover_prefetch_delay)

        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self._apply_theme()

        # 停止悬停预取定时器
        if self._hover_prefetch_timer:
            self._hover_prefetch_timer.stop()

        super().leaveEvent(event)

    def _emit_hover_prefetch(self):
        """发射悬停预取信号"""
        chapter_number = self.chapter_data.get('chapter_number')
        if chapter_number:
            self.hoverPrefetchRequested.emit(chapter_number)
