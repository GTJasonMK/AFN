"""
大纲操作按钮栏

提供三个统一的操作按钮：
1. 重新生成最新N个
2. 删除最新N个
3. 继续生成N个
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QWidget, QVBoxLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class OutlineActionBar(QFrame):
    """大纲操作按钮栏"""

    regenerateLatestClicked = pyqtSignal()  # 重新生成最新N个
    deleteLatestClicked = pyqtSignal()  # 删除最新N个
    continueGenerateClicked = pyqtSignal()  # 继续生成N个
    addOutlineClicked = pyqtSignal()  # 手动新增大纲

    def __init__(
        self,
        title: str = "大纲",
        current_count: int = 0,
        total_count: int = 0,
        outline_type: str = "chapter",  # "chapter" 或 "part"
        editable: bool = True,
        show_continue_button: bool = True,  # 是否显示"继续生成"按钮
        show_add_button: bool = True,  # 是否显示"新增"按钮
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.current_count = current_count
        self.total_count = total_count
        self.outline_type = outline_type
        self.editable = editable
        self.show_continue_button = show_continue_button
        self.show_add_button = show_add_button
        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(16))

        # 左侧: 标题和进度信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        self.title_label = QLabel(self.title)
        info_layout.addWidget(self.title_label)

        type_text = "章节" if self.outline_type == "chapter" else "部分"
        self.progress_label = QLabel(f"已生成 {self.current_count} / {self.total_count} {type_text}")
        info_layout.addWidget(self.progress_label)

        layout.addWidget(info_widget, stretch=1)

        # 右侧: 操作按钮
        if self.editable:
            # 新增按钮（仅在show_add_button为True时显示）
            self.add_btn = None
            if self.show_add_button:
                self.add_btn = QPushButton("新增")
                self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.add_btn.setToolTip(f"手动新增一个{type_text}大纲")
                self.add_btn.clicked.connect(self.addOutlineClicked.emit)
                layout.addWidget(self.add_btn)

            # 继续生成按钮（仅在show_continue_button为True时显示）
            self.continue_btn = None
            if self.show_continue_button:
                self.continue_btn = QPushButton("继续生成")
                self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.continue_btn.setToolTip(f"继续生成N个{type_text}")
                self.continue_btn.clicked.connect(self.continueGenerateClicked.emit)
                layout.addWidget(self.continue_btn)

            # 重新生成按钮
            self.regenerate_btn = QPushButton("重新生成最新")
            self.regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.regenerate_btn.setToolTip(f"重新生成最新的N个{type_text}大纲")
            self.regenerate_btn.clicked.connect(self.regenerateLatestClicked.emit)
            layout.addWidget(self.regenerate_btn)

            # 删除按钮
            self.delete_btn = QPushButton("删除最新")
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.setToolTip(f"删除最新的N个{type_text}大纲")
            self.delete_btn.clicked.connect(self.deleteLatestClicked.emit)
            layout.addWidget(self.delete_btn)

    def _apply_style(self):
        """应用样式"""
        # 容器样式
        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        self.setStyleSheet(f"""
            background-color: {theme_manager.BG_CARD};
            border: 1px solid {theme_manager.BORDER_LIGHT};
            border-radius: {dp(12)}px;
        """)

        # 标题样式
        self.title_label.setStyleSheet(
            f"background: transparent; border: none; font-size: {sp(18)}px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};"
        )

        # 进度标签样式
        self.progress_label.setStyleSheet(
            f"background: transparent; border: none; font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};"
        )

        # 按钮样式
        if self.editable:
            # 新增按钮 - 次要按钮样式（如果存在）
            if self.add_btn:
                self.add_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme_manager.BG_SECONDARY};
                        color: {theme_manager.PRIMARY};
                        border: 1px solid {theme_manager.PRIMARY};
                        border-radius: {dp(6)}px;
                        padding: {dp(8)}px {dp(16)}px;
                        font-size: {sp(13)}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {theme_manager.PRIMARY_PALE};
                    }}
                    QPushButton:disabled {{
                        background-color: {theme_manager.BG_TERTIARY};
                        color: {theme_manager.TEXT_DISABLED};
                        border-color: {theme_manager.BORDER_LIGHT};
                    }}
                """)

            # 继续生成按钮 - 主按钮样式（如果存在）
            if self.continue_btn:
                self.continue_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme_manager.PRIMARY};
                        color: {theme_manager.BUTTON_TEXT};
                        border: none;
                        border-radius: {dp(6)}px;
                        padding: {dp(8)}px {dp(16)}px;
                        font-size: {sp(13)}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {theme_manager.PRIMARY_DARK};
                    }}
                    QPushButton:disabled {{
                        background-color: {theme_manager.BG_TERTIARY};
                        color: {theme_manager.TEXT_DISABLED};
                    }}
                """)

            # 重新生成按钮 - 警告样式
            self.regenerate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.WARNING_BG};
                    color: {theme_manager.WARNING};
                    border: 1px solid {theme_manager.WARNING};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                    color: {theme_manager.BUTTON_TEXT};
                }}
                QPushButton:disabled {{
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_DISABLED};
                    border-color: {theme_manager.BORDER_LIGHT};
                }}
            """)

            # 删除按钮 - 危险样式
            self.delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.ERROR_BG};
                    color: {theme_manager.ERROR};
                    border: 1px solid {theme_manager.ERROR};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.ERROR};
                    color: {theme_manager.BUTTON_TEXT};
                }}
                QPushButton:disabled {{
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_DISABLED};
                    border-color: {theme_manager.BORDER_LIGHT};
                }}
            """)

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_progress(self, current_count: int, total_count: int):
        """更新进度信息"""
        self.current_count = current_count
        self.total_count = total_count
        type_text = "章节" if self.outline_type == "chapter" else "部分"
        self.progress_label.setText(f"已生成 {current_count} / {total_count} {type_text}")

        # 根据状态启用/禁用按钮
        if self.editable:
            # 如果已生成数量为0，禁用重新生成和删除按钮
            has_outlines = current_count > 0
            self.regenerate_btn.setEnabled(has_outlines)
            self.delete_btn.setEnabled(has_outlines)

            # 如果已达到总数，禁用继续生成按钮（如果存在）
            if self.continue_btn:
                can_generate_more = current_count < total_count
                self.continue_btn.setEnabled(can_generate_more)

    def set_buttons_enabled(self, enabled: bool):
        """设置所有按钮的启用状态"""
        if self.editable:
            if self.add_btn:
                self.add_btn.setEnabled(enabled)
            if self.continue_btn:
                self.continue_btn.setEnabled(enabled)
            self.regenerate_btn.setEnabled(enabled)
            self.delete_btn.setEnabled(enabled)

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
