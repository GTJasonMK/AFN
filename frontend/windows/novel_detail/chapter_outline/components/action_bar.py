"""
大纲操作按钮栏

提供三个统一的操作按钮：
1. 重新生成最新N个
2. 删除最新N个
3. 继续生成N个
"""

from typing import Optional

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
        show_regenerate_button: bool = True,  # 是否显示"重新生成"按钮
        show_delete_button: bool = True,  # 是否显示"删除"按钮
        show_progress: bool = True,  # 是否显示进度信息
        add_label: str = "新增",
        continue_label: str = "继续生成",
        regenerate_label: str = "重新生成最新",
        delete_label: str = "删除最新",
        add_tooltip: Optional[str] = None,
        continue_tooltip: Optional[str] = None,
        regenerate_tooltip: Optional[str] = None,
        delete_tooltip: Optional[str] = None,
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
        self.show_regenerate_button = show_regenerate_button
        self.show_delete_button = show_delete_button
        self.show_progress = show_progress
        self.add_label = add_label
        self.continue_label = continue_label
        self.regenerate_label = regenerate_label
        self.delete_label = delete_label
        self.add_tooltip = add_tooltip
        self.continue_tooltip = continue_tooltip
        self.regenerate_tooltip = regenerate_tooltip
        self.delete_tooltip = delete_tooltip
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
        self.progress_label = None
        if self.show_progress:
            self.progress_label = QLabel(
                f"已生成 {self.current_count} / {self.total_count} {type_text}"
            )
            info_layout.addWidget(self.progress_label)

        layout.addWidget(info_widget, stretch=1)

        # 右侧: 操作按钮
        if self.editable:
            # 新增按钮（仅在show_add_button为True时显示）
            self.add_btn = None
            if self.show_add_button:
                self.add_btn = QPushButton(self.add_label)
                self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                tooltip = self.add_tooltip or f"手动新增一个{type_text}大纲"
                self.add_btn.setToolTip(tooltip)
                self.add_btn.clicked.connect(self.addOutlineClicked.emit)
                layout.addWidget(self.add_btn)

            # 继续生成按钮（仅在show_continue_button为True时显示）
            self.continue_btn = None
            if self.show_continue_button:
                self.continue_btn = QPushButton(self.continue_label)
                self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                tooltip = self.continue_tooltip or f"继续生成N个{type_text}"
                self.continue_btn.setToolTip(tooltip)
                self.continue_btn.clicked.connect(self.continueGenerateClicked.emit)
                layout.addWidget(self.continue_btn)

            # 重新生成按钮
            self.regenerate_btn = None
            if self.show_regenerate_button:
                self.regenerate_btn = QPushButton(self.regenerate_label)
                self.regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                tooltip = self.regenerate_tooltip or f"重新生成最新的N个{type_text}大纲"
                self.regenerate_btn.setToolTip(tooltip)
                self.regenerate_btn.clicked.connect(self.regenerateLatestClicked.emit)
                layout.addWidget(self.regenerate_btn)

            # 删除按钮
            self.delete_btn = None
            if self.show_delete_button:
                self.delete_btn = QPushButton(self.delete_label)
                self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                tooltip = self.delete_tooltip or f"删除最新的N个{type_text}大纲"
                self.delete_btn.setToolTip(tooltip)
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
        if self.progress_label:
            self.progress_label.setStyleSheet(
                f"background: transparent; border: none; font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};"
            )

        # 按钮样式
        if self.editable:
            # 新增按钮 - 次要按钮样式（如果存在）
            if self.add_btn:
                self.add_btn.setStyleSheet(ButtonStyles.secondary("SM"))

            # 继续生成按钮 - 主按钮样式（如果存在）
            if self.continue_btn:
                self.continue_btn.setStyleSheet(ButtonStyles.primary("SM"))

            # 重新生成按钮 - 警告样式
            if self.regenerate_btn:
                self.regenerate_btn.setStyleSheet(ButtonStyles.warning("SM"))

            # 删除按钮 - 危险样式
            if self.delete_btn:
                self.delete_btn.setStyleSheet(ButtonStyles.outline_danger("SM"))

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_progress(self, current_count: int, total_count: int):
        """更新进度信息"""
        self.current_count = current_count
        self.total_count = total_count
        type_text = "章节" if self.outline_type == "chapter" else "部分"
        if self.progress_label:
            self.progress_label.setText(f"已生成 {current_count} / {total_count} {type_text}")

        # 根据状态启用/禁用按钮
        if self.editable:
            # 如果已生成数量为0，禁用重新生成和删除按钮
            has_outlines = current_count > 0
            if self.regenerate_btn:
                self.regenerate_btn.setEnabled(has_outlines)
            if self.delete_btn:
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
            if self.regenerate_btn:
                self.regenerate_btn.setEnabled(enabled)
            if self.delete_btn:
                self.delete_btn.setEnabled(enabled)

    def set_add_visible(self, visible: bool):
        """设置新增按钮可见性"""
        if self.add_btn:
            self.add_btn.setVisible(visible)

    def set_continue_visible(self, visible: bool):
        """设置继续生成按钮可见性"""
        if self.continue_btn:
            self.continue_btn.setVisible(visible)

    def set_regenerate_visible(self, visible: bool):
        """设置重新生成按钮可见性"""
        if self.regenerate_btn:
            self.regenerate_btn.setVisible(visible)

    def set_delete_visible(self, visible: bool):
        """设置删除按钮可见性"""
        if self.delete_btn:
            self.delete_btn.setVisible(visible)

    def set_progress_visible(self, visible: bool):
        """设置进度信息可见性"""
        if self.progress_label:
            self.progress_label.setVisible(visible)

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
