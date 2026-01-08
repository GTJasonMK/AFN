"""
修改建议卡片组件

显示单个修改建议，支持应用、忽略操作。
增强功能：差异对比显示、折叠/展开、状态动画。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class SuggestionCard(ThemeAwareFrame):
    """修改建议卡片 - 增强版

    显示单个修改建议，包含原文和建议修改后的文本对比。
    支持应用、忽略操作，以及差异对比显示。
    """

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
        self.is_expanded = True  # 默认展开

        # UI组件
        self.priority_label = None
        self.category_label = None
        self.paragraph_label = None
        self.toggle_btn = None
        self.content_widget = None
        self.original_label = None
        self.original_text = None
        self.suggested_label = None
        self.suggested_text = None
        self.diff_label = None
        self.diff_view = None
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

        # 头部：优先级、类别、段落号、折叠按钮
        header = QHBoxLayout()

        self.priority_label = QLabel()
        header.addWidget(self.priority_label)

        self.category_label = QLabel()
        header.addWidget(self.category_label)

        header.addStretch()

        self.paragraph_label = QLabel()
        header.addWidget(self.paragraph_label)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(dp(24), dp(24))
        self.toggle_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self.toggle_btn)

        layout.addLayout(header)

        # 内容区域（可折叠）
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(dp(8))

        # 差异对比视图（默认显示）
        self.diff_label = QLabel("变更对比:")
        content_layout.addWidget(self.diff_label)

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setMaximumHeight(dp(100))
        content_layout.addWidget(self.diff_view)

        # 原文（可选查看）
        orig_header = QHBoxLayout()
        self.original_label = QLabel("原文:")
        orig_header.addWidget(self.original_label)
        orig_header.addStretch()
        content_layout.addLayout(orig_header)

        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.suggestion.get("original_text", ""))
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(dp(50))
        self.original_text.setVisible(False)  # 默认隐藏
        content_layout.addWidget(self.original_text)

        # 建议（可选查看）
        sugg_header = QHBoxLayout()
        self.suggested_label = QLabel("建议修改为:")
        sugg_header.addWidget(self.suggested_label)
        sugg_header.addStretch()
        content_layout.addLayout(sugg_header)

        self.suggested_text = QTextEdit()
        self.suggested_text.setPlainText(self.suggestion.get("suggested_text", ""))
        self.suggested_text.setReadOnly(True)
        self.suggested_text.setMaximumHeight(dp(50))
        self.suggested_text.setVisible(False)  # 默认隐藏
        content_layout.addWidget(self.suggested_text)

        # 理由
        self.reason_label = QLabel()
        reason = self.suggestion.get("reason", "")
        self.reason_label.setText(f"理由: {reason}")
        self.reason_label.setWordWrap(True)
        content_layout.addWidget(self.reason_label)

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

        content_layout.addLayout(btn_layout)

        layout.addWidget(self.content_widget)

        # 状态标签（初始隐藏）
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # 填充差异视图
        self._populate_diff_view()

    def _populate_diff_view(self):
        """填充差异对比视图"""
        original = self.suggestion.get("original_text", "")
        suggested = self.suggestion.get("suggested_text", "")

        if not self.diff_view:
            return

        self.diff_view.clear()
        cursor = self.diff_view.textCursor()

        # 简化的差异显示
        # 删除的内容用删除线红色显示，新增的内容用绿色显示
        del_format = QTextCharFormat()
        del_format.setForeground(QColor(theme_manager.ERROR))
        del_format.setFontStrikeOut(True)

        add_format = QTextCharFormat()
        add_format.setForeground(QColor(theme_manager.SUCCESS))
        add_format.setFontWeight(600)

        normal_format = QTextCharFormat()
        normal_format.setForeground(QColor(theme_manager.TEXT_PRIMARY))

        # 使用简单的单词级别差异
        original_words = original.split()
        suggested_words = suggested.split()

        # 找出差异（简化版本）
        i = 0
        j = 0
        while i < len(original_words) or j < len(suggested_words):
            if i < len(original_words) and j < len(suggested_words):
                if original_words[i] == suggested_words[j]:
                    cursor.insertText(original_words[i] + " ", normal_format)
                    i += 1
                    j += 1
                else:
                    # 寻找匹配
                    found_in_suggested = False
                    for k in range(j, min(j + 5, len(suggested_words))):
                        if original_words[i] == suggested_words[k]:
                            # 在建议中找到了，说明中间有插入
                            for m in range(j, k):
                                cursor.insertText(suggested_words[m] + " ", add_format)
                            j = k
                            found_in_suggested = True
                            break

                    if not found_in_suggested:
                        # 原文中的词被删除或替换
                        cursor.insertText(original_words[i] + " ", del_format)
                        i += 1
            elif i < len(original_words):
                # 剩余原文被删除
                cursor.insertText(original_words[i] + " ", del_format)
                i += 1
            else:
                # 新增内容
                cursor.insertText(suggested_words[j] + " ", add_format)
                j += 1

    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self.is_expanded = not self.is_expanded
        if self.content_widget:
            self.content_widget.setVisible(self.is_expanded)
        if self.toggle_btn:
            self.toggle_btn.setText("-" if self.is_expanded else "+")

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

        # 优先级背景色映射 - 使用主题色彩系统
        priority_bg_map = {
            "high": theme_manager.ERROR_BG if hasattr(theme_manager, 'ERROR_BG') else theme_manager.BG_TERTIARY,
            "medium": theme_manager.WARNING_BG if hasattr(theme_manager, 'WARNING_BG') else theme_manager.BG_TERTIARY,
            "low": theme_manager.INFO_BG if hasattr(theme_manager, 'INFO_BG') else theme_manager.BG_TERTIARY,
        }
        priority_bg = priority_bg_map.get(priority, theme_manager.BG_TERTIARY)

        # 设置优先级标签
        if self.priority_label:
            self.priority_label.setText(f"[{priority_name}]")
            self.priority_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: bold;
                color: {priority_color};
                padding: {dp(2)}px {dp(6)}px;
                background-color: {priority_bg};
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

        # 设置折叠按钮样式
        if self.toggle_btn:
            self.toggle_btn.setText("-" if self.is_expanded else "+")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    font-weight: bold;
                    color: {theme_manager.TEXT_SECONDARY};
                    background-color: transparent;
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {dp(4)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.BG_CARD_HOVER};
                }}
            """)

        # 设置差异视图标签和内容样式
        if self.diff_label:
            self.diff_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        if self.diff_view:
            self.diff_view.setStyleSheet(f"""
                QTextEdit {{
                    font-family: {ui_font};
                    font-size: {sp(13)}px;
                    color: {theme_manager.TEXT_PRIMARY};
                    background-color: {theme_manager.BG_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px;
                }}
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
