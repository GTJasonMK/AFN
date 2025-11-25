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
import json


class WDEvaluationDetailModal(QDialog):
    """评审详情对话框 - 禅意风格

    对应Vue3组件：WDEvaluationDetailModal.vue

    UI规范：
    - 遮罩层：50%黑色半透明 + 背景模糊
    - 最大宽度：896px (max-w-4xl)
    - 最大高度：80vh
    - 特色图标：灰绿色圆形 + 铃铛图标
    - 内容：JSON解析显示评审结果或Markdown渲染
    """

    def __init__(self, evaluation_text='', parent=None):
        super().__init__(parent)
        self.evaluation_text = evaluation_text

        # 存储UI组件引用
        self.overlay = None
        self.dialog_widget = None
        self.header = None
        self.icon_label = None
        self.title_label = None
        self.close_btn = None
        self.scroll_area = None
        self.content_widget = None
        self.eval_label = None
        self.footer = None
        self.close_footer_btn = None
        self.structured_cards = []  # 存储结构化评审卡片

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 获取屏幕尺寸计算80vh
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

        # 遮罩层（50%黑色半透明）
        self.overlay = QWidget(self)
        self.overlay.mousePressEvent = lambda e: self.reject() if e.button() == Qt.MouseButton.LeftButton else None

        # 对话框容器
        container_layout = QVBoxLayout(self.overlay)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setContentsMargins(16, 16, 16, 16)

        # 对话框主体
        self.dialog_widget = QWidget()
        self.dialog_widget.setFixedWidth(dp(896))  # max-w-4xl = 56rem = 896px
        self.dialog_widget.setMaximumHeight(self.max_height)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 10)
        self.dialog_widget.setGraphicsEffect(shadow)

        dialog_layout = QVBoxLayout(self.dialog_widget)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)

        # 头部
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 16, 20, 16)  # 减小padding

        # 左侧：图标 + 标题
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)

        # 灰绿色圆形图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(dp(40), dp(40))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setText("◑")
        left_layout.addWidget(self.icon_label)

        self.title_label = QLabel("AI 评审详情")
        left_layout.addWidget(self.title_label)

        header_layout.addLayout(left_layout)
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

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 16, 20, 16)  # 减小from 24px
        content_layout.setSpacing(16)  # 减小from 24px

        # 解析评审内容
        parsed_eval = self.parseEvaluation()

        if parsed_eval:
            # JSON格式的评审结果
            self.renderStructuredEvaluation(content_layout, parsed_eval)
        else:
            # Markdown格式
            self.eval_label = QLabel(self.evaluation_text or '暂无评审内容')
            self.eval_label.setWordWrap(True)
            self.eval_label.setTextFormat(Qt.TextFormat.RichText)
            content_layout.addWidget(self.eval_label)

        content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        dialog_layout.addWidget(self.scroll_area)

        # 底部按钮
        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.addStretch()

        self.close_footer_btn = QPushButton("关闭")
        self.close_footer_btn.setMinimumHeight(32)  # 减小from 40px
        self.close_footer_btn.setMinimumWidth(64)   # 减小from 88px
        self.close_footer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_footer_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.close_footer_btn)

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

        if self.icon_label:
            self.icon_label.setStyleSheet(f"""
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border-radius: 20px;
                font-size: 24px;
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
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

        if self.eval_label:
            self.eval_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.6;
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

        if self.close_footer_btn:
            self.close_footer_btn.setStyleSheet(f"""
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

        # 更新结构化评审卡片样式
        for card_widget in self.structured_cards:
            if hasattr(card_widget, '_is_best_card') and card_widget._is_best_card:
                # 最佳选择卡片
                card_widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: {theme_manager.SUCCESS_BG};
                        border: 1px solid {theme_manager.INFO};
                        border-radius: {theme_manager.RADIUS_MD};
                        padding: 16px;
                    }}
                """)
            else:
                # 普通版本卡片
                card_widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: {theme_manager.BG_SECONDARY};
                        border: 1px solid {theme_manager.BORDER_DEFAULT};
                        border-radius: {theme_manager.RADIUS_SM};
                        padding: 16px;
                    }}
                """)

    def parseEvaluation(self):
        """解析评审JSON"""
        if not self.evaluation_text:
            return None
        try:
            data = json.loads(self.evaluation_text)
            if isinstance(data, str):
                data = json.loads(data)
            return data
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def renderStructuredEvaluation(self, layout, parsed_eval):
        """渲染结构化评审结果"""
        # 最佳选择卡片
        if 'best_choice' in parsed_eval:
            best_card = QFrame()
            best_card._is_best_card = True  # 标记为最佳选择卡片
            self.structured_cards.append(best_card)

            best_layout = QVBoxLayout(best_card)
            best_layout.setSpacing(8)

            best_title = QLabel(f"◐ 最佳选择：版本 {parsed_eval['best_choice']}")
            best_title.setStyleSheet(f"""
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.WARNING};
            """)
            best_layout.addWidget(best_title)

            if 'reason_for_choice' in parsed_eval:
                best_reason = QLabel(parsed_eval['reason_for_choice'])
                best_reason.setWordWrap(True)
                best_reason.setStyleSheet(f"""
                    font-size: {sp(14)}px;
                    color: {theme_manager.PRIMARY};
                """)
                best_layout.addWidget(best_reason)

            layout.addWidget(best_card)

        # 各版本评估
        if 'evaluation' in parsed_eval:
            for version_name, eval_result in parsed_eval['evaluation'].items():
                version_card = QFrame()
                self.structured_cards.append(version_card)

                version_layout = QVBoxLayout(version_card)
                version_layout.setSpacing(12)

                # 版本标题
                version_title = QLabel(f"版本 {version_name.replace('version', '')} 评估")
                version_title.setStyleSheet(f"""
                    font-size: {sp(18)}px;
                    font-weight: 700;
                    color: {theme_manager.TEXT_PRIMARY};
                """)
                version_layout.addWidget(version_title)

                # 综合评价
                if 'overall_review' in eval_result:
                    overall_widget = QWidget()
                    overall_layout = QVBoxLayout(overall_widget)
                    overall_layout.setContentsMargins(0, 0, 0, 0)
                    overall_layout.setSpacing(4)

                    overall_label = QLabel("综合评价:")
                    overall_label.setStyleSheet(f"""
                        font-weight: 600;
                        color: {theme_manager.TEXT_PRIMARY};
                        font-size: {sp(14)}px;
                    """)
                    overall_layout.addWidget(overall_label)

                    overall_content = QLabel(eval_result['overall_review'])
                    overall_content.setWordWrap(True)
                    overall_content.setStyleSheet(f"""
                        color: {theme_manager.TEXT_SECONDARY};
                        font-size: {sp(14)}px;
                    """)
                    overall_layout.addWidget(overall_content)

                    version_layout.addWidget(overall_widget)

                # 优点
                if 'pros' in eval_result and eval_result['pros']:
                    pros_widget = QWidget()
                    pros_layout = QVBoxLayout(pros_widget)
                    pros_layout.setContentsMargins(0, 0, 0, 0)
                    pros_layout.setSpacing(4)

                    pros_label = QLabel("优点:")
                    pros_label.setStyleSheet(f"""
                        font-weight: 600;
                        color: {theme_manager.TEXT_PRIMARY};
                        font-size: {sp(14)}px;
                    """)
                    pros_layout.addWidget(pros_label)

                    for pro in eval_result['pros']:
                        pro_item = QLabel(f"• {pro}")
                        pro_item.setWordWrap(True)
                        pro_item.setStyleSheet(f"""
                            color: {theme_manager.TEXT_SECONDARY};
                            font-size: {sp(14)}px;
                            padding-left: 16px;
                        """)
                        pros_layout.addWidget(pro_item)

                    version_layout.addWidget(pros_widget)

                # 缺点
                if 'cons' in eval_result and eval_result['cons']:
                    cons_widget = QWidget()
                    cons_layout = QVBoxLayout(cons_widget)
                    cons_layout.setContentsMargins(0, 0, 0, 0)
                    cons_layout.setSpacing(4)

                    cons_label = QLabel("缺点:")
                    cons_label.setStyleSheet(f"""
                        font-weight: 600;
                        color: {theme_manager.TEXT_PRIMARY};
                        font-size: {sp(14)}px;
                    """)
                    cons_layout.addWidget(cons_label)

                    for con in eval_result['cons']:
                        con_item = QLabel(f"• {con}")
                        con_item.setWordWrap(True)
                        con_item.setStyleSheet(f"""
                            color: {theme_manager.TEXT_SECONDARY};
                            font-size: {sp(14)}px;
                            padding-left: 16px;
                        """)
                        cons_layout.addWidget(con_item)

                    version_layout.addWidget(cons_widget)

                layout.addWidget(version_card)


