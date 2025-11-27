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
from utils.dpi_utils import dp, sp


class WDGenerateOutlineModal(QDialog):
    """生成大纲对话框 - 禅意风格

    对应Vue3组件：WDGenerateOutlineModal.vue

    UI规范：
    - 遮罩层：灰色75%透明
    - 最大宽度：512px
    - 特色：灰绿色圆形图标 + 数字输入 + 快捷按钮(1/2/5/10章)
    - 按钮：生成(主要) + 取消(次要)
    """

    generated = pyqtSignal(int)  # 生成时发射章节数

    def __init__(self, parent=None):
        super().__init__(parent)

        # 存储UI组件引用
        self.overlay = None
        self.dialog_widget = None
        self.content_widget = None
        self.icon_label = None
        self.title_label = None
        self.desc_label = None
        self.num_input = None
        self.quick_buttons = []
        self.footer = None
        self.cancel_btn = None
        self.generate_btn = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
        self.dialog_widget.setFixedWidth(512)  # max-w-lg = 32rem

        dialog_layout = QVBoxLayout(self.dialog_widget)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)

        # 主内容区
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 24, 20, 20)

        # 顶部：图标 + 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # 灰绿色圆形图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(dp(48), dp(48))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setText("◐")
        header_layout.addWidget(self.icon_label)

        # 标题和描述
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        self.title_label = QLabel("生成后续大纲")
        title_layout.addWidget(self.title_label)

        self.desc_label = QLabel("请输入或选择要生成的后续章节数量。")
        self.desc_label.setWordWrap(True)
        title_layout.addWidget(self.desc_label)

        header_layout.addWidget(title_widget, stretch=1)
        content_layout.addLayout(header_layout)

        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(0, 24, 0, 0)
        form_layout.setSpacing(12)

        form_label = QLabel("生成数量")
        form_layout.addWidget(form_label)

        # 数字输入框
        self.num_input = QSpinBox()
        self.num_input.setRange(1, 20)
        self.num_input.setValue(5)
        form_layout.addWidget(self.num_input)

        # 快捷按钮（1/2/5/10章）
        quick_btns_layout = QHBoxLayout()
        quick_btns_layout.setSpacing(12)
        quick_btns_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for count in [1, 2, 5, 10]:
            btn = QPushButton(f"{count} 章")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=count: self.num_input.setValue(c))
            self.quick_buttons.append(btn)
            quick_btns_layout.addWidget(btn)

        form_layout.addLayout(quick_btns_layout)
        content_layout.addLayout(form_layout)

        dialog_layout.addWidget(self.content_widget)

        # 底部按钮区
        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)  # 统一边距
        footer_layout.setSpacing(12)
        footer_layout.addStretch()

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(dp(32))  # 减小from 44px
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_btn)

        # 生成按钮
        self.generate_btn = QPushButton("生成")
        self.generate_btn.setFixedHeight(dp(32))  # 减小from 44px
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self.onGenerate)
        footer_layout.addWidget(self.generate_btn)

        dialog_layout.addWidget(self.footer)

        container_layout.addWidget(self.dialog_widget)
        main_layout.addWidget(self.overlay)

        # 应用主题
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        # 使用书香风格字体
        serif_font = theme_manager.serif_font()
        # 获取当前是否为深色模式
        is_dark = theme_manager.is_dark_mode()

        if self.overlay:
            # 使用主题遮罩层颜色
            overlay_color = theme_manager.OVERLAY_COLOR
            self.overlay.setStyleSheet(f"background-color: {overlay_color};")

        if self.dialog_widget:
            self.dialog_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_TERTIARY};
                    border-radius: {theme_manager.RADIUS_SM};
                }}
            """)

        if self.content_widget:
            self.content_widget.setStyleSheet(f"background-color: {theme_manager.BG_CARD};")

        if self.icon_label:
            self.icon_label.setStyleSheet(f"""
                background-color: {theme_manager.SUCCESS_BG};
                color: {theme_manager.PRIMARY};
                border-radius: 24px;
                font-size: {sp(28)}px;
                font-weight: 700;
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(20)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        if self.desc_label:
            self.desc_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(16)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        if self.num_input:
            self.num_input.setStyleSheet(f"""
                QSpinBox {{
                    font-family: {serif_font};
                    padding: 12px 16px;
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_MD};
                    background-color: {theme_manager.BG_SECONDARY};
                    font-size: 18px;
                    color: {theme_manager.TEXT_PRIMARY};
                }}
                QSpinBox:focus {{
                    border: 1px solid {theme_manager.PRIMARY};
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_PRIMARY};
                    outline: none;
                }}
            """)

        for btn in self.quick_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {serif_font};
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_SECONDARY};
                    border: none;
                    border-radius: {theme_manager.RADIUS_LG};
                    padding: 8px 20px;
                    font-size: {sp(16)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.SUCCESS_BG};
                    color: {theme_manager.PRIMARY};
                }}
            """)

        if self.footer:
            self.footer.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme_manager.BG_SECONDARY};
                    border-bottom-left-radius: {theme_manager.RADIUS_SM};
                    border-bottom-right-radius: {theme_manager.RADIUS_SM};
                }}
            """)

        if self.cancel_btn:
            self.cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {serif_font};
                    background-color: {theme_manager.BG_TERTIARY};
                    color: {theme_manager.TEXT_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: 0 20px;
                    font-size: {sp(16)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.BG_SECONDARY};
                }}
            """)

        if self.generate_btn:
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {serif_font};
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: 0 20px;
                    font-size: {theme_manager.FONT_SIZE_MD};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                }}
            """)

    def onGenerate(self):
        """生成大纲"""
        count = self.num_input.value()
        if count > 0:
            self.generated.emit(count)
            self.accept()
