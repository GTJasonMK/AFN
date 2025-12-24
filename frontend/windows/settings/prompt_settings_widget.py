"""
提示词管理界面 - 书籍风格

管理系统中所有LLM提示词，支持查看、编辑和恢复默认值。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors
from .prompt_edit_dialog import PromptEditDialog


class PromptSettingsWidget(QWidget):
    """提示词管理界面 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.prompts_data = []
        self._create_ui_structure()
        self._apply_styles()
        self.loadPrompts()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 顶部说明
        self.description_label = QLabel(
            "管理系统中的LLM提示词。您可以编辑提示词内容来自定义AI的行为，"
            "修改后的提示词会在系统更新时保留。"
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # 提示词列表
        self.prompt_list = QListWidget()
        self.prompt_list.setObjectName("prompt_list")
        self.prompt_list.setFrameShape(QFrame.Shape.NoFrame)
        self.prompt_list.setSpacing(dp(4))
        self.prompt_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.prompt_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.prompt_list, stretch=1)

        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))

        # 恢复全部按钮
        self.reset_all_btn = QPushButton("恢复全部默认值")
        self.reset_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        button_layout.addWidget(self.reset_all_btn)

        button_layout.addStretch()

        # 恢复默认值按钮（单个）
        self.reset_btn = QPushButton("恢复默认值")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset_single)
        button_layout.addWidget(self.reset_btn)

        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit)
        button_layout.addWidget(self.edit_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 说明文字样式
        self.description_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_tertiary};
                padding: {dp(8)}px 0;
                background: transparent;
            }}
        """)

        # 列表样式
        self.prompt_list.setStyleSheet(f"""
            QListWidget#prompt_list {{
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                outline: none;
            }}
            QListWidget#prompt_list::item {{
                background-color: transparent;
                color: {palette.text_primary};
                border-bottom: 1px solid {palette.border_color};
                padding: {dp(12)}px {dp(16)}px;
            }}
            QListWidget#prompt_list::item:last-child {{
                border-bottom: none;
            }}
            QListWidget#prompt_list::item:hover {{
                background-color: {palette.bg_secondary};
                color: {palette.text_primary};
            }}
            QListWidget#prompt_list::item:selected {{
                background-color: {palette.accent_light};
                color: {palette.text_primary};
            }}
        """)

        # 次要按钮样式
        secondary_btn_style = f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;
                font-size: {sp(14)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_primary};
            }}
            QPushButton:disabled {{
                color: {palette.text_tertiary};
                border-color: {palette.border_color};
            }}
        """
        self.reset_all_btn.setStyleSheet(secondary_btn_style)
        self.reset_btn.setStyleSheet(secondary_btn_style)

        # 主要按钮样式
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}
            QPushButton:pressed {{
                background-color: {palette.accent_light};
            }}
            QPushButton:disabled {{
                background-color: {palette.border_color};
                color: {palette.text_tertiary};
            }}
        """)

    @handle_errors("加载提示词")
    def loadPrompts(self):
        """加载提示词列表"""
        self.prompts_data = self.api_client.get_prompts()
        self._update_list()

    def _update_list(self):
        """更新列表显示"""
        self.prompt_list.clear()
        palette = theme_manager.get_book_palette()

        for prompt in self.prompts_data:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, dp(72)))
            item.setData(Qt.ItemDataRole.UserRole, prompt)

            # 构建显示文本
            title = prompt.get('title') or prompt.get('name', '未命名')
            description = prompt.get('description') or ''
            is_modified = prompt.get('is_modified', False)

            # 截断描述
            if description and len(description) > 60:
                description = description[:60] + '...'

            # 添加修改标记
            modified_mark = ' [已修改]' if is_modified else ''

            # 设置富文本
            display_text = f"{title}{modified_mark}\n{description}"
            item.setText(display_text)

            self.prompt_list.addItem(item)

    def _on_selection_changed(self, current, previous):
        """选择项变化时更新按钮状态"""
        has_selection = current is not None
        self.edit_btn.setEnabled(has_selection)
        self.reset_btn.setEnabled(has_selection)

    def _on_item_double_clicked(self, item):
        """双击项时打开编辑"""
        self._on_edit()

    def _on_edit(self):
        """编辑选中的提示词"""
        current_item = self.prompt_list.currentItem()
        if not current_item:
            return

        prompt_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not prompt_data:
            return

        dialog = PromptEditDialog(prompt_data, self)
        if dialog.exec():
            # 对话框确认后重新加载
            self.loadPrompts()

    def _on_reset_single(self):
        """恢复单个提示词默认值"""
        current_item = self.prompt_list.currentItem()
        if not current_item:
            return

        prompt_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not prompt_data:
            return

        name = prompt_data.get('name', '')
        title = prompt_data.get('title') or name

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认恢复",
            f"确定要将「{title}」恢复到默认值吗？\n您的修改将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._do_reset_single(name)

    @handle_errors("恢复默认值")
    def _do_reset_single(self, name: str):
        """执行单个恢复"""
        self.api_client.reset_prompt(name)
        MessageService.show_success(self, "已恢复默认值")
        self.loadPrompts()

    def _on_reset_all(self):
        """恢复全部提示词默认值"""
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认恢复全部",
            "确定要将所有提示词恢复到默认值吗？\n您的所有修改将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._do_reset_all()

    @handle_errors("恢复全部默认值")
    def _do_reset_all(self):
        """执行全部恢复"""
        result = self.api_client.reset_all_prompts()
        count = result.get('reset_count', 0)
        MessageService.show_success(self, f"已恢复 {count} 个提示词到默认值")
        self.loadPrompts()

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
