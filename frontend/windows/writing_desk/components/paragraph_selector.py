"""
段落选择器组件

用于选择要分析的段落，支持全选、清空选择等操作。
"""

import re
import logging
from typing import List, Set

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QScrollArea, QPushButton, QFrame, QSizePolicy,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

logger = logging.getLogger(__name__)


def parse_range_input(text: str, max_index: int) -> Set[int]:
    """
    解析范围输入，支持格式如 "1-5, 9-18, 20"

    Args:
        text: 输入文本
        max_index: 最大索引（段落总数）

    Returns:
        选中的索引集合（0-based）
    """
    result = set()
    if not text.strip():
        return result

    # 分割逗号或空格分隔的部分
    parts = re.split(r'[,\s]+', text.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            # 范围格式: 1-5
            try:
                range_parts = part.split('-')
                if len(range_parts) == 2:
                    start = int(range_parts[0].strip())
                    end = int(range_parts[1].strip())
                    # 转换为 0-based 索引，并限制范围
                    for i in range(max(0, start - 1), min(max_index, end)):
                        result.add(i)
            except ValueError:
                continue
        else:
            # 单个数字: 5
            try:
                num = int(part)
                # 转换为 0-based 索引
                if 1 <= num <= max_index:
                    result.add(num - 1)
            except ValueError:
                continue

    return result


class ParagraphItem(QFrame):
    """单个段落项 - 使用简单的 QFrame 而不是 ThemeAwareFrame"""

    selection_changed = pyqtSignal(int, bool)  # (索引, 是否选中)

    def __init__(self, index: int, text: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.text = text

        self._setup_ui()
        self._apply_style()

        # 连接主题切换
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        layout.setSpacing(dp(8))

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.checkbox)

        # 段落号
        self.index_label = QLabel(f"{self.index + 1}.")
        self.index_label.setFixedWidth(dp(30))
        layout.addWidget(self.index_label)

        # 预览文本
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        preview = preview.replace("\n", " ")
        self.preview_label = QLabel(preview)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.preview_label, stretch=1)

        # 字数
        self.length_label = QLabel(f"{len(self.text)}字")
        self.length_label.setFixedWidth(dp(60))
        layout.addWidget(self.length_label)

    def _apply_style(self):
        """应用样式"""
        ui_font = theme_manager.ui_font()

        # 整个项的样式
        self.setStyleSheet(f"""
            ParagraphItem {{
                background-color: {theme_manager.BG_CARD};
                border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
            }}
            ParagraphItem:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
            }}
        """)

        # 复选框样式
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: {dp(16)}px;
                height: {dp(16)}px;
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(3)}px;
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme_manager.PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

        # 标签样式
        self.index_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_SECONDARY};
        """)

        self.preview_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_PRIMARY};
        """)

        self.length_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)

    def _on_state_changed(self, state):
        """复选框状态变化"""
        is_checked = state == Qt.CheckState.Checked.value
        self.selection_changed.emit(self.index, is_checked)

    def set_checked(self, checked: bool):
        """设置选中状态"""
        self.checkbox.setChecked(checked)

    def is_checked(self) -> bool:
        """是否选中"""
        return self.checkbox.isChecked()


