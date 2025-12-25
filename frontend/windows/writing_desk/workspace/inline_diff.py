"""
写作台主工作区 - 内联差异 Mixin

包含应用修改建议、显示内联diff、确认/撤销修改等功能。
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class InlineDiffMixin:
    """内联差异功能的 Mixin"""

    def applySuggestion(self, suggestion: dict):
        """
        应用修改建议 - 在正文中显示内联diff

        显示方式：
        - 原文：红色背景 + 删除线
        - 新文本：绿色背景
        - 浮动确认按钮

        Args:
            suggestion: 建议数据，包含 original_text, suggested_text, paragraph_index
        """
        if not self.content_text:
            return

        original_text = suggestion.get("original_text", "")
        suggested_text = suggestion.get("suggested_text", "")

        if not original_text or not suggested_text:
            return

        # 获取当前正文内容
        current_content = self.content_text.toPlainText()

        # 查找原文位置
        start_pos = current_content.find(original_text)
        if start_pos == -1:
            # 如果找不到完全匹配，尝试模糊匹配（去除首尾空白）
            trimmed_original = original_text.strip()
            start_pos = current_content.find(trimmed_original)
            if start_pos == -1:
                return
            original_text = trimmed_original

        # 切换到正文标签页
        if self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

        # 显示内联diff
        self._showInlineDiff(start_pos, original_text, suggested_text)

    def _showInlineDiff(self, start_pos: int, original_text: str, suggested_text: str):
        """
        在正文中显示内联diff

        Args:
            start_pos: 原文开始位置
            original_text: 原文
            suggested_text: 新文本
        """
        if not self.content_text:
            return

        # 获取文本光标
        cursor = self.content_text.textCursor()

        # 1. 先选中原文并设置删除线+红色背景格式
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(original_text), QTextCursor.MoveMode.KeepAnchor)

        delete_format = QTextCharFormat()
        delete_format.setBackground(QColor(theme_manager.ERROR_BG))  # 错误背景色
        delete_format.setForeground(QColor(theme_manager.ERROR_DARK))  # 深红色文字
        delete_format.setFontStrikeOut(True)  # 删除线

        cursor.mergeCharFormat(delete_format)

        # 2. 在原文后插入新文本（绿色高亮）
        cursor.setPosition(start_pos + len(original_text))

        add_format = QTextCharFormat()
        add_format.setBackground(QColor(theme_manager.SUCCESS_BG))  # 成功背景色
        add_format.setForeground(QColor(theme_manager.SUCCESS_DARK))  # 深绿色文字
        add_format.setFontStrikeOut(False)

        cursor.insertText(suggested_text, add_format)

        # 3. 保存待确认的修改信息
        pending_change = {
            "start_pos": start_pos,
            "original_text": original_text,
            "original_length": len(original_text),
            "suggested_text": suggested_text,
            "suggested_length": len(suggested_text),
        }

        if not hasattr(self, '_pending_changes'):
            self._pending_changes = []
        self._pending_changes.append(pending_change)

        # 4. 显示确认面板
        self._showConfirmPanel(pending_change, len(self._pending_changes) - 1)

        # 5. 跳转到修改位置 - 将光标定位到修改开始处并确保可见
        cursor.setPosition(start_pos)
        self.content_text.setTextCursor(cursor)
        self.content_text.ensureCursorVisible()

        # 额外滚动调整，确保修改内容在视口中间位置
        self._scrollToPosition(start_pos)

    def _scrollToPosition(self, position: int):
        """
        滚动到指定位置，使其在视口中间

        Args:
            position: 文本位置
        """
        if not self.content_text:
            return

        # 获取位置对应的矩形区域
        cursor = self.content_text.textCursor()
        cursor.setPosition(position)
        self.content_text.setTextCursor(cursor)

        # 获取光标位置的矩形
        cursor_rect = self.content_text.cursorRect(cursor)

        # 获取视口高度
        viewport_height = self.content_text.viewport().height()

        # 计算目标滚动位置（使修改内容在视口中上部）
        scrollbar = self.content_text.verticalScrollBar()
        target_scroll = scrollbar.value() + cursor_rect.top() - int(viewport_height * 0.3)

        # 确保不超出范围
        target_scroll = max(0, min(target_scroll, scrollbar.maximum()))

        scrollbar.setValue(target_scroll)

    def _showConfirmPanel(self, change: dict, change_index: int):
        """
        显示确认修改的浮动面板

        Args:
            change: 待确认的修改信息
            change_index: 修改索引
        """
        # 如果已有确认面板，先移除
        if hasattr(self, '_confirm_panel') and self._confirm_panel:
            self._confirm_panel.deleteLater()

        # 创建确认面板
        self._confirm_panel = QFrame(self.content_text)
        self._confirm_panel.setObjectName("confirm_panel")
        self._confirm_panel.setStyleSheet(f"""
            QFrame#confirm_panel {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
            }}
        """)

        layout = QHBoxLayout(self._confirm_panel)
        layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        layout.setSpacing(dp(8))

        # 提示文字
        hint_label = QLabel("修改预览")
        hint_label.setStyleSheet(f"""
            font-family: {theme_manager.ui_font()};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(hint_label)

        layout.addStretch()

        # 撤销按钮
        cancel_btn = QPushButton("撤销")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {theme_manager.ui_font()};
                font-size: {sp(12)}px;
                color: {theme_manager.ERROR};
                background-color: transparent;
                border: 1px solid {theme_manager.ERROR};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR}20;
            }}
        """)
        cancel_btn.clicked.connect(lambda: self._revertChange(change_index))
        layout.addWidget(cancel_btn)

        # 确认按钮
        confirm_btn = QPushButton("确认修改")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {theme_manager.ui_font()};
                font-size: {sp(12)}px;
                color: {theme_manager.BUTTON_TEXT};
                background-color: {theme_manager.SUCCESS};
                border: 1px solid {theme_manager.SUCCESS};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS}dd;
            }}
        """)
        confirm_btn.clicked.connect(lambda: self._confirmChange(change_index))
        layout.addWidget(confirm_btn)

        # 定位面板到编辑器顶部
        self._confirm_panel.setFixedWidth(dp(280))
        self._confirm_panel.move(
            self.content_text.width() - dp(290),
            dp(10)
        )
        self._confirm_panel.show()

    def _confirmChange(self, change_index: int):
        """
        确认修改 - 删除原文，保留新文本，移除高亮

        Args:
            change_index: 修改索引
        """
        if not hasattr(self, '_pending_changes') or change_index >= len(self._pending_changes):
            return

        change = self._pending_changes[change_index]
        start_pos = change["start_pos"]
        original_length = change["original_length"]
        suggested_length = change["suggested_length"]

        cursor = self.content_text.textCursor()

        # 1. 删除原文（带删除线的部分）
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + original_length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # 2. 移除新文本的高亮格式
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + suggested_length, QTextCursor.MoveMode.KeepAnchor)

        normal_format = QTextCharFormat()
        normal_format.setBackground(QColor("transparent"))
        normal_format.setForeground(QColor(theme_manager.TEXT_PRIMARY))
        normal_format.setFontStrikeOut(False)

        cursor.setCharFormat(normal_format)

        # 3. 清理
        self._pending_changes.pop(change_index)
        self._hideConfirmPanel()

        # 4. 更新后续修改的位置偏移
        offset = original_length  # 删除了原文，位置需要调整
        for i, c in enumerate(self._pending_changes):
            if c["start_pos"] > start_pos:
                c["start_pos"] -= offset

    def _revertChange(self, change_index: int):
        """
        撤销修改 - 删除新文本，恢复原文格式

        Args:
            change_index: 修改索引
        """
        if not hasattr(self, '_pending_changes') or change_index >= len(self._pending_changes):
            return

        change = self._pending_changes[change_index]
        start_pos = change["start_pos"]
        original_length = change["original_length"]
        suggested_length = change["suggested_length"]

        cursor = self.content_text.textCursor()

        # 1. 删除新文本（在原文之后）
        cursor.setPosition(start_pos + original_length)
        cursor.setPosition(start_pos + original_length + suggested_length, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # 2. 恢复原文格式（移除删除线和红色背景）
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + original_length, QTextCursor.MoveMode.KeepAnchor)

        normal_format = QTextCharFormat()
        normal_format.setBackground(QColor("transparent"))
        normal_format.setForeground(QColor(theme_manager.TEXT_PRIMARY))
        normal_format.setFontStrikeOut(False)

        cursor.setCharFormat(normal_format)

        # 3. 清理
        self._pending_changes.pop(change_index)
        self._hideConfirmPanel()

        # 4. 更新后续修改的位置偏移
        offset = suggested_length  # 删除了新文本，位置需要调整
        for i, c in enumerate(self._pending_changes):
            if c["start_pos"] > start_pos:
                c["start_pos"] -= offset

    def _hideConfirmPanel(self):
        """隐藏确认面板"""
        if hasattr(self, '_confirm_panel') and self._confirm_panel:
            self._confirm_panel.deleteLater()
            self._confirm_panel = None

        # 如果还有其他待确认的修改，显示下一个
        if hasattr(self, '_pending_changes') and self._pending_changes:
            self._showConfirmPanel(self._pending_changes[0], 0)
