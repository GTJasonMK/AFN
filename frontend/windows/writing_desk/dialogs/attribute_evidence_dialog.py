"""
属性溯源对话框

显示某个属性的变更历史和原文证据。
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt

from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class ChangeRecordCard(ThemeAwareWidget):
    """变更记录卡片"""

    def __init__(self, change: Dict[str, Any], parent=None):
        self.change = change
        self.chapter_label = None
        self.operation_label = None
        self.description_label = None
        self.evidence_label = None
        self.value_label = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 头部：章节号和操作类型
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        self.chapter_label = QLabel(f"第 {self.change.get('chapter_number', '?')} 章")
        self.chapter_label.setObjectName("chapter_label")
        header.addWidget(self.chapter_label)

        operation = self.change.get('operation', 'unknown')
        operation_text = {'add': '新增', 'modify': '修改', 'delete': '删除'}.get(operation, operation)
        self.operation_label = QLabel(operation_text)
        self.operation_label.setObjectName("operation_label")
        header.addWidget(self.operation_label)

        header.addStretch()
        layout.addLayout(header)

        # 变更描述
        description = self.change.get('change_description', '')
        if description:
            self.description_label = QLabel(description)
            self.description_label.setObjectName("description_label")
            self.description_label.setWordWrap(True)
            layout.addWidget(self.description_label)

        # 值变化
        old_value = self.change.get('old_value')
        new_value = self.change.get('new_value')
        if old_value or new_value:
            value_text = ""
            if old_value and new_value:
                value_text = f"从 \"{old_value}\" 变为 \"{new_value}\""
            elif new_value:
                value_text = f"设为 \"{new_value}\""
            elif old_value:
                value_text = f"删除 \"{old_value}\""

            if value_text:
                self.value_label = QLabel(value_text)
                self.value_label.setObjectName("value_label")
                self.value_label.setWordWrap(True)
                layout.addWidget(self.value_label)

        # 触发事件
        event_cause = self.change.get('event_cause', '')
        if event_cause:
            cause_label = QLabel(f"触发事件: {event_cause}")
            cause_label.setObjectName("cause_label")
            cause_label.setWordWrap(True)
            layout.addWidget(cause_label)

        # 原文证据（关键）
        evidence = self.change.get('evidence', '')
        if evidence:
            evidence_frame = QFrame()
            evidence_frame.setObjectName("evidence_frame")
            evidence_layout = QVBoxLayout(evidence_frame)
            evidence_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
            evidence_layout.setSpacing(dp(4))

            evidence_title = QLabel("原文依据:")
            evidence_title.setObjectName("evidence_title")
            evidence_layout.addWidget(evidence_title)

            self.evidence_label = QLabel(evidence)
            self.evidence_label.setObjectName("evidence_label")
            self.evidence_label.setWordWrap(True)
            evidence_layout.addWidget(self.evidence_label)

            layout.addWidget(evidence_frame)

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()
        bg_secondary = theme_manager.book_bg_secondary()
        bg_tertiary = theme_manager.book_bg_tertiary() if hasattr(theme_manager, 'book_bg_tertiary') else bg_secondary
        border_color = theme_manager.book_border_color()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.book_text_tertiary()
        accent_color = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            background-color: {bg_secondary};
            border: 1px solid {border_color};
            border-radius: {theme_manager.RADIUS_MD};
        """)

        if self.chapter_label:
            self.chapter_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {accent_color};
            """)

        if self.operation_label:
            operation = self.change.get('operation', '')
            color_map = {
                'add': '#4CAF50',  # 绿色
                'modify': '#FF9800',  # 橙色
                'delete': '#F44336',  # 红色
            }
            op_color = color_map.get(operation, text_secondary)
            self.operation_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                color: {op_color};
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(4)}px;
            """)

        if self.description_label:
            self.description_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {text_primary};
            """)

        if self.value_label:
            self.value_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {text_secondary};
                font-style: italic;
            """)

        if cause_label := self.findChild(QLabel, "cause_label"):
            cause_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                color: {text_tertiary};
            """)

        if evidence_frame := self.findChild(QFrame, "evidence_frame"):
            evidence_frame.setStyleSheet(f"""
                QFrame#evidence_frame {{
                    background-color: {theme_manager.book_bg_primary()};
                    border: 1px dashed {border_color};
                    border-radius: {theme_manager.RADIUS_SM};
                }}
            """)

        if evidence_title := self.findChild(QLabel, "evidence_title"):
            evidence_title.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XS};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {text_tertiary};
            """)

        if self.evidence_label:
            self.evidence_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {text_primary};
                line-height: 1.5;
            """)


class AttributeEvidenceDialog(QDialog):
    """属性溯源对话框"""

    def __init__(
        self,
        project_id: str,
        character_name: str,
        category: str,
        attribute_key: str,
        current_value: Any,
        parent=None
    ):
        super().__init__(parent)
        self.project_id = project_id
        self.character_name = character_name
        self.category = category
        self.attribute_key = attribute_key
        self.current_value = current_value
        self.api_client = APIClientManager.get_client()
        self._worker = None

        self.title_label = None
        self.current_value_label = None
        self.content_container = None
        self.loading_label = None

        category_names = {
            'explicit': '显性属性',
            'implicit': '隐性属性',
            'social': '社会属性'
        }
        category_display = category_names.get(category, category)

        self.setWindowTitle(f"属性溯源 - {attribute_key}")
        self.setMinimumSize(dp(500), dp(500))
        self.setModal(True)

        self._setup_ui()
        self._apply_theme()
        self._load_history()

        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_theme()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(f"{self.attribute_key} 的变更历史")
        self.title_label.setObjectName("dialog_title")
        layout.addWidget(self.title_label)

        # 当前值
        current_frame = QFrame()
        current_frame.setObjectName("current_frame")
        current_layout = QHBoxLayout(current_frame)
        current_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))

        current_label = QLabel("当前值:")
        current_label.setObjectName("current_label")
        current_layout.addWidget(current_label)

        value_text = self._format_value(self.current_value)
        self.current_value_label = QLabel(value_text)
        self.current_value_label.setObjectName("current_value_label")
        self.current_value_label.setWordWrap(True)
        current_layout.addWidget(self.current_value_label, stretch=1)

        layout.addWidget(current_frame)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(theme_manager.scrollbar())

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, dp(8), 0)
        self.content_layout.setSpacing(dp(12))

        # 加载提示
        self.loading_label = QLabel("正在加载变更历史...")
        self.loading_label.setObjectName("loading_label")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.loading_label)

        self.content_layout.addStretch()
        scroll.setWidget(self.content_container)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _format_value(self, value: Any) -> str:
        """格式化值为字符串"""
        if isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value) if value else "无"

    def _load_history(self):
        """加载变更历史"""
        def do_load():
            return self.api_client.get_protagonist_change_history(
                project_id=self.project_id,
                character_name=self.character_name,
                category=self.category
            )

        def on_success(history: List[Dict]):
            # 过滤出当前属性的变更
            filtered = [h for h in history if h.get('attribute_key') == self.attribute_key]

            # 清空加载提示
            if self.loading_label:
                self.loading_label.setVisible(False)

            if not filtered:
                empty_label = QLabel("暂无变更记录")
                empty_label.setObjectName("empty_label")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.insertWidget(0, empty_label)
                self._style_empty_label(empty_label)
            else:
                # 按章节倒序显示
                filtered.sort(key=lambda x: x.get('chapter_number', 0), reverse=True)
                for change in filtered:
                    card = ChangeRecordCard(change)
                    self.content_layout.insertWidget(self.content_layout.count() - 1, card)

        def on_error(error):
            logger.error(f"加载变更历史失败: {error}")
            if self.loading_label:
                self.loading_label.setText(f"加载失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _style_empty_label(self, label: QLabel):
        """设置空状态标签样式"""
        ui_font = theme_manager.ui_font()
        text_tertiary = theme_manager.book_text_tertiary()
        label.setStyleSheet(f"""
            color: {text_tertiary};
            font-family: {ui_font};
            font-size: {theme_manager.FONT_SIZE_MD};
            padding: {dp(40)}px;
        """)

    def _apply_theme(self):
        """应用主题"""
        ui_font = theme_manager.ui_font()
        bg_primary = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.book_text_tertiary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_primary};
            }}
        """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {text_primary};
            """)

        if current_frame := self.findChild(QFrame, "current_frame"):
            current_frame.setStyleSheet(f"""
                QFrame#current_frame {{
                    background-color: {bg_secondary};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)

        if current_label := self.findChild(QLabel, "current_label"):
            current_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {text_secondary};
            """)

        if self.current_value_label:
            self.current_value_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {accent_color};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
            """)

        if self.loading_label:
            self.loading_label.setStyleSheet(f"""
                color: {text_tertiary};
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                padding: {dp(40)}px;
            """)

        if close_btn := self.findChild(QPushButton, "close_btn"):
            close_btn.setStyleSheet(ButtonStyles.secondary('MD'))

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