class ParagraphSelector(QWidget):
    """段落选择器 - 使用简单的 QWidget"""

    paragraphs_selected = pyqtSignal(list)  # 选中的段落索引列表

    def __init__(self, content: str = "", parent=None):
        super().__init__(parent)
        self.content = content
        self.paragraphs: List[str] = []
        self.selected_indices: Set[int] = set()
        self.paragraph_items: List[ParagraphItem] = []

        self._setup_ui()
        self._apply_style()

        # 连接主题切换
        theme_manager.theme_changed.connect(self._on_theme_changed)

        if content:
            self.set_content(content)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 头部
        header = QHBoxLayout()

        self.header_label = QLabel("选择要分析的段落")
        header.addWidget(self.header_label)

        header.addStretch()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setFixedWidth(dp(60))
        self.select_all_btn.clicked.connect(self.select_all)
        header.addWidget(self.select_all_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(dp(60))
        self.clear_btn.clicked.connect(self.clear_selection)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        # 范围选择器
        range_layout = QHBoxLayout()
        range_layout.setSpacing(dp(8))

        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("输入范围，如: 1-5, 9-18, 20")
        self.range_input.returnPressed.connect(self._apply_range_selection)
        range_layout.addWidget(self.range_input, stretch=1)

        self.apply_range_btn = QPushButton("应用")
        self.apply_range_btn.setFixedWidth(dp(60))
        self.apply_range_btn.clicked.connect(self._apply_range_selection)
        range_layout.addWidget(self.apply_range_btn)

        layout.addLayout(range_layout)

        # 状态标签
        self.status_label = QLabel("已选择 0 个段落")
        layout.addWidget(self.status_label)

        # 滚动区域 - 参考 chapter_list.py 的实现
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 容器 widget
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, stretch=1)

    def _apply_style(self):
        """应用样式"""
        ui_font = theme_manager.ui_font()

        self.header_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)

        btn_style = f"""
            QPushButton {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_CARD_HOVER};
            }}
        """
        self.select_all_btn.setStyleSheet(btn_style)
        self.clear_btn.setStyleSheet(btn_style)
        self.apply_range_btn.setStyleSheet(btn_style)

        # 范围输入框样式
        self.range_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {theme_manager.TEXT_TERTIARY};
            }}
        """)

        self.status_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)

        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                background-color: {theme_manager.BG_CARD};
            }}
            {theme_manager.scrollbar()}
        """)

        self.scroll_content.setStyleSheet(f"""
            background-color: {theme_manager.BG_CARD};
        """)

    def set_content(self, content: str):
        """
        设置内容并分割段落

        Args:
            content: 正文内容
        """
        self.content = content
        self.paragraphs = self._split_paragraphs(content)
        self.selected_indices.clear()

        logger.info("ParagraphSelector.set_content: 内容长度=%d, 分割出%d个段落",
                    len(content) if content else 0, len(self.paragraphs))

        # 清除旧的段落项
        for item in self.paragraph_items:
            item.deleteLater()
        self.paragraph_items.clear()

        # 清除旧的布局项（包括 stretch）
        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            # widget 已经在上面删除了，这里只是清除布局项

        # 创建新的段落项
        for i, paragraph in enumerate(self.paragraphs):
            item = ParagraphItem(i, paragraph, parent=self.scroll_content)
            item.selection_changed.connect(self._on_selection_changed)
            self.paragraph_items.append(item)
            self.scroll_layout.addWidget(item)

        # 关键：在末尾添加 stretch
        self.scroll_layout.addStretch()

        logger.info("ParagraphSelector: 创建了%d个段落项", len(self.paragraph_items))
        self._update_status()

    def _split_paragraphs(self, content: str) -> List[str]:
        """
        分割段落

        Args:
            content: 正文内容

        Returns:
            段落列表
        """
        if not content or not content.strip():
            return []

        # 统一换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # 尝试按双换行符分割（标准段落格式）
        double_newline_paragraphs = re.split(r'\n\s*\n', content)
        double_newline_paragraphs = [p.strip() for p in double_newline_paragraphs if p.strip()]

        # 如果双换行分割结果只有1段或更少，尝试按单换行分割
        if len(double_newline_paragraphs) <= 1:
            # 按单换行符分割
            single_newline_paragraphs = content.split('\n')
            single_newline_paragraphs = [p.strip() for p in single_newline_paragraphs if p.strip()]

            # 如果单换行分割有多个段落，使用它
            if len(single_newline_paragraphs) > 1:
                return single_newline_paragraphs

        return double_newline_paragraphs

    def _on_selection_changed(self, index: int, is_checked: bool):
        """选择状态变化"""
        if is_checked:
            self.selected_indices.add(index)
        else:
            self.selected_indices.discard(index)

        self._update_status()
        self.paragraphs_selected.emit(list(self.selected_indices))

    def _update_status(self):
        """更新状态显示"""
        count = len(self.selected_indices)
        total = len(self.paragraphs)

        if count == 0:
            self.status_label.setText(f"共 {total} 个段落，未选择（将分析全部）")
        else:
            self.status_label.setText(f"已选择 {count}/{total} 个段落")

    def select_all(self):
        """全选"""
        self.selected_indices = set(range(len(self.paragraphs)))
        for item in self.paragraph_items:
            item.set_checked(True)
        self._update_status()
        self.paragraphs_selected.emit(list(self.selected_indices))

    def clear_selection(self):
        """清空选择"""
        self.selected_indices.clear()
        for item in self.paragraph_items:
            item.set_checked(False)
        self._update_status()
        self.paragraphs_selected.emit([])

    def get_selected_indices(self) -> List[int]:
        """获取选中的段落索引"""
        return sorted(list(self.selected_indices))

    def get_selected_paragraphs(self) -> List[str]:
        """获取选中的段落内容"""
        return [self.paragraphs[i] for i in sorted(self.selected_indices)]

    def get_total_count(self) -> int:
        """获取总段落数"""
        return len(self.paragraphs)

    def is_all_selected(self) -> bool:
        """是否全选"""
        return len(self.selected_indices) == len(self.paragraphs) and len(self.paragraphs) > 0

    def has_selection(self) -> bool:
        """是否有选择"""
        return len(self.selected_indices) > 0

    def _apply_range_selection(self):
        """应用范围选择"""
        text = self.range_input.text()
        if not text.strip():
            return

        # 解析范围输入
        indices = parse_range_input(text, len(self.paragraphs))
        if not indices:
            logger.warning("范围输入解析结果为空: %s", text)
            return

        # 先清空当前选择
        self.selected_indices.clear()
        for item in self.paragraph_items:
            item.set_checked(False)

        # 应用新的选择
        self.selected_indices = indices
        for idx in indices:
            if idx < len(self.paragraph_items):
                self.paragraph_items[idx].set_checked(True)

        logger.info("范围选择应用成功: 选中了 %d 个段落", len(indices))
        self._update_status()
        self.paragraphs_selected.emit(list(self.selected_indices))
