"""
评审面板构建器 - 章节评审Tab的UI构建逻辑

从 WDWorkspace 中提取，负责创建评审结果Tab的所有UI组件。
包含AI推荐展示、版本优缺点对比、重新评审等功能。
"""

import json
from typing import Callable, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes.button_styles import ButtonStyles
from themes.modern_effects import ModernEffects
from components.empty_state import EmptyStateWithIllustration
from utils.dpi_utils import dp, sp
from .base import BasePanelBuilder


class ReviewPanelBuilder(BasePanelBuilder):
    """评审面板构建器

    职责：创建章节评审Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    继承自 BasePanelBuilder，使用缓存的 styler 属性减少 theme_manager 调用。
    """

    def __init__(
        self,
        on_evaluate_chapter: Optional[Callable[[], None]] = None
    ):
        """初始化构建器

        Args:
            on_evaluate_chapter: 开始评审回调函数
        """
        super().__init__()  # 初始化 BasePanelBuilder，获取 _styler
        self._on_evaluate_chapter = on_evaluate_chapter

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_review_tab(data)

    def create_review_tab(self, chapter_data: dict, parent: QWidget = None) -> QWidget:
        """创建评审结果标签页

        Args:
            chapter_data: 章节数据，包含 evaluation 字段和 versions 字段
            parent: 父组件（用于空状态组件）

        Returns:
            评审Tab的根Widget
        """
        evaluation_str = chapter_data.get('evaluation')
        versions = chapter_data.get('versions') or []
        version_count = len(versions)

        # 如果没有评审数据，显示空状态
        if not evaluation_str:
            return self._create_empty_state(parent, version_count)

        # 解析评审JSON
        try:
            evaluation_data = json.loads(evaluation_str)
        except json.JSONDecodeError:
            return self._create_error_state()

        # 创建评审结果展示容器
        return self._create_review_content(evaluation_data, version_count)

    def _create_empty_state(self, parent: QWidget = None, version_count: int = 0) -> QWidget:
        """创建空状态Widget

        Args:
            parent: 父组件
            version_count: 版本数量，用于决定是否启用评审按钮

        Returns:
            空状态Widget
        """
        # 根据版本数量显示不同的空状态
        if version_count <= 1:
            # 只有一个版本或没有版本，不需要评审
            empty_widget, _ = self._create_empty_state_layout(
                title='无需评审',
                description='评审功能用于比较多个版本并推荐最佳版本\n当前章节只有一个版本，无需评审',
                icon_char='R',
            )
        else:
            # 多个版本，可以评审
            empty_widget, empty_layout = self._create_empty_state_layout(
                title='暂无评审结果',
                description='AI可以分析各版本优缺点并推荐最佳版本',
                icon_char='R',
            )

            # 开始评审按钮
            evaluate_btn = QPushButton("开始评审")
            evaluate_btn.setObjectName("evaluate_btn")
            evaluate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            evaluate_btn.setStyleSheet(ButtonStyles.primary())
            if self._on_evaluate_chapter:
                evaluate_btn.clicked.connect(self._on_evaluate_chapter)
            evaluate_btn.setFixedWidth(dp(160))
            empty_layout.addWidget(evaluate_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return empty_widget

    def _create_error_state(self) -> QWidget:
        """创建错误状态Widget"""
        s = self._styler
        error_widget = QLabel("评审数据格式错误")
        error_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_widget.setStyleSheet(
            f"color: {s.text_secondary}; padding: {dp(40)}px;"
        )
        return error_widget

    def _create_review_content(self, evaluation_data: dict, version_count: int = 0) -> QWidget:
        """创建评审内容Widget

        Args:
            evaluation_data: 解析后的评审数据
            version_count: 版本数量

        Returns:
            评审内容Widget
        """
        s = self._styler

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # AI推荐区域
        best_choice = evaluation_data.get('best_choice', 1)
        reason = evaluation_data.get('reason_for_choice', '暂无说明')
        recommendation_card = self._create_recommendation_card(best_choice, reason)
        layout.addWidget(recommendation_card)

        # 版本评审详情
        evaluation_details = evaluation_data.get('evaluation', {})
        details_scroll = self._create_details_scroll(evaluation_details, best_choice)
        layout.addWidget(details_scroll, stretch=1)

        # 底部重新评审按钮（只有多版本时才显示）
        if version_count > 1:
            reeval_btn = QPushButton("重新评审")
            reeval_btn.setObjectName("reeval_btn")
            reeval_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reeval_btn.setStyleSheet(ButtonStyles.secondary())
            if self._on_evaluate_chapter:
                reeval_btn.clicked.connect(self._on_evaluate_chapter)
            layout.addWidget(reeval_btn)

        return container

    def _create_recommendation_card(self, best_choice: int, reason: str) -> QFrame:
        """创建AI推荐卡片

        Args:
            best_choice: 推荐的版本号
            reason: 推荐理由

        Returns:
            推荐卡片Frame
        """
        s = self._styler

        recommendation_card = QFrame()
        recommendation_card.setObjectName("recommendation_card")

        # 使用渐变背景
        gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)
        recommendation_card.setStyleSheet(f"""
            QFrame#recommendation_card {{
                background: {gradient};
                border-radius: {dp(12)}px;
                border: none;
                padding: {dp(14)}px;
            }}
        """)

        rec_layout = QHBoxLayout(recommendation_card)
        rec_layout.setSpacing(dp(12))
        rec_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：推荐信息
        rec_info = QWidget()
        rec_info.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        rec_info_layout = QVBoxLayout(rec_info)
        rec_info_layout.setContentsMargins(0, 0, 0, 0)
        rec_info_layout.setSpacing(dp(4))

        rec_title = QLabel(f"AI推荐: 版本 {best_choice}")
        rec_title.setObjectName("rec_title")
        rec_title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(15)}px;
            font-weight: 700;
            color: {s.button_text};
        """)
        rec_info_layout.addWidget(rec_title)

        rec_reason = QLabel(reason)
        rec_reason.setObjectName("rec_reason")
        rec_reason.setWordWrap(True)
        rec_reason.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(12)}px;
            color: {s.button_text};
            opacity: 0.9;
        """)
        rec_info_layout.addWidget(rec_reason)

        rec_layout.addWidget(rec_info, stretch=1)

        return recommendation_card

    def _create_details_scroll(
        self,
        evaluation_details: dict,
        best_choice: int
    ) -> QScrollArea:
        """创建评审详情滚动区域

        Args:
            evaluation_details: 各版本的评审详情
            best_choice: 推荐的版本号

        Returns:
            滚动区域Widget
        """
        s = self._styler

        details_scroll = QScrollArea()
        details_scroll.setObjectName("details_scroll")
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        details_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {s.scrollbar_style()}
        """)

        details_container = QWidget()
        details_container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        details_layout = QVBoxLayout(details_container)
        details_layout.setSpacing(dp(10))

        for version_key in sorted(evaluation_details.keys()):
            version_num = version_key.replace('version', '')
            version_data = evaluation_details[version_key]

            version_card = self._create_version_evaluation_card(
                int(version_num),
                version_data,
                int(version_num) == best_choice
            )
            details_layout.addWidget(version_card)

        details_scroll.setWidget(details_container)
        return details_scroll

    def _create_version_evaluation_card(
        self,
        version_num: int,
        version_data: dict,
        is_recommended: bool
    ) -> QFrame:
        """创建单个版本的评审卡片

        Args:
            version_num: 版本号
            version_data: 版本评审数据
            is_recommended: 是否为推荐版本

        Returns:
            评审卡片Frame
        """
        s = self._styler

        card = QFrame()
        card.setObjectName(f"eval_card_{version_num}")

        # 根据是否推荐使用不同样式
        border_style = (
            f"2px solid {s.primary}"
            if is_recommended
            else f"1px solid {s.border_default}"
        )
        card.setStyleSheet(f"""
            QFrame#eval_card_{version_num} {{
                background-color: {s.bg_card};
                border: {border_style};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(dp(8))
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        title = QLabel(f"版本 {version_num}")
        title.setObjectName(f"eval_title_{version_num}")
        title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(14)}px;
            font-weight: 700;
            color: {s.text_primary};
        """)
        header_layout.addWidget(title)

        if is_recommended:
            badge = QLabel("AI推荐")
            badge.setObjectName(f"eval_badge_{version_num}")
            badge.setStyleSheet(f"""
                font-family: {s.serif_font};
                background: {s.primary};
                color: {s.button_text};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(11)}px;
            """)
            header_layout.addWidget(badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 优点区域
        pros = version_data.get('pros', [])
        if pros:
            pros_label = self._create_pros_label(pros, version_num)
            layout.addWidget(pros_label)

        # 缺点区域
        cons = version_data.get('cons', [])
        if cons:
            cons_label = self._create_cons_label(cons, version_num)
            layout.addWidget(cons_label)

        return card

    def _create_pros_label(self, pros: list, version_num: int) -> QLabel:
        """创建优点标签

        Args:
            pros: 优点列表
            version_num: 版本号

        Returns:
            优点标签
        """
        s = self._styler

        pros_text = " | ".join(pros[:2])
        if len(pros) > 2:
            pros_text += f" (+{len(pros) - 2})"

        pros_label = QLabel(f"+ {pros_text}")
        pros_label.setObjectName(f"pros_label_{version_num}")
        pros_label.setWordWrap(True)
        pros_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(12)}px;
            color: {s.text_success};
            padding: {dp(4)}px {dp(8)}px;
            background-color: {s.success_bg};
            border-radius: {dp(4)}px;
        """)
        return pros_label

    def _create_cons_label(self, cons: list, version_num: int) -> QLabel:
        """创建缺点标签

        Args:
            cons: 缺点列表
            version_num: 版本号

        Returns:
            缺点标签
        """
        s = self._styler

        cons_text = " | ".join(cons[:2])
        if len(cons) > 2:
            cons_text += f" (+{len(cons) - 2})"

        cons_label = QLabel(f"- {cons_text}")
        cons_label.setObjectName(f"cons_label_{version_num}")
        cons_label.setWordWrap(True)
        cons_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(12)}px;
            color: {s.text_warning};
            padding: {dp(4)}px {dp(8)}px;
            background-color: {s.warning_bg};
            border-radius: {dp(4)}px;
        """)
        return cons_label
