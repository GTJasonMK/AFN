"""
修改建议卡片组件

显示单个修改建议，支持应用、忽略操作。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class SuggestionCard(ThemeAwareFrame):
    """修改建议卡片"""

    applied = pyqtSignal(dict)   # 应用建议信号，传递建议数据
    ignored = pyqtSignal(dict)   # 忽略建议信号，传递建议数据
    detail_requested = pyqtSignal(dict)  # 查看详情信号

    def __init__(self, suggestion: dict, parent=None):
        """
        初始化建议卡片

        Args:
            suggestion: 建议数据，包含：
                - paragraph_index: 段落索引
                - original_text: 原文
                - suggested_text: 建议修改后的文本
                - reason: 修改理由
                - category: 建议类别
                - priority: 优先级 (high/medium/low)
            parent: 父组件
        """
        self.suggestion = suggestion
        self.is_applied = False
        self.is_ignored = False

        # UI组件
        self.priority_label = None
        self.category_label = None
        self.paragraph_label = None
        self.original_label = None
        self.original_text = None
        self.suggested_label = None
        self.suggested_text = None
        self.reason_label = None
        self.apply_btn = None
        self.ignore_btn = None
        self.status_label = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 头部：优先级、类别、段落号
        header = QHBoxLayout()

        self.priority_label = QLabel()
        header.addWidget(self.priority_label)

        self.category_label = QLabel()
        header.addWidget(self.category_label)

        header.addStretch()

        self.paragraph_label = QLabel()
        header.addWidget(self.paragraph_label)

        layout.addLayout(header)

        # 原文
        self.original_label = QLabel("原文:")
        layout.addWidget(self.original_label)

        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.suggestion.get("original_text", ""))
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(dp(60))
        layout.addWidget(self.original_text)

        # 建议
        self.suggested_label = QLabel("建议修改为:")
        layout.addWidget(self.suggested_label)

        self.suggested_text = QTextEdit()
        self.suggested_text.setPlainText(self.suggestion.get("suggested_text", ""))
        self.suggested_text.setReadOnly(True)
        self.suggested_text.setMaximumHeight(dp(80))
        layout.addWidget(self.suggested_text)

        # 理由
        self.reason_label = QLabel()
        reason = self.suggestion.get("reason", "")
        self.reason_label.setText(f"理由: {reason}")
        self.reason_label.setWordWrap(True)
        layout.addWidget(self.reason_label)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.ignore_btn = QPushButton("忽略")
        self.ignore_btn.setFixedWidth(dp(70))
        self.ignore_btn.clicked.connect(self._on_ignore)
        btn_layout.addWidget(self.ignore_btn)

        self.apply_btn = QPushButton("应用")
        self.apply_btn.setFixedWidth(dp(70))
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)

        # 状态标签（初始隐藏）
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()
        priority = self.suggestion.get("priority", "medium")
        category = self.suggestion.get("category", "coherence")
        paragraph_index = self.suggestion.get("paragraph_index", 0)

        # 优先级颜色
        priority_colors = {
            "high": theme_manager.ERROR,
            "medium": theme_manager.WARNING,
            "low": theme_manager.INFO,
        }
        priority_names = {
            "high": "高优先级",
            "medium": "中优先级",
            "low": "低优先级",
        }
        priority_color = priority_colors.get(priority, theme_manager.TEXT_SECONDARY)
        priority_name = priority_names.get(priority, priority)

        # 类别名称
        category_names = {
            "coherence": "逻辑连贯",
            "character": "角色一致",
            "foreshadow": "伏笔呼应",
            "timeline": "时间线",
            "style": "风格",
            "scene": "场景",
        }
        category_name = category_names.get(category, category)

        # 设置优先级标签
        if self.priority_label:
            self.priority_label.setText(f"[{priority_name}]")
            self.priority_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: bold;
                color: {priority_color};
                padding: {dp(2)}px {dp(6)}px;
                background-color: {priority_color}20;
                border-radius: {dp(4)}px;
            """)

        # 设置类别标签
        if self.category_label:
            self.category_label.setText(category_name)
            self.category_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding: {dp(2)}px {dp(6)}px;
                background-color: {theme_manager.BG_SECONDARY};
                border-radius: {dp(4)}px;
            """)

        # 设置段落标签
        if self.paragraph_label:
            self.paragraph_label.setText(f"第 {paragraph_index + 1} 段")
            self.paragraph_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        # 设置标签样式
        label_style = f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_SECONDARY};
        """
        if self.original_label:
            self.original_label.setStyleSheet(label_style)
        if self.suggested_label:
            self.suggested_label.setStyleSheet(label_style)

        # 设置文本框样式
        text_style = f"""
            QTextEdit {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px;
            }}
        """
        if self.original_text:
            self.original_text.setStyleSheet(text_style)
        if self.suggested_text:
            self.suggested_text.setStyleSheet(text_style)

        # 设置理由标签
        if self.reason_label:
            self.reason_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                font-style: italic;
            """)

        # 设置按钮样式
        if self.ignore_btn:
            self.ignore_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                    background-color: transparent;
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.BG_CARD_HOVER};
                }}
                QPushButton:disabled {{
                    color: {theme_manager.TEXT_DISABLED};
                    border-color: {theme_manager.BORDER_LIGHT};
                }}
            """)

        if self.apply_btn:
            self.apply_btn.setStyleSheet(ButtonStyles.primary())

        # 设置状态标签
        if self.status_label:
            self.status_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                padding: {dp(8)}px;
            """)

        # 设置卡片边框颜色
        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        border_color = theme_manager.BORDER_DEFAULT
        if priority == "high":
            border_color = theme_manager.ERROR
        elif priority == "medium":
            border_color = theme_manager.WARNING

        self.setStyleSheet(f"""
            background-color: {theme_manager.BG_CARD};
            border: 1px solid {border_color};
            border-radius: {dp(8)}px;
        """)

    def _on_apply(self):
        """应用建议"""
        if self.is_applied or self.is_ignored:
            return

        self.is_applied = True
        self._update_status("已应用", theme_manager.SUCCESS)
        self.applied.emit(self.suggestion)

    def _on_ignore(self):
        """忽略建议"""
        if self.is_applied or self.is_ignored:
            return

        self.is_ignored = True
        self._update_status("已忽略", theme_manager.TEXT_SECONDARY)
        self.ignored.emit(self.suggestion)

    def _update_status(self, status_text: str, color: str):
        """更新状态显示"""
        # 禁用按钮
        if self.apply_btn:
            self.apply_btn.setEnabled(False)
        if self.ignore_btn:
            self.ignore_btn.setEnabled(False)

        # 显示状态
        if self.status_label:
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"""
                font-family: {theme_manager.ui_font()};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {color};
                padding: {dp(8)}px;
            """)
            self.status_label.setVisible(True)

        # 降低透明度
        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        self.setStyleSheet(f"""
            background-color: {theme_manager.BG_CARD};
            border: 1px solid {theme_manager.BORDER_LIGHT};
            border-radius: {dp(8)}px;
            opacity: 0.6;
        """)

    def get_suggestion(self) -> dict:
        """获取建议数据"""
        return self.suggestion

    def is_high_priority(self) -> bool:
        """是否为高优先级"""
        return self.suggestion.get("priority") == "high"
