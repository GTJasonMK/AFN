"""
功能大纲Section

显示编程项目的功能大纲（对应小说的章节大纲）。
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


class FeatureCard(QFrame):
    """功能卡片"""

    generateClicked = pyqtSignal(int)  # feature_index
    viewClicked = pyqtSignal(int)  # feature_index

    def __init__(self, index: int, feature_data: Dict[str, Any], chapter_data: Dict = None, parent=None):
        super().__init__(parent)
        self.index = index
        self.feature_data = feature_data
        self.chapter_data = chapter_data  # 对应的章节数据（如果已生成）
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("feature_card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 左侧：序号
        index_label = QLabel(str(self.index + 1))
        index_label.setObjectName("feature_index")
        index_label.setFixedWidth(dp(32))
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(index_label)

        # 中间：功能信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题
        title = self.feature_data.get('title') or self.feature_data.get('name', f'功能 {self.index + 1}')
        title_label = QLabel(title)
        title_label.setObjectName("feature_title")
        info_layout.addWidget(title_label)

        # 描述
        summary = self.feature_data.get('summary') or self.feature_data.get('description', '')
        if summary:
            summary_label = QLabel(summary[:100] + '...' if len(summary) > 100 else summary)
            summary_label.setObjectName("feature_summary")
            summary_label.setWordWrap(True)
            info_layout.addWidget(summary_label)

        # 元信息行
        meta_row = QWidget()
        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(dp(16))

        # 优先级
        priority = self.feature_data.get('priority', 'medium')
        priority_labels = {'high': '高优先级', 'medium': '中优先级', 'low': '低优先级'}
        priority_label = QLabel(priority_labels.get(priority, priority))
        priority_label.setObjectName(f"priority_{priority}")
        meta_layout.addWidget(priority_label)

        # 如果已生成，显示字数
        if self.chapter_data:
            word_count = self.chapter_data.get('word_count', 0)
            if word_count:
                word_label = QLabel(f"{word_count} 字")
                word_label.setObjectName("feature_meta")
                meta_layout.addWidget(word_label)

        meta_layout.addStretch()
        info_layout.addWidget(meta_row)

        layout.addWidget(info_widget, 1)

        # 右侧：状态和操作
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(dp(8))

        # 状态
        if self.chapter_data:
            status = self.chapter_data.get('status', 'generated')
            status_labels = {'generated': '已生成', 'reviewed': '已审核'}
            status_label = QLabel(status_labels.get(status, '已生成'))
            status_label.setObjectName("status_generated")
            action_layout.addWidget(status_label)

            # 查看按钮
            view_btn = QPushButton("查看")
            view_btn.setObjectName("view_btn")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.clicked.connect(lambda: self.viewClicked.emit(self.index))
            action_layout.addWidget(view_btn)

            # 重新生成按钮
            regen_btn = QPushButton("重生成")
            regen_btn.setObjectName("regen_btn")
            regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            regen_btn.clicked.connect(lambda: self.generateClicked.emit(self.index))
            action_layout.addWidget(regen_btn)
        else:
            status_label = QLabel("待生成")
            status_label.setObjectName("status_pending")
            action_layout.addWidget(status_label)

            # 生成按钮
            gen_btn = QPushButton("生成")
            gen_btn.setObjectName("gen_btn")
            gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gen_btn.clicked.connect(lambda: self.generateClicked.emit(self.index))
            action_layout.addWidget(gen_btn)

        layout.addWidget(action_widget)

        self._apply_style()

    def _apply_style(self):
        """应用样式"""
        priority = self.feature_data.get('priority', 'medium')
        priority_colors = {
            'high': theme_manager.ERROR,
            'medium': theme_manager.WARNING,
            'low': theme_manager.TEXT_TERTIARY,
        }
        priority_color = priority_colors.get(priority, theme_manager.TEXT_TERTIARY)

        self.setStyleSheet(f"""
            QFrame#feature_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QFrame#feature_card:hover {{
                border-color: {theme_manager.PRIMARY}50;
            }}
            QLabel#feature_index {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(14)}px;
                font-weight: 600;
                background-color: {theme_manager.BORDER_DEFAULT}30;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px;
            }}
            QLabel#feature_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#feature_summary {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
            }}
            QLabel#feature_meta {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(12)}px;
            }}
            QLabel#priority_high {{
                color: {theme_manager.ERROR};
                font-size: {dp(11)}px;
            }}
            QLabel#priority_medium {{
                color: {theme_manager.WARNING};
                font-size: {dp(11)}px;
            }}
            QLabel#priority_low {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
            }}
            QLabel#status_pending {{
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BORDER_DEFAULT};
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QLabel#status_generated {{
                color: {theme_manager.SUCCESS};
                background-color: {theme_manager.SUCCESS}15;
                font-size: {dp(11)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
            QPushButton#gen_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#gen_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
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
            QPushButton#regen_btn {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#regen_btn:hover {{
                background-color: {theme_manager.BORDER_DEFAULT}30;
            }}
        """)


class FeaturesSection(BaseSection):
    """功能大纲Section

    显示：
    - 功能卡片列表
    - 每个功能的标题、摘要、优先级、状态
    - 支持生成功能文档，导航到工作台
    """

    refreshRequested = pyqtSignal()
    generateRequested = pyqtSignal(int, str)  # 功能编号(1-based), 功能标题
    navigateToDesk = pyqtSignal(int)  # 导航到工作台，传递feature_number

    def __init__(
        self,
        features: List[Dict] = None,
        chapters: List[Dict] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        """初始化功能大纲Section

        Args:
            features: 功能列表（来自蓝图的chapter_outline或modules）
            chapters: 章节列表（已生成的功能内容）
            project_id: 项目ID
            editable: 是否可编辑
            parent: 父组件
        """
        self.features = features or []
        self.chapters = chapters or []
        self.project_id = project_id
        self.feature_cards = []  # 保存卡片引用
        self.cards_container = None
        self.count_label = None
        super().__init__(features, editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("功能大纲")
        title_label.setObjectName("section_title")
        header_layout.addWidget(title_label)

        # 功能数量
        count = len(self.features)
        self.count_label = QLabel(f"共 {count} 个功能")
        self.count_label.setObjectName("feature_count")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # 打开工作台按钮
        desk_btn = QPushButton("打开工作台")
        desk_btn.setObjectName("desk_btn")
        desk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        desk_btn.clicked.connect(lambda: self.navigateToDesk.emit(1))  # 默认选中第一个功能
        header_layout.addWidget(desk_btn)

        # 操作按钮
        if self._editable:
            refresh_btn = QPushButton("刷新大纲")
            refresh_btn.setObjectName("refresh_btn")
            refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            refresh_btn.clicked.connect(self._on_refresh)
            header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("features_scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # 卡片容器
        self.cards_container = QWidget()
        cards_layout = QVBoxLayout(self.cards_container)
        cards_layout.setContentsMargins(0, 0, dp(8), 0)
        cards_layout.setSpacing(dp(8))

        # 填充功能卡片
        self._populate_features()

        cards_layout.addStretch()
        scroll_area.setWidget(self.cards_container)

        layout.addWidget(scroll_area, 1)

        self._apply_styles()

    def _populate_features(self):
        """填充功能卡片"""
        # 清除现有卡片
        self.feature_cards.clear()
        if self.cards_container:
            layout = self.cards_container.layout()
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        if not self.features:
            # 空状态
            empty_label = QLabel("暂无功能大纲")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_container.layout().addWidget(empty_label)
            return

        # 构建章节映射（chapter_number -> chapter_data）
        chapter_map = {ch.get('chapter_number'): ch for ch in self.chapters}

        # 创建功能卡片
        for idx, feature in enumerate(self.features):
            # feature_index + 1 = chapter_number
            chapter_data = chapter_map.get(idx + 1)

            card = FeatureCard(
                index=idx,
                feature_data=feature,
                chapter_data=chapter_data,
                parent=self.cards_container
            )

            # 连接信号
            card.generateClicked.connect(self._on_generate_clicked)
            card.viewClicked.connect(self._on_view_clicked)

            self.cards_container.layout().addWidget(card)
            self.feature_cards.append(card)

    def _on_generate_clicked(self, feature_index: int):
        """处理生成点击"""
        if feature_index < len(self.features):
            feature = self.features[feature_index]
            feature_number = feature_index + 1  # 转换为1-based
            title = feature.get('title') or feature.get('name', f'功能 {feature_number}')
            self.generateRequested.emit(feature_number, title)
            # 导航到工作台
            self.navigateToDesk.emit(feature_number)

    def _on_view_clicked(self, feature_index: int):
        """处理查看点击"""
        feature_number = feature_index + 1  # 转换为1-based
        self.navigateToDesk.emit(feature_number)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QLabel#feature_count {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(8)}px;
            }}
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(14)}px;
                padding: {dp(40)}px;
            }}
            QScrollArea#features_scroll {{
                background-color: transparent;
                border: none;
            }}
            QPushButton#desk_btn {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#desk_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton#refresh_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#refresh_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_styles()
        # 重新应用卡片样式
        for card in self.feature_cards:
            card._apply_style()

    def _on_refresh(self):
        """刷新大纲"""
        self.refreshRequested.emit()

    def updateData(self, features: List[Dict], chapters: List[Dict] = None):
        """更新数据

        Args:
            features: 功能列表
            chapters: 章节列表
        """
        self.features = features or []
        self._data = self.features
        if chapters is not None:
            self.chapters = chapters

        # 更新计数
        if self.count_label:
            count = len(self.features)
            self.count_label.setText(f"共 {count} 个功能")

        # 重新填充功能卡片
        self._populate_features()


__all__ = ["FeaturesSection"]
