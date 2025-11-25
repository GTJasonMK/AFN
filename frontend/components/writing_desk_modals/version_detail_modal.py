"""
写作台精美Modal对话框组件（禅意风格）

完全照抄Vue3的UI设计规范，替代系统原生对话框
对应Vue3组件：
- WDEditChapterModal.vue
- WDEvaluationDetailModal.vue
- WDVersionDetailModal.vue
- WDGenerateOutlineModal.vue
"""

from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from themes.theme_manager import theme_manager
from utils.dpi_utils import dpi_helper, dp, sp, responsive
import json


class WDVersionDetailModal(QDialog):
    """版本详情对话框 - 禅意风格

    对应Vue3组件：WDVersionDetailModal.vue

    UI规范：
    - 遮罩层：50%黑色半透明 + 背景模糊
    - 最大宽度：896px
    - 最大高度：80vh
    - 头部信息：版本号、风格、字数统计
    - 内容：whitespace-pre-wrap显示正文
    - 底部：当前版本标记 + 选择按钮
    """

    versionSelected = pyqtSignal()  # 选择版本时发射

    def __init__(self, version_index=0, version_data=None, is_current=False, parent=None):
        super().__init__(parent)
        self.version_index = version_index
        self.version_data = version_data or {}
        self.is_current = is_current

        # 存储UI组件引用
        self.overlay = None
        self.dialog_widget = None
        self.header = None
        self.title_label = None
        self.meta_label = None
        self.close_btn = None
        self.scroll_area = None
        self.content_label = None
        self.footer = None
        self.current_badge = None
        self.placeholder_label = None
        self.close_footer_btn = None
        self.select_btn = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        self.max_height = int(screen.height() * 0.8)

        self.setupUI()

        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def setupUI(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 遮罩层
        self.overlay = QWidget(self)
        self.overlay.mousePressEvent = lambda e: self.reject() if e.button() == Qt.MouseButton.LeftButton else None

        # 对话框容器
        container_layout = QVBoxLayout(self.overlay)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setContentsMargins(16, 16, 16, 16)

        # 对话框主体
        self.dialog_widget = QWidget()
        self.dialog_widget.setFixedWidth(dp(896))
        self.dialog_widget.setMaximumHeight(self.max_height)

        dialog_layout = QVBoxLayout(self.dialog_widget)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)

        # 头部
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 16, 20, 16)  # 减小from 24px

        # 左侧：标题和元信息
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.title_label = QLabel("版本详情")
        left_layout.addWidget(self.title_label)

        # 元信息（版本号、风格、字数）
        content = self.cleanVersionContent(self.version_data.get('content', ''))
        word_count = len(content)
        style = self.version_data.get('style', '标准')

        meta_text = f"版本 {self.version_index + 1}  •  {style}风格  •  约 {round(word_count / 100) * 100} 字"
        self.meta_label = QLabel(meta_text)
        left_layout.addWidget(self.meta_label)

        header_layout.addWidget(left_widget)
        header_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(dp(36), dp(36))
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self.close_btn)

        dialog_layout.addWidget(self.header)

        # 内容区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 16, 20, 16)  # 减小from 24px

        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        content_layout.addWidget(self.content_label)
        content_layout.addStretch()

        self.scroll_area.setWidget(content_widget)
        dialog_layout.addWidget(self.scroll_area)

        # 底部
        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)

        # 当前版本标记
        if self.is_current:
            self.current_badge = QLabel("✓ 当前选中版本")
            footer_layout.addWidget(self.current_badge)
        else:
            self.placeholder_label = QLabel("未选中版本")
            footer_layout.addWidget(self.placeholder_label)

        footer_layout.addStretch()

        # 右侧按钮
        self.close_footer_btn = QPushButton("关闭")
        self.close_footer_btn.setFixedHeight(dp(32))  # 减小from 36px
        self.close_footer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_footer_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.close_footer_btn)

        # 选择按钮（仅未选中时显示）
        if not self.is_current:
            self.select_btn = QPushButton("选择此版本")
            self.select_btn.setFixedHeight(dp(32))  # 减小from 36px
            self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.select_btn.clicked.connect(self.onSelectVersion)
            footer_layout.addWidget(self.select_btn)

        dialog_layout.addWidget(self.footer)

        container_layout.addWidget(self.dialog_widget)
        main_layout.addWidget(self.overlay)

        # 应用主题
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        # 获取当前是否为深色模式
        is_dark = theme_manager.is_dark_mode()

        if self.overlay:
            # 使用主题遮罩层颜色
            overlay_color = theme_manager.OVERLAY_COLOR
            self.overlay.setStyleSheet(f"background-color: {overlay_color};")

        if self.dialog_widget:
            self.dialog_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_CARD};
                    border-radius: {theme_manager.RADIUS_LG};
                }}
            """)

        if self.header:
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_TERTIARY};
                    border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
                    border-top-left-radius: {theme_manager.RADIUS_LG};
                    border-top-right-radius: {theme_manager.RADIUS_LG};
                }}
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if self.meta_label:
            self.meta_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
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

        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {theme_manager.BG_TERTIARY};
                    border: none;
                }}
                {theme_manager.scrollbar()}
            """)

        if self.content_label:
            self.content_label.setStyleSheet(f"""
                font-size: 15px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.7;
            """)

        if self.footer:
            self.footer.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_SECONDARY};
                    border-top: 1px solid {theme_manager.BORDER_LIGHT};
                    border-bottom-left-radius: {theme_manager.RADIUS_LG};
                    border-bottom-right-radius: {theme_manager.RADIUS_LG};
                }}
            """)

        if self.current_badge:
            self.current_badge.setStyleSheet(f"""
                background-color: {theme_manager.SUCCESS_BG};
                color: {theme_manager.SUCCESS};
                padding: 4px 12px;
                border-radius: {theme_manager.RADIUS_SM};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
            """)

        if self.placeholder_label:
            self.placeholder_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(14)}px;
            """)

        if self.close_footer_btn:
            self.close_footer_btn.setStyleSheet(theme_manager.button_ghost())

        if self.select_btn:
            self.select_btn.setStyleSheet(f"""
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
            """)

    def cleanVersionContent(self, content):
        """清理版本内容"""
        if not content:
            return ''

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'content' in parsed:
                content = parsed['content']
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # 清理转义字符
        cleaned = content.strip('"')
        cleaned = cleaned.replace('\\n', '\n')
        cleaned = cleaned.replace('\\"', '"')
        cleaned = cleaned.replace('\\t', '\t')
        cleaned = cleaned.replace('\\\\', '\\')

        return cleaned

    def onSelectVersion(self):
        """选择版本"""
        self.versionSelected.emit()
        self.accept()


