"""
对话输入框组件 - 现代化设计 (2025)

提供文本输入功能，带玻璃态背景和focus发光效果
Enter键换行，Ctrl+Enter发送
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects


class ConversationInput(ThemeAwareWidget):
    """对话输入框 - 现代化设计，玻璃态+发光效果"""

    messageSent = pyqtSignal(str)  # 用户发送的消息

    def __init__(self, parent=None):
        # 保存组件引用
        self.input_field = None
        self.char_count = None
        self.hint_label = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 输入框
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("描述你的创意，比如：我想写一个科幻小说...")
        self.input_field.setMaximumHeight(140)
        self.input_field.setMinimumHeight(100)
        self.input_field.textChanged.connect(self.updateCharCount)
        # 安装事件过滤器来捕获按键
        self.input_field.installEventFilter(self)
        layout.addWidget(self.input_field)

        # 底部：字数统计 + 快捷键提示
        bottom_layout = QHBoxLayout()

        self.char_count = QLabel("0 字")
        bottom_layout.addWidget(self.char_count)

        bottom_layout.addStretch()

        # 快捷键提示
        self.hint_label = QLabel("Enter 换行 • Ctrl+Enter 发送")
        bottom_layout.addWidget(self.hint_label)

        layout.addLayout(bottom_layout)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 输入框 - 玻璃态背景 + focus发光
        if self.input_field:
            # 使用玻璃态背景
            glass_bg = theme_manager.current_theme.GLASS_BG

            self.input_field.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {glass_bg};
                    border: 2px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 16px;
                    font-size: {theme_manager.FONT_SIZE_BASE};
                    color: {theme_manager.TEXT_PRIMARY};
                    line-height: {theme_manager.LINE_HEIGHT_RELAXED};
                }}
                QTextEdit:focus {{
                    border-color: {theme_manager.PRIMARY};
                    background-color: {theme_manager.BG_CARD};
                    /* QSS不支持box-shadow，但我们可以通过边框颜色暗示focus状态 */
                }}
                QTextEdit:hover {{
                    border-color: {theme_manager.PRIMARY_LIGHT};
                }}
            """)

        # 字数统计
        if self.char_count:
            self.char_count.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_SECONDARY};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            """)

        # 快捷键提示
        if self.hint_label:
            self.hint_label.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.TEXT_TERTIARY};
                font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
            """)

    def eventFilter(self, obj, event):
        """事件过滤器，捕获快捷键"""
        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            key_event = event

            # Ctrl+Enter 发送
            if key_event.key() == Qt.Key.Key_Return and (key_event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.sendMessage()
                return True  # 阻止默认行为

            # Enter 换行（默认行为，不需要特殊处理）

        return super().eventFilter(obj, event)

    def updateCharCount(self):
        """更新字数统计"""
        if self.input_field and self.char_count:
            text = self.input_field.toPlainText()
            count = len(text.strip())
            self.char_count.setText(f"{count} 字")

            # 字数过多时变色提示
            if count > 500:
                self.char_count.setStyleSheet(f"""
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {theme_manager.WARNING};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                """)
            else:
                self._apply_theme()  # 恢复默认样式

    def sendMessage(self):
        """发送消息"""
        if self.input_field:
            message = self.input_field.toPlainText().strip()
            if message:
                self.messageSent.emit(message)
                self.input_field.clear()

    def setEnabled(self, enabled):
        """设置启用状态"""
        super().setEnabled(enabled)
        if self.input_field:
            self.input_field.setEnabled(enabled)

    def setPlaceholder(self, text):
        """设置输入框占位符文本"""
        if self.input_field:
            self.input_field.setPlaceholderText(text)