"""
蓝图优化对话框

允许用户输入优化指令来改进蓝图
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class RefineDialog(QDialog):
    """蓝图优化对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("优化蓝图")
        self.setMinimumSize(dp(550), dp(450))
        self.setModal(True)

        self.setupUI()
        self.applyTheme()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 标题和说明
        title = QLabel("优化蓝图")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        # 说明文字
        desc = QLabel(
            "请描述您想要优化的方向。系统会基于灵感对话的内容和当前蓝图进行针对性改进。\n"
            "例如：「让主角的性格更鲜明」「增加世界观的科技感」「让反派动机更合理」"
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 提示词示例卡片
        hints_card = QFrame()
        hints_card.setObjectName("hints_card")
        hints_layout = QVBoxLayout(hints_card)
        hints_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        hints_layout.setSpacing(dp(8))

        hints_title = QLabel("常用优化方向")
        hints_title.setObjectName("hints_title")
        hints_layout.addWidget(hints_title)

        hints = [
            "角色塑造：让角色更立体、动机更充分、关系更复杂",
            "世界观：丰富设定细节、增加独特元素、完善规则体系",
            "情节结构：增加冲突张力、优化节奏感、加强高潮设计",
            "风格基调：调整叙事语调、加强氛围营造、统一文风"
        ]

        for hint in hints:
            hint_label = QLabel(f"  {hint}")
            hint_label.setObjectName("hint_item")
            hints_layout.addWidget(hint_label)

        layout.addWidget(hints_card)

        # 输入框
        input_label = QLabel("您的优化指令")
        input_label.setObjectName("input_label")
        layout.addWidget(input_label)

        self.input_edit = QTextEdit()
        self.input_edit.setObjectName("input_edit")
        self.input_edit.setPlaceholderText(
            "请输入您希望如何优化蓝图...\n\n"
            "例如：\n"
            "- 主角的背景故事太单薄，希望增加一些童年经历来解释他的性格成因\n"
            "- 世界观中的魔法体系不够清晰，需要明确魔法的来源和限制\n"
            "- 反派角色缺乏深度，希望给他一个令人同情的过往"
        )
        self.input_edit.setMinimumHeight(dp(120))
        layout.addWidget(self.input_edit, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("开始优化")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    def applyTheme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            #dialog_title {{
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #dialog_desc {{
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.6;
            }}
            #hints_card {{
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
            }}
            #hints_title {{
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {theme_manager.PRIMARY};
            }}
            #hint_item {{
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #input_label {{
                font-size: {sp(14)}px;
                font-weight: 500;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #input_edit {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #input_edit:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
        """)

        # 按钮样式
        self.cancel_btn.setStyleSheet(ButtonStyles.secondary())
        self.confirm_btn.setStyleSheet(ButtonStyles.primary())

    def getValue(self) -> str:
        """获取用户输入的优化指令"""
        return self.input_edit.toPlainText().strip()
