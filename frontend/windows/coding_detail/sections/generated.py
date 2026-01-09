"""
已生成内容Section

显示编程项目已生成的内容（类似小说的已生成章节）。
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class GeneratedItemCard(QFrame):
    """已生成内容卡片"""

    viewClicked = pyqtSignal(int)  # feature_number
    editClicked = pyqtSignal(int)  # feature_number

    def __init__(self, feature_number: int, item_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.feature_number = feature_number
        self.item_data = item_data
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("generated_card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 左侧：序号
        index_label = QLabel(str(self.feature_number))
        index_label.setObjectName("item_index")
        index_label.setFixedWidth(dp(32))
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(index_label)

        # 中间：内容信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题
        title = self.item_data.get('title', f'功能 {self.feature_number}')
        title_label = QLabel(title)
        title_label.setObjectName("item_title")
        info_layout.addWidget(title_label)

        # 摘要或描述
        summary = self.item_data.get('summary', '')
        if summary:
            summary_label = QLabel(summary[:100] + '...' if len(summary) > 100 else summary)
            summary_label.setObjectName("item_summary")
            summary_label.setWordWrap(True)
            info_layout.addWidget(summary_label)

        # 元信息行
        meta_row = QWidget()
        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(dp(16))

        # 字数
        word_count = self.item_data.get('word_count', 0)
        if word_count:
            word_label = QLabel(f"{word_count} 字")
            word_label.setObjectName("item_meta")
            meta_layout.addWidget(word_label)

        # 版本数
        version_count = self.item_data.get('version_count', 1)
        version_label = QLabel(f"{version_count} 个版本")
        version_label.setObjectName("item_meta")
        meta_layout.addWidget(version_label)

        # 创建时间
        created_at = self.item_data.get('created_at', '')
        if created_at:
            # 简化时间显示
            if 'T' in created_at:
                created_at = created_at.split('T')[0]
            time_label = QLabel(created_at)
            time_label.setObjectName("item_meta")
            meta_layout.addWidget(time_label)

        meta_layout.addStretch()
        info_layout.addWidget(meta_row)

        layout.addWidget(info_widget, 1)

        # 右侧：状态和操作
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(dp(8))

        # 状态标签
        status = self.item_data.get('status', 'draft')
        status_label = QLabel(self._get_status_label(status))
        status_label.setObjectName(f"status_{status}")
        action_layout.addWidget(status_label)

        # 查看按钮
        view_btn = QPushButton("查看")
        view_btn.setObjectName("view_btn")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.clicked.connect(lambda: self.viewClicked.emit(self.feature_number))
        action_layout.addWidget(view_btn)

        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("edit_btn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.editClicked.emit(self.feature_number))
        action_layout.addWidget(edit_btn)

        layout.addWidget(action_widget)

        self._apply_style()

    def _get_status_label(self, status: str) -> str:
        """获取状态标签"""
        labels = {
            'draft': '草稿',
            'generated': '已生成',
            'reviewed': '已审核',
            'published': '已发布',
        }
        return labels.get(status, status)

    def _apply_style(self):
        """应用样式"""
        status = self.item_data.get('status', 'draft')

        self.setStyleSheet(f"""
            QFrame#generated_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QFrame#generated_card:hover {{
                border-color: {theme_manager.PRIMARY}50;
            }}
            QLabel#item_index {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(14)}px;
                font-weight: 600;
                background-color: {theme_manager.BORDER_DEFAULT}30;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px;
            }}
            QLabel#item_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#item_summary {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
            }}
            QLabel#item_meta {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
            }}
            QLabel#status_draft {{
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BORDER_DEFAULT};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#status_generated {{
                color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY}15;
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#status_reviewed {{
                color: {theme_manager.SUCCESS};
                background-color: {theme_manager.SUCCESS}15;
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#status_published {{
                color: {theme_manager.SUCCESS};
                background-color: {theme_manager.SUCCESS}15;
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QPushButton#view_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#view_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QPushButton#edit_btn {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#edit_btn:hover {{
                background-color: {theme_manager.BORDER_DEFAULT}30;
            }}
        """)


class GeneratedSection(BaseSection):
    """已生成内容Section

    显示：
    - 已生成的内容列表
    - 每个内容的标题、摘要、状态、版本数
    - 支持查看、编辑操作（跳转到工作台）
    """

    dataChanged = pyqtSignal()
    navigateToDesk = pyqtSignal(int)  # feature_number - 导航到工作台

    def __init__(
        self,
        chapters: List[Dict] = None,
        features: List[Dict] = None,
        parent=None
    ):
        self._item_cards = []
        self._project_id = None
        self._chapters = chapters or []
        self._features = features or []
        super().__init__(self._chapters, False, parent)
        self.setupUI()

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        self._project_id = project_id

    def setFeatures(self, features: List[Dict]):
        """设置功能列表（用于获取标题）"""
        self._features = features or []

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("已生成内容")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        # 内容数量
        count = len(self._chapters) if self._chapters else 0
        count_label = QLabel(f"共 {count} 项")
        count_label.setObjectName("item_count")
        header_layout.addWidget(count_label)
        self.count_label = count_label

        header_layout.addStretch()

        # 统计信息
        if self._chapters:
            total_words = sum(ch.get('word_count', 0) for ch in self._chapters)
            if total_words > 0:
                stats_label = QLabel(f"总计 {total_words:,} 字")
                stats_label.setObjectName("stats_label")
                header_layout.addWidget(stats_label)
                self.stats_label = stats_label

        # 打开工作台按钮
        open_desk_btn = QPushButton("打开工作台")
        open_desk_btn.setObjectName("open_desk_btn")
        open_desk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_desk_btn.clicked.connect(lambda: self.navigateToDesk.emit(1))  # 默认选中第一个功能
        header_layout.addWidget(open_desk_btn)

        layout.addWidget(header)

        # 内容列表容器
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(dp(12))

        # 填充内容卡片
        self._populate_items()

        layout.addWidget(self.items_container)
        layout.addStretch()

        self._apply_header_style()

    def _populate_items(self):
        """填充内容卡片"""
        # 清除现有卡片
        for card in self._item_cards:
            card.deleteLater()
        self._item_cards.clear()

        if not self._chapters:
            empty_widget = self._create_empty_state()
            self.items_layout.addWidget(empty_widget)
            self._item_cards.append(empty_widget)
            return

        # 构建 feature_number 到功能数据的映射
        feature_map = {}
        for f in self._features:
            fn = f.get('feature_number', 0)
            if fn > 0:
                feature_map[fn] = f

        # 构建章节到功能的映射（chapter_number = feature_number）
        for chapter in self._chapters:
            chapter_number = chapter.get('chapter_number', 0)
            feature_number = chapter_number  # feature_number 就是 chapter_number

            # 通过 feature_number 查找对应的功能
            feature = feature_map.get(feature_number, {})
            feature_title = feature.get('name') or feature.get('title') or f'功能 {feature_number}'
            feature_summary = feature.get('description') or feature.get('summary', '')

            # 合并数据
            item_data = {
                'title': feature_title,
                'summary': feature_summary,
                'word_count': chapter.get('word_count', 0) or 0,
                'version_count': chapter.get('version_count', 0) or len(chapter.get('versions') or []),
                'status': chapter.get('status', 'generated') or 'generated',
                'created_at': chapter.get('created_at', '') or '',
            }

            card = GeneratedItemCard(feature_number, item_data)
            card.viewClicked.connect(self._on_view_item)
            card.editClicked.connect(self._on_edit_item)
            self.items_layout.addWidget(card)
            self._item_cards.append(card)

    def _create_empty_state(self) -> QWidget:
        """创建空状态组件"""
        empty = QFrame()
        empty.setObjectName("empty_state")

        layout = QVBoxLayout(empty)
        layout.setContentsMargins(dp(40), dp(60), dp(40), dp(60))
        layout.setSpacing(dp(16))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 图标占位
        icon_label = QLabel("[ ]")
        icon_label.setObjectName("empty_icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 提示文字
        text_label = QLabel("暂无已生成内容")
        text_label.setObjectName("empty_text")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)

        # 提示说明
        hint_label = QLabel("在工作台中选择功能并生成内容")
        hint_label.setObjectName("empty_hint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        # 打开工作台按钮
        open_btn = QPushButton("打开工作台")
        open_btn.setObjectName("open_desk_btn_empty")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.navigateToDesk.emit(1))  # 默认选中第一个功能
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        empty.setStyleSheet(f"""
            QFrame#empty_state {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 2px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
            }}
            QLabel#empty_icon {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(48)}px;
            }}
            QLabel#empty_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(16)}px;
                font-weight: 500;
            }}
            QLabel#empty_hint {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
            }}
            QPushButton#open_desk_btn_empty {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {dp(14)}px;
            }}
            QPushButton#open_desk_btn_empty:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

        return empty

    def _apply_header_style(self):
        """应用标题样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QLabel#item_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(8)}px;
            }}
            QLabel#stats_label {{
                color: {theme_manager.PRIMARY};
                font-size: {dp(13)}px;
                font-weight: 500;
            }}
            QPushButton#open_desk_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#open_desk_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_header_style()
        for card in self._item_cards:
            if isinstance(card, GeneratedItemCard):
                card._apply_style()

    def _on_view_item(self, feature_number: int):
        """查看内容 - 导航到工作台"""
        logger.info(f"View feature: {feature_number}")
        self.navigateToDesk.emit(feature_number)

    def _on_edit_item(self, feature_number: int):
        """编辑内容 - 导航到工作台"""
        logger.info(f"Edit feature: {feature_number}")
        self.navigateToDesk.emit(feature_number)

    def updateData(self, chapters: List[Dict], features: List[Dict] = None):
        """更新数据"""
        self._chapters = chapters or []
        if features is not None:
            self._features = features

        # 更新计数
        if hasattr(self, 'count_label') and self.count_label:
            count = len(self._chapters)
            self.count_label.setText(f"共 {count} 项")

        # 更新统计
        if hasattr(self, 'stats_label'):
            total_words = sum(ch.get('word_count', 0) for ch in self._chapters)
            self.stats_label.setText(f"总计 {total_words:,} 字")

        # 重新填充内容
        self._populate_items()


__all__ = ["GeneratedSection"]
