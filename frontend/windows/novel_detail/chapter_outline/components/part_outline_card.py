"""
部分大纲卡片组件

显示长篇小说的部分大纲网格
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QGridLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from ..dialogs import PartOutlineDetailDialog


class PartOutlineCard(QFrame):
    """部分大纲卡片 - 展示所有部分大纲的网格视图"""

    regenerateClicked = pyqtSignal()  # 重新生成所有部分
    regeneratePartClicked = pyqtSignal(int)  # 重新生成指定部分（参数：部分编号）

    def __init__(self, part_outlines: list, editable: bool = True, parent=None):
        super().__init__(parent)
        self.part_outlines = part_outlines or []
        self.editable = editable
        # 使用现代UI字体
        self.ui_font = theme_manager.ui_font()
        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self.ui_font = theme_manager.ui_font()
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(dp(16))

        # Header区域
        self._create_header()

        # 部分大纲网格
        self._create_grid()

    def _create_header(self):
        """创建头部区域"""
        header = QHBoxLayout()

        # 标题区
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(4))

        self.title_label = QLabel("部分大纲")
        title_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(f"全书共分为 {len(self.part_outlines)} 个部分")
        title_layout.addWidget(self.subtitle_label)

        header.addWidget(title_widget, stretch=1)

        # 重新生成按钮
        if self.editable:
            self.regenerate_btn = QPushButton("重新生成")
            self.regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.regenerate_btn.clicked.connect(self.regenerateClicked.emit)
            header.addWidget(self.regenerate_btn)

        # 长篇标签
        self.tag_label = QLabel("长篇小说")
        header.addWidget(self.tag_label)

        self._layout.addLayout(header)

    def _create_grid(self):
        """创建部分大纲网格"""
        self.grid = QGridLayout()
        self.grid.setSpacing(dp(16))
        self.part_cards = []

        for idx, part in enumerate(self.part_outlines):
            row = idx // 3
            col = idx % 3

            part_card = self._create_single_part_card(part, idx)
            self.part_cards.append(part_card)
            self.grid.addWidget(part_card, row, col)

        self._layout.addLayout(self.grid)

    def _create_single_part_card(self, part: dict, idx: int) -> QFrame:
        """创建单个部分卡片"""
        card = QFrame()
        card.setObjectName("part_card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(dp(8))

        # 头部：部分编号 + 章节范围
        part_header = QHBoxLayout()

        part_num = QLabel(f"第{part.get('part_number', idx+1)}部分")
        part_num.setObjectName("part_num")
        part_header.addWidget(part_num, stretch=1)

        part_range = QLabel(f"{part.get('start_chapter', '')}-{part.get('end_chapter', '')}章")
        part_range.setObjectName("part_range")
        part_header.addWidget(part_range)

        card_layout.addLayout(part_header)

        # 标题
        part_title = QLabel(part.get('title', ''))
        part_title.setWordWrap(True)
        part_title.setObjectName("part_title")
        card_layout.addWidget(part_title)

        # 摘要
        part_summary = QLabel(part.get('summary', ''))
        part_summary.setWordWrap(True)
        part_summary.setObjectName("part_summary")
        part_summary.setMaximumHeight(dp(60))  # 增加高度显示更多内容
        card_layout.addWidget(part_summary)

        # 底部按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(8))

        # 查看详情按钮
        detail_btn = QPushButton("查看完整详情")
        detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detail_btn.setObjectName("detail_btn")
        detail_btn.clicked.connect(lambda: self._show_detail_dialog(part))
        button_layout.addWidget(detail_btn)

        # 重新生成此部分按钮（仅在editable时显示）
        if self.editable:
            regen_btn = QPushButton("重新生成")
            regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            regen_btn.setObjectName("regen_part_btn")
            part_number = part.get('part_number', idx + 1)
            regen_btn.clicked.connect(lambda: self.regeneratePartClicked.emit(part_number))
            button_layout.addWidget(regen_btn)

        card_layout.addLayout(button_layout)

        return card

    def _show_detail_dialog(self, part: dict):
        """显示部分大纲详情对话框"""
        dialog = PartOutlineDetailDialog(part, parent=self)
        dialog.exec()

    def _apply_style(self):
        """应用样式"""
        # 主容器样式
        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置样式
        self.setStyleSheet(f"""
            background-color: {theme_manager.BG_SECONDARY};
            border: 1px solid {theme_manager.BORDER_LIGHT};
            border-radius: {dp(12)}px;
            padding: {dp(24)}px;
        """)

        # 标题样式
        self.title_label.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(20)}px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};"
        )
        self.subtitle_label.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};"
        )

        # 重新生成按钮样式
        if self.editable and hasattr(self, 'regenerate_btn'):
            self.regenerate_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {self.ui_font};
                    background-color: {theme_manager.WARNING_BG};
                    color: {theme_manager.WARNING};
                    border: 1px solid {theme_manager.WARNING};
                    border-radius: {dp(6)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {sp(12)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                    color: {theme_manager.BUTTON_TEXT};
                }}
            """)

        # 标签样式
        self.tag_label.setStyleSheet(f"""
            font-family: {self.ui_font};
            background-color: {theme_manager.PRIMARY_PALE};
            color: {theme_manager.PRIMARY};
            padding: {dp(4)}px {dp(12)}px;
            border-radius: {dp(12)}px;
            font-size: {sp(11)}px;
            font-weight: 600;
        """)

        # 部分卡片样式
        for card in self.part_cards:
            card.setStyleSheet(f"""
                QFrame#part_card {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {dp(12)}px;
                    padding: {dp(16)}px;
                }}
            """)
            # 子元素样式
            for child in card.findChildren(QLabel):
                name = child.objectName()
                if name == "part_num":
                    child.setStyleSheet(
                        f"font-family: {self.ui_font}; font-size: {sp(14)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};"
                    )
                elif name == "part_range":
                    child.setStyleSheet(
                        f"font-family: {self.ui_font}; font-size: {sp(11)}px; color: {theme_manager.TEXT_SECONDARY};"
                    )
                elif name == "part_title":
                    child.setStyleSheet(
                        f"font-family: {self.ui_font}; font-size: {sp(13)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};"
                    )
                elif name == "part_summary":
                    child.setStyleSheet(
                        f"font-family: {self.ui_font}; font-size: {sp(12)}px; color: {theme_manager.TEXT_SECONDARY};"
                    )

            # 查看详情按钮样式
            for btn in card.findChildren(QPushButton):
                obj_name = btn.objectName()
                if obj_name == "detail_btn":
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-family: {self.ui_font};
                            background-color: {theme_manager.PRIMARY_PALE};
                            color: {theme_manager.PRIMARY};
                            border: 1px solid {theme_manager.PRIMARY};
                            border-radius: {dp(6)}px;
                            padding: {dp(6)}px {dp(12)}px;
                            font-size: {sp(12)}px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{
                            background-color: {theme_manager.PRIMARY};
                            color: {theme_manager.BUTTON_TEXT};
                        }}
                    """)
                elif obj_name == "regen_part_btn":
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-family: {self.ui_font};
                            background-color: {theme_manager.WARNING_BG};
                            color: {theme_manager.WARNING};
                            border: 1px solid {theme_manager.WARNING};
                            border-radius: {dp(6)}px;
                            padding: {dp(6)}px {dp(12)}px;
                            font-size: {sp(12)}px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{
                            background-color: {theme_manager.WARNING};
                            color: {theme_manager.BUTTON_TEXT};
                        }}
                    """)

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_data(self, part_outlines: list):
        """更新数据"""
        self.part_outlines = part_outlines or []
        self.subtitle_label.setText(f"全书共分为 {len(self.part_outlines)} 个部分")

        # 清除旧网格
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.part_cards.clear()

        # 重建网格
        for idx, part in enumerate(self.part_outlines):
            row = idx // 3
            col = idx % 3
            part_card = self._create_single_part_card(part, idx)
            self.part_cards.append(part_card)
            self.grid.addWidget(part_card, row, col)

        self._apply_style()

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass