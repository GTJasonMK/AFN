"""
提示词预览对话框

展示发送给图片生成模型的实际提示词，包含所有处理后的内容。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class PromptPreviewDialog(QDialog):
    """提示词预览对话框"""

    def __init__(self, preview_data: dict, parent=None):
        """
        初始化对话框

        Args:
            preview_data: 预览数据，包含：
                - success: 是否成功
                - error: 错误信息（如果失败）
                - original_prompt: 原始提示词
                - scene_type: 场景类型（英文）
                - scene_type_zh: 场景类型（中文）
                - final_prompt: 最终发送的完整提示词
                - prompt_without_context: 不带上下文前缀的提示词
                - negative_prompt: 负面提示词
                - provider: 供应商类型
                - model: 模型名称
                - style: 风格
                - ratio: 宽高比
            parent: 父窗口
        """
        super().__init__(parent)
        self.preview_data = preview_data
        self.setWindowTitle("实际提示词预览")
        self.setMinimumSize(dp(700), dp(500))
        self.resize(dp(850), dp(650))

        self._create_ui()
        self._apply_styles()

    def _create_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(16))

        # 检查是否成功
        if not self.preview_data.get('success', False):
            error_label = QLabel(f"预览失败: {self.preview_data.get('error', '未知错误')}")
            error_label.setObjectName("error_label")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            layout.addStretch()

            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
            return

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("preview_scroll")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, dp(8), 0)
        content_layout.setSpacing(dp(16))

        # 元信息卡片
        meta_card = self._create_meta_card()
        content_layout.addWidget(meta_card)

        # 原始提示词区域
        original_section = self._create_prompt_section(
            "原始提示词",
            "LLM生成的基础提示词",
            self.preview_data.get('original_prompt', ''),
        )
        content_layout.addWidget(original_section)

        # 漫画视觉元素区域（如果有）
        manga_visual = self.preview_data.get('manga_visual_elements', '')
        if manga_visual:
            manga_section = self._create_prompt_section(
                "漫画视觉元素",
                "根据对话、旁白、音效等元数据生成的视觉描述",
                manga_visual,
            )
            content_layout.addWidget(manga_section)

        # 最终提示词区域（带高亮）
        final_section = self._create_prompt_section(
            "实际发送的提示词",
            "包含上下文前缀、风格后缀、宽高比描述、漫画视觉元素等完整内容",
            self.preview_data.get('final_prompt', ''),
            is_final=True,
        )
        content_layout.addWidget(final_section)

        # 负面提示词区域
        negative_prompt = self.preview_data.get('negative_prompt', '')
        if negative_prompt:
            negative_section = self._create_prompt_section(
                "负面提示词",
                "用于排除不想要的元素",
                negative_prompt,
            )
            content_layout.addWidget(negative_section)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_btn = QPushButton("复制完整提示词")
        copy_btn.setObjectName("primary_btn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_final_prompt)
        button_layout.addWidget(copy_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondary_btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_meta_card(self) -> QFrame:
        """创建元信息卡片"""
        card = QFrame()
        card.setObjectName("meta_card")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(24))

        # 供应商
        provider = self.preview_data.get('provider', '未知')
        provider_widget = self._create_meta_item("供应商", provider)
        layout.addWidget(provider_widget)

        # 模型
        model = self.preview_data.get('model', '未知')
        model_widget = self._create_meta_item("模型", model)
        layout.addWidget(model_widget)

        # 场景类型
        scene_type_zh = self.preview_data.get('scene_type_zh', '日常生活')
        scene_widget = self._create_meta_item("检测场景", scene_type_zh)
        layout.addWidget(scene_widget)

        # 风格
        style = self.preview_data.get('style', '')
        if style:
            style_widget = self._create_meta_item("风格", style)
            layout.addWidget(style_widget)

        # 宽高比
        ratio = self.preview_data.get('ratio', '')
        if ratio:
            ratio_widget = self._create_meta_item("宽高比", ratio)
            layout.addWidget(ratio_widget)

        layout.addStretch()

        return card

    def _create_meta_item(self, label: str, value: str) -> QWidget:
        """创建元信息项"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        item_layout = QVBoxLayout(widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(dp(2))

        label_widget = QLabel(label)
        label_widget.setObjectName("meta_label")
        item_layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("meta_value")
        item_layout.addWidget(value_widget)

        return widget

    def _create_prompt_section(
        self,
        title: str,
        description: str,
        content: str,
        is_final: bool = False,
    ) -> QFrame:
        """创建提示词区域"""
        section = QFrame()
        section.setObjectName("final_section" if is_final else "prompt_section")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(8))

        # 标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        title_label = QLabel(title)
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        if is_final:
            tag = QLabel("发送内容")
            tag.setObjectName("final_tag")
            header_layout.addWidget(tag)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 描述
        desc_label = QLabel(description)
        desc_label.setObjectName("section_desc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 内容
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setPlainText(content)
        content_text.setObjectName("prompt_content")
        # 根据内容长度设置高度
        lines = content.count('\n') + 1
        height = min(max(dp(100), lines * dp(20)), dp(250))
        content_text.setMinimumHeight(height)
        content_text.setMaximumHeight(dp(300))
        layout.addWidget(content_text)

        return section

    def _apply_styles(self):
        """应用样式"""
        palette = theme_manager.get_book_palette()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {palette.bg_primary};
            }}

            QScrollArea#preview_scroll {{
                background: transparent;
                border: none;
            }}
            QScrollArea#preview_scroll > QWidget > QWidget {{
                background: transparent;
            }}

            QLabel#error_label {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {getattr(palette, 'error', '#ef4444')};
                padding: {dp(16)}px;
            }}

            QFrame#meta_card {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}

            QLabel#meta_label {{
                font-family: {palette.ui_font};
                font-size: {sp(11)}px;
                color: {palette.text_tertiary};
            }}

            QLabel#meta_value {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {palette.text_primary};
            }}

            QFrame#prompt_section {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}

            QFrame#final_section {{
                background-color: {palette.accent_light};
                border: 2px solid {palette.accent_color};
                border-radius: {dp(8)}px;
            }}

            QLabel#section_title {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {palette.text_primary};
            }}

            QLabel#final_tag {{
                font-family: {palette.ui_font};
                font-size: {sp(10)}px;
                color: white;
                background-color: {palette.accent_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}

            QLabel#section_desc {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
            }}

            QTextEdit#prompt_content {{
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: {sp(12)}px;
                color: {palette.text_primary};
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
            }}

            QPushButton#primary_btn {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton#primary_btn:hover {{
                background-color: {palette.text_primary};
            }}

            QPushButton#secondary_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
            }}
            QPushButton#secondary_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """)

    def _copy_final_prompt(self):
        """复制最终提示词到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        final_prompt = self.preview_data.get('final_prompt', '')
        if final_prompt:
            clipboard = QApplication.clipboard()
            clipboard.setText(final_prompt)
