"""
编辑章节大纲对话框

对应Vue3组件：WDEditChapterModal.vue
"""

from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class WDEditChapterModal(QDialog):
    """编辑章节大纲对话框 - 禅意风格

    对应Vue3组件：WDEditChapterModal.vue

    UI规范：
    - 遮罩层：30%黑色半透明
    - 最大宽度：512px
    - 圆角：16px
    - 输入框：标题input + 摘要textarea(5行)
    - 按钮：取消(灰色) + 保存(灰绿色)
    """

    saved = pyqtSignal(dict)  # 保存时发射：{title, summary}

    def __init__(self, chapter_data=None, parent=None):
        super().__init__(parent)
        self.chapter_data = chapter_data or {}
        self.title_input = None
        self.summary_input = None
        self.dialog_widget = None
        self.cancel_btn = None
        self.save_btn = None
        self.close_btn = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setupUI()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def setupUI(self):
        """初始化UI"""
        # 主布局（包含遮罩效果）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 遮罩层（半透明）
        overlay = QWidget(self)
        overlay_color = theme_manager.OVERLAY_COLOR
        overlay.setStyleSheet(f"background-color: {overlay_color};")
        overlay.mousePressEvent = lambda e: self.reject() if e.button() == Qt.MouseButton.LeftButton else None

        # 对话框容器（居中）
        container_layout = QVBoxLayout(overlay)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 对话框主体
        self.dialog_widget = QWidget()
        self.dialog_widget.setFixedWidth(dp(512))  # max-w-lg = 32rem = 512px

        dialog_layout = QVBoxLayout(self.dialog_widget)
        dialog_layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))  # 减小from 32px
        dialog_layout.setSpacing(dp(16))  # 减小from 24px

        # 顶部标题和关闭按钮
        header_layout = QHBoxLayout()

        title_label = QLabel("编辑章节大纲")
        title_label.setStyleSheet(f"""
            font-size: {sp(24)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(dp(36), dp(36))
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self.close_btn)

        dialog_layout.addLayout(header_layout)

        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)  # 减小from 24px

        # 章节标题输入框
        title_label = QLabel("章节标题")
        title_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            font-weight: 500;
            color: {theme_manager.TEXT_SECONDARY};
            margin-bottom: 8px;
        """)
        form_layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请输入章节标题")
        self.title_input.setText(self.chapter_data.get('title', ''))
        form_layout.addWidget(self.title_input)

        # 章节摘要输入框
        summary_label = QLabel("章节摘要")
        summary_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            font-weight: 500;
            color: {theme_manager.TEXT_SECONDARY};
            margin-bottom: 8px;
        """)
        form_layout.addWidget(summary_label)

        self.summary_input = QTextEdit()
        self.summary_input.setPlaceholderText("请输入章节摘要")
        self.summary_input.setPlainText(self.chapter_data.get('summary', ''))
        self.summary_input.setMinimumHeight(120)  # 约5行
        form_layout.addWidget(self.summary_input)

        dialog_layout.addLayout(form_layout)

        # 底部按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(dp(32))  # 减小from 40px
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存更改")
        self.save_btn.setFixedHeight(dp(32))  # 减小from 40px
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.onSave)
        buttons_layout.addWidget(self.save_btn)

        dialog_layout.addLayout(buttons_layout)

        container_layout.addWidget(self.dialog_widget)
        main_layout.addWidget(overlay)

        # 应用主题
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        if self.dialog_widget:
            self.dialog_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_CARD};
                    border-radius: {theme_manager.RADIUS_LG};
                }}
            """)

        if self.close_btn:
            self.close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    border: none;
                    border-radius: {theme_manager.RADIUS_SM};
                    font-size: {sp(20)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.SUCCESS_BG};
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)

        if self.title_input:
            self.title_input.setStyleSheet(f"""
                QLineEdit {{
                    padding: 8px 16px;
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_SM};
                    font-size: {sp(15)}px;
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                QLineEdit:focus {{
                    border: 2px solid {theme_manager.PRIMARY};
                    outline: none;
                }}
            """)

        if self.summary_input:
            self.summary_input.setStyleSheet(f"""
                QTextEdit {{
                    padding: 8px 16px;
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_SM};
                    font-size: {sp(15)}px;
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                QTextEdit:focus {{
                    border: 2px solid {theme_manager.PRIMARY};
                    outline: none;
                }}
            """)

        if self.cancel_btn:
            self.cancel_btn.setStyleSheet(theme_manager.button_secondary())

        if self.save_btn:
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: 0 24px;
                    font-size: {theme_manager.FONT_SIZE_SM};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                }}
                QPushButton:disabled {{
                    background-color: {theme_manager.TEXT_DISABLED};
                    opacity: 0.5;
                }}
            """)

    def onSave(self):
        """保存更改"""
        title = self.title_input.text().strip()
        summary = self.summary_input.toPlainText().strip()

        # 检查是否有更改
        if (title != self.chapter_data.get('title', '') or
            summary != self.chapter_data.get('summary', '')):
            self.saved.emit({'title': title, 'summary': summary})
            self.accept()
        else:
            self.reject()
