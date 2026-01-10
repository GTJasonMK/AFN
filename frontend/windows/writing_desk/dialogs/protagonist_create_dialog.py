"""
主角档案创建对话框

允许用户创建新的主角档案，可以从蓝图角色中选择或手动输入。
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QTextEdit, QWidget, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker
from api.manager import APIClientManager

logger = logging.getLogger(__name__)


class AttributeInputCard(ThemeAwareWidget):
    """属性输入卡片"""

    def __init__(self, category: str, title: str, icon: str, parent=None):
        self.category = category
        self.title = title
        self.icon = icon
        self.title_label = None
        self.text_edit = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon_label = QLabel(self.icon)
        icon_label.setObjectName("category_icon")
        header.addWidget(icon_label)

        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("category_title")
        header.addWidget(self.title_label)

        header.addStretch()
        layout.addLayout(header)

        # 提示文本
        hint_label = QLabel(self._get_hint_text())
        hint_label.setObjectName("hint_label")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 输入框
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("attr_input")
        self.text_edit.setPlaceholderText(self._get_placeholder())
        self.text_edit.setMaximumHeight(dp(100))
        layout.addWidget(self.text_edit)

    def _get_hint_text(self) -> str:
        hints = {
            "explicit": "外在可见的特征，如外貌、装备、技能等",
            "implicit": "内在性格特质，如性格、价值观、习惯等",
            "social": "社会关系和地位，如身份、人际关系等"
        }
        return hints.get(self.category, "")

    def _get_placeholder(self) -> str:
        placeholders = {
            "explicit": "例如：\n外貌: 黑发黑眼，身材修长\n年龄: 18岁\n装备: 青铜剑",
            "implicit": "例如：\n性格: 坚韧不拔\n价值观: 重情重义\n弱点: 过于信任他人",
            "social": "例如：\n身份: 落魄贵族\n师门: 青云宗外门弟子\n仇敌: 王家"
        }
        return placeholders.get(self.category, "")

    def _apply_theme(self):
        ui_font = theme_manager.ui_font()
        bg_secondary = theme_manager.book_bg_secondary()
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

        if icon_label := self.findChild(QLabel, "category_icon"):
            icon_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-size: {sp(18)}px;
                color: {accent_color};
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {text_primary};
            """)

        if hint_label := self.findChild(QLabel, "hint_label"):
            hint_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {text_tertiary};
            """)

        if self.text_edit:
            bg_primary = theme_manager.book_bg_primary()
            self.text_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_primary};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_SM};
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {text_primary};
                    padding: {dp(8)}px;
                }}
                QTextEdit:focus {{
                    border-color: {accent_color};
                }}
            """)

    def get_attributes(self) -> Dict[str, Any]:
        """解析输入的属性，返回字典"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            return {}

        attrs = {}
        for line in text.split('\n'):
            line = line.strip()
            if ':' in line or '：' in line:
                # 支持中英文冒号
                sep = '：' if '：' in line else ':'
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        attrs[key] = value
        return attrs


class ProtagonistCreateDialog(QDialog):
    """主角档案创建对话框"""

    profileCreated = pyqtSignal(dict)  # 创建成功后发出信号

    def __init__(self, project_id: str, blueprint_characters: List[Dict] = None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.blueprint_characters = blueprint_characters or []
        self.api_client = APIClientManager.get_client()
        self._create_worker = None

        self.name_input = None
        self.character_combo = None
        self.explicit_card = None
        self.implicit_card = None
        self.social_card = None

        self.setWindowTitle("创建主角档案")
        self.setMinimumSize(dp(550), dp(650))
        self.setModal(True)

        self._setup_ui()
        self._apply_theme()

        # 连接主题切换信号
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
        title_label = QLabel("创建主角档案")
        title_label.setObjectName("dialog_title")
        layout.addWidget(title_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(theme_manager.scrollbar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, dp(8), 0)
        content_layout.setSpacing(dp(16))

        # 角色名称输入
        name_frame = QFrame()
        name_frame.setObjectName("name_frame")
        name_layout = QVBoxLayout(name_frame)
        name_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        name_layout.setSpacing(dp(8))

        name_label = QLabel("角色名称")
        name_label.setObjectName("section_label")
        name_layout.addWidget(name_label)

        # 如果有蓝图角色，显示下拉选择
        if self.blueprint_characters:
            combo_layout = QHBoxLayout()
            combo_layout.setSpacing(dp(8))

            self.character_combo = QComboBox()
            self.character_combo.setObjectName("character_combo")
            self.character_combo.addItem("-- 从蓝图角色选择 --", "")
            for char in self.blueprint_characters:
                name = char.get('name', '')
                identity = char.get('identity', '')
                display = f"{name} ({identity})" if identity else name
                self.character_combo.addItem(display, name)
            self.character_combo.currentIndexChanged.connect(self._on_character_selected)
            combo_layout.addWidget(self.character_combo, stretch=1)

            combo_layout.addWidget(QLabel("或"))

            self.name_input = QLineEdit()
            self.name_input.setObjectName("name_input")
            self.name_input.setPlaceholderText("手动输入名称")
            combo_layout.addWidget(self.name_input, stretch=1)

            name_layout.addLayout(combo_layout)
        else:
            self.name_input = QLineEdit()
            self.name_input.setObjectName("name_input")
            self.name_input.setPlaceholderText("输入主角名称")
            name_layout.addWidget(self.name_input)

        content_layout.addWidget(name_frame)

        # 三类属性输入
        self.explicit_card = AttributeInputCard("explicit", "显性属性", "◉")
        content_layout.addWidget(self.explicit_card)

        self.implicit_card = AttributeInputCard("implicit", "隐性属性", "◎")
        content_layout.addWidget(self.implicit_card)

        self.social_card = AttributeInputCard("social", "社会属性", "◈")
        content_layout.addWidget(self.social_card)

        # 提示信息
        tip_label = QLabel("提示：初始属性可以留空，后续通过章节同步自动提取")
        tip_label.setObjectName("tip_label")
        tip_label.setWordWrap(True)
        content_layout.addWidget(tip_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("创建")
        create_btn.setObjectName("create_btn")
        create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _on_character_selected(self, index: int):
        """从蓝图角色选择时"""
        if index > 0 and self.character_combo:
            name = self.character_combo.currentData()
            if self.name_input:
                self.name_input.setText(name)

            # 尝试填充角色信息
            for char in self.blueprint_characters:
                if char.get('name') == name:
                    # 填充显性属性
                    explicit = {}
                    if char.get('appearance'):
                        explicit['外貌'] = char['appearance']
                    if explicit and self.explicit_card:
                        text = '\n'.join(f"{k}: {v}" for k, v in explicit.items())
                        self.explicit_card.text_edit.setPlainText(text)

                    # 填充隐性属性
                    implicit = {}
                    if char.get('personality'):
                        implicit['性格'] = char['personality']
                    if char.get('goals'):
                        implicit['目标'] = char['goals']
                    if implicit and self.implicit_card:
                        text = '\n'.join(f"{k}: {v}" for k, v in implicit.items())
                        self.implicit_card.text_edit.setPlainText(text)

                    # 填充社会属性
                    social = {}
                    if char.get('identity'):
                        social['身份'] = char['identity']
                    if char.get('abilities'):
                        social['能力'] = char['abilities']
                    if social and self.social_card:
                        text = '\n'.join(f"{k}: {v}" for k, v in social.items())
                        self.social_card.text_edit.setPlainText(text)
                    break

    def _on_create(self):
        """创建档案"""
        # 获取名称
        name = ""
        if self.name_input:
            name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "提示", "请输入角色名称")
            return

        # 获取属性
        explicit_attrs = self.explicit_card.get_attributes() if self.explicit_card else {}
        implicit_attrs = self.implicit_card.get_attributes() if self.implicit_card else {}
        social_attrs = self.social_card.get_attributes() if self.social_card else {}

        # 禁用按钮
        if create_btn := self.findChild(QPushButton, "create_btn"):
            create_btn.setEnabled(False)
            create_btn.setText("创建中...")

        def do_create():
            return self.api_client.create_protagonist_profile(
                project_id=self.project_id,
                character_name=name,
                explicit_attributes=explicit_attrs if explicit_attrs else None,
                implicit_attributes=implicit_attrs if implicit_attrs else None,
                social_attributes=social_attrs if social_attrs else None,
            )

        def on_success(result):
            logger.info(f"创建主角档案成功: {name}")
            self.profileCreated.emit(result)
            self.accept()

        def on_error(error):
            logger.error(f"创建主角档案失败: {error}")
            QMessageBox.critical(self, "错误", f"创建失败: {error}")
            if create_btn := self.findChild(QPushButton, "create_btn"):
                create_btn.setEnabled(True)
                create_btn.setText("创建")

        self._create_worker = AsyncWorker(do_create)
        self._create_worker.success.connect(on_success)
        self._create_worker.error.connect(on_error)
        self._create_worker.start()

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

        if title_label := self.findChild(QLabel, "dialog_title"):
            title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {text_primary};
                padding-bottom: {dp(8)}px;
            """)

        if name_frame := self.findChild(QFrame, "name_frame"):
            name_frame.setStyleSheet(f"""
                QFrame#name_frame {{
                    background-color: {bg_secondary};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_MD};
                }}
            """)

        if section_label := self.findChild(QLabel, "section_label"):
            section_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {text_primary};
            """)

        if self.name_input:
            self.name_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {bg_primary};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_SM};
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {text_primary};
                    padding: {dp(8)}px {dp(12)}px;
                }}
                QLineEdit:focus {{
                    border-color: {accent_color};
                }}
            """)

        if self.character_combo:
            self.character_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {bg_primary};
                    border: 1px solid {border_color};
                    border-radius: {theme_manager.RADIUS_SM};
                    font-family: {ui_font};
                    font-size: {theme_manager.FONT_SIZE_SM};
                    color: {text_primary};
                    padding: {dp(8)}px {dp(12)}px;
                }}
                QComboBox:focus {{
                    border-color: {accent_color};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: {dp(24)}px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {bg_primary};
                    border: 1px solid {border_color};
                    color: {text_primary};
                    selection-background-color: {accent_color};
                }}
            """)

        if tip_label := self.findChild(QLabel, "tip_label"):
            tip_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {text_tertiary};
                font-style: italic;
                padding: {dp(8)}px 0;
            """)

        if cancel_btn := self.findChild(QPushButton, "cancel_btn"):
            cancel_btn.setStyleSheet(ButtonStyles.secondary('MD'))

        if create_btn := self.findChild(QPushButton, "create_btn"):
            create_btn.setStyleSheet(ButtonStyles.primary('MD'))

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
