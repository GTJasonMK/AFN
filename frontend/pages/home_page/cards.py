"""
首页卡片和Tab组件模块

包含项目卡片、Tab按钮和Tab栏组件。
"""

from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareFrame, ThemeAwareButton
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.formatters import get_project_status_text


class RecentProjectCard(ThemeAwareFrame):
    """最近项目卡片 - 继承主题感知基类，自动管理主题信号"""

    # 定义信号
    deleteRequested = pyqtSignal(str, str)  # project_id, title

    def __init__(self, project_data: dict, parent=None, show_delete: bool = False):
        self.project_data = project_data
        self.project_id = project_data.get('id')
        self._show_delete = show_delete  # 是否显示删除按钮
        # 预先声明UI组件
        self.title_label = None
        self.status_label = None
        self.time_label = None
        self.delete_btn = None
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(dp(80))
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(6))

        # 标题行（标题 + 删除按钮）
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        self.title_label = QLabel(self.project_data.get('title', '未命名项目'))
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, 1)

        # 删除按钮（仅在启用时创建，默认隐藏，hover时显示）
        if self._show_delete:
            self.delete_btn = QPushButton("删除")
            self.delete_btn.setFixedSize(dp(48), dp(32))
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.setVisible(False)
            self.delete_btn.clicked.connect(self._on_delete_clicked)
            title_row.addWidget(self.delete_btn)

        layout.addLayout(title_row)

        # 底部信息：状态 + 更新时间
        info_layout = QHBoxLayout()
        info_layout.setSpacing(dp(12))

        # 状态
        status = self.project_data.get('status', 'draft')
        status_text = get_project_status_text(status)
        self.status_label = QLabel(status_text)
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()

        # 更新时间
        updated_at = self.project_data.get('updated_at', '')
        time_text = self._format_time(updated_at)
        self.time_label = QLabel(time_text)
        info_layout.addWidget(self.time_label)

        layout.addLayout(info_layout)

    def _format_time(self, time_str: str) -> str:
        """格式化时间为友好显示"""
        if not time_str:
            return ""
        try:
            # 解析ISO格式时间
            if 'T' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt

            if diff.days == 0:
                if diff.seconds < 3600:
                    return f"{diff.seconds // 60}分钟前"
                else:
                    return f"{diff.seconds // 3600}小时前"
            elif diff.days == 1:
                return "昨天"
            elif diff.days < 7:
                return f"{diff.days}天前"
            else:
                return dt.strftime('%m-%d')
        except (ValueError, TypeError, AttributeError):
            # ValueError: 日期格式解析失败
            # TypeError: 类型不匹配
            # AttributeError: 属性访问失败
            return time_str[:10] if len(time_str) >= 10 else time_str

    def _apply_theme(self):
        bg_color = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()
        ui_font = theme_manager.ui_font()

        self.setStyleSheet(f"""
            RecentProjectCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
            }}
            RecentProjectCard:hover {{
                border-color: {accent_color};
                background-color: {theme_manager.book_bg_primary()};
            }}
        """)

        # 注意：这些属性在_create_ui_structure中创建，
        # setupUI保证_create_ui_structure在_apply_theme之前调用
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(15)}px;
                font-weight: 500;
                color: {text_primary};
                background: transparent;
            }}
        """)

        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(12)}px;
                color: {accent_color};
                background: transparent;
            }}
        """)

        self.time_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(12)}px;
                color: {text_secondary};
                background: transparent;
            }}
        """)

        # 删除按钮样式
        if self.delete_btn:
            self.delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {dp(11)}px;
                }}
                QPushButton:hover {{
                    background-color: #e74c3c;
                    color: white;
                    border-color: #e74c3c;
                }}
            """)

    def enterEvent(self, event):
        """鼠标进入时显示删除按钮"""
        if self.delete_btn:
            self.delete_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开时隐藏删除按钮"""
        if self.delete_btn:
            self.delete_btn.setVisible(False)
        super().leaveEvent(event)

    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        title = self.project_data.get('title', '未命名项目')
        self.deleteRequested.emit(self.project_id, title)

    def mousePressEvent(self, event):
        """点击卡片时通知父组件（排除删除按钮区域）"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击位置是否在删除按钮上
            if self.delete_btn and self.delete_btn.isVisible():
                btn_rect = self.delete_btn.geometry()
                if btn_rect.contains(event.pos()):
                    return  # 让删除按钮处理点击
            # 查找HomePage父组件（延迟导入避免循环引用）
            from .core import HomePage
            parent = self.parent()
            while parent and not isinstance(parent, HomePage):
                parent = parent.parent()
            if parent and hasattr(parent, '_on_project_clicked'):
                parent._on_project_clicked(self.project_data)


class TabButton(ThemeAwareButton):
    """Tab切换按钮 - 继承主题感知基类，自动管理主题信号"""

    def __init__(self, text: str, parent=None):
        self._is_active = False
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setupUI()

    def setActive(self, active: bool):
        """设置激活状态"""
        self._is_active = active
        self.setChecked(active)
        self._apply_theme()

    def _apply_theme(self):
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        ui_font = theme_manager.ui_font()

        if self._is_active:
            # 激活状态
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent_color};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(24)}px;
                    font-family: {ui_font};
                    font-size: {dp(14)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                }}
                QPushButton:focus {{
                    outline: 2px solid {theme_manager.PRIMARY_LIGHT};
                    outline-offset: 2px;
                }}
            """)
        else:
            # 非激活状态
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(24)}px;
                    font-family: {ui_font};
                    font-size: {dp(14)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {accent_color};
                    border-color: {accent_color};
                }}
                QPushButton:focus {{
                    border: 2px solid {accent_color};
                    outline: none;
                }}
            """)


class TabBar(ThemeAwareFrame):
    """Tab栏组件 - 继承主题感知基类，自动管理主题信号"""

    def __init__(self, parent=None):
        self.buttons = []
        self.recent_btn = None
        self.all_btn = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, dp(12))
        layout.setSpacing(dp(12))

        # 最近项目Tab
        self.recent_btn = TabButton("最近项目")
        self.recent_btn.setActive(True)
        layout.addWidget(self.recent_btn)

        # 全部项目Tab
        self.all_btn = TabButton("全部项目")
        layout.addWidget(self.all_btn)

        layout.addStretch()

        self.buttons = [self.recent_btn, self.all_btn]

    def setCurrentIndex(self, index: int):
        """设置当前激活的Tab"""
        for i, btn in enumerate(self.buttons):
            btn.setActive(i == index)

    def _apply_theme(self):
        self.setStyleSheet("background: transparent;")
