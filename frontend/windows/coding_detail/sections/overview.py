"""
编程项目概览Section

显示编程项目的基本信息：标题、类型、风格、摘要等。
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class CodingOverviewSection(BaseSection):
    """编程项目概览Section

    显示：
    - 一句话摘要
    - 目标受众
    - 项目类型
    - 技术风格
    - 项目调性
    - 架构概述
    """

    # 重新生成蓝图信号
    regenerateBlueprintRequested = pyqtSignal(str)  # preference (可为None)

    def __init__(self, data: Dict[str, Any] = None, editable: bool = True, project_id: str = None, parent=None):
        self.project_id = project_id
        super().__init__(data, editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题行（包含重新生成按钮）
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, dp(8))
        header_layout.setSpacing(dp(12))

        section_title = QLabel("架构设计概览")
        section_title.setObjectName("section_title")
        header_layout.addWidget(section_title)

        header_layout.addStretch()

        # 重新生成蓝图按钮
        if self._editable:
            self.regenerate_btn = QPushButton("重新生成蓝图")
            self.regenerate_btn.setObjectName("regenerate_blueprint_btn")
            self.regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.regenerate_btn.clicked.connect(self._on_regenerate_blueprint)
            header_layout.addWidget(self.regenerate_btn)

        layout.addWidget(header_row)

        # 一句话摘要卡片
        self.summary_card = self._create_field_card(
            "一句话摘要",
            self._data.get('one_sentence_summary', '') if self._data else '',
            'one_sentence_summary',
            multiline=False
        )
        layout.addWidget(self.summary_card)

        # 基本信息行
        info_row = QWidget()
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(16))

        # 目标受众
        self.audience_card = self._create_field_card(
            "目标受众",
            self._data.get('target_audience', '') if self._data else '',
            'target_audience',
            multiline=False
        )
        info_layout.addWidget(self.audience_card)

        # 项目类型
        self.type_card = self._create_field_card(
            "项目类型",
            self._data.get('project_type_desc', '') if self._data else '',
            'project_type_desc',
            multiline=False
        )
        info_layout.addWidget(self.type_card)

        layout.addWidget(info_row)

        # 风格行
        style_row = QWidget()
        style_layout = QHBoxLayout(style_row)
        style_layout.setContentsMargins(0, 0, 0, 0)
        style_layout.setSpacing(dp(16))

        # 技术风格
        self.tech_style_card = self._create_field_card(
            "技术风格",
            self._data.get('tech_style', '') if self._data else '',
            'tech_style',
            multiline=False
        )
        style_layout.addWidget(self.tech_style_card)

        # 项目调性
        self.tone_card = self._create_field_card(
            "项目调性",
            self._data.get('project_tone', '') if self._data else '',
            'project_tone',
            multiline=False
        )
        style_layout.addWidget(self.tone_card)

        layout.addWidget(style_row)

        # 架构概述卡片
        self.synopsis_card = self._create_field_card(
            "架构概述",
            self._data.get('architecture_synopsis', '') if self._data else '',
            'architecture_synopsis',
            multiline=True
        )
        layout.addWidget(self.synopsis_card)

        # 技术栈卡片
        tech_stack = self._data.get('tech_stack', {}) if self._data else {}
        self.tech_stack_card = self._create_tech_stack_card(tech_stack)
        layout.addWidget(self.tech_stack_card)

        layout.addStretch()

    def _create_field_card(
        self,
        title: str,
        value: str,
        field_name: str,
        multiline: bool = False
    ) -> QFrame:
        """创建字段卡片"""
        card = QFrame()
        card.setObjectName("field_card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(8))

        # 标题行
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(8))

        title_label = QLabel(title)
        title_label.setObjectName("field_title")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 编辑按钮
        if self._editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda: self.requestEdit(field_name, title, value)
            )
            title_layout.addWidget(edit_btn)

        layout.addWidget(title_row)

        # 内容
        value_label = QLabel(value or "暂无内容")
        value_label.setObjectName("field_value")
        value_label.setWordWrap(True)
        if multiline:
            value_label.setMinimumHeight(dp(80))
        layout.addWidget(value_label)

        # 保存引用
        card.value_label = value_label

        self._apply_card_style(card)
        return card

    def _create_tech_stack_card(self, tech_stack: dict) -> QFrame:
        """创建技术栈卡片"""
        card = QFrame()
        card.setObjectName("tech_stack_card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题
        title_label = QLabel("技术栈")
        title_label.setObjectName("tech_stack_title")
        layout.addWidget(title_label)

        if not tech_stack:
            empty_label = QLabel("暂无技术栈信息")
            empty_label.setObjectName("tech_stack_empty")
            layout.addWidget(empty_label)
        else:
            # 核心技术约束
            core_constraints = tech_stack.get('core_constraints', '')
            if core_constraints:
                constraints_widget = self._create_tech_field("核心约束", core_constraints)
                layout.addWidget(constraints_widget)

            # 技术组件
            components = tech_stack.get('components', [])
            if components:
                components_widget = self._create_tech_list("技术组件", components)
                layout.addWidget(components_widget)

            # 技术领域
            domains = tech_stack.get('domains', [])
            if domains:
                domains_widget = self._create_tech_list("技术领域", domains)
                layout.addWidget(domains_widget)

            # 如果都为空
            if not any([core_constraints, components, domains]):
                empty_label = QLabel("暂无技术栈信息")
                empty_label.setObjectName("tech_stack_empty")
                layout.addWidget(empty_label)

        self._apply_tech_stack_style(card)
        return card

    def _create_tech_field(self, label: str, value: str) -> QWidget:
        """创建技术栈字段"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        label_widget = QLabel(label)
        label_widget.setObjectName("tech_field_label")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("tech_field_value")
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget)

        return widget

    def _create_tech_list(self, label: str, items: list) -> QWidget:
        """创建技术栈列表"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        label_widget = QLabel(label)
        label_widget.setObjectName("tech_field_label")
        layout.addWidget(label_widget)

        # 创建标签流式布局
        tags_widget = QWidget()
        tags_layout = QHBoxLayout(tags_widget)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(dp(8))

        for item in items[:6]:  # 最多显示6个
            name = item.get('name', '') if isinstance(item, dict) else str(item)
            desc = item.get('description', '') if isinstance(item, dict) else ''

            tag = QLabel(name)
            tag.setObjectName("tech_tag")
            if desc:
                tag.setToolTip(desc)
            tags_layout.addWidget(tag)

        if len(items) > 6:
            more_label = QLabel(f"+{len(items) - 6}")
            more_label.setObjectName("tech_tag_more")
            tags_layout.addWidget(more_label)

        tags_layout.addStretch()
        layout.addWidget(tags_widget)

        return widget

    def _apply_tech_stack_style(self, card: QFrame):
        """应用技术栈卡片样式"""
        card.setStyleSheet(f"""
            QFrame#tech_stack_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#tech_stack_title {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#tech_stack_empty {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                font-style: italic;
            }}
            QLabel#tech_field_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                font-weight: 500;
            }}
            QLabel#tech_field_value {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
            }}
            QLabel#tech_tag {{
                background-color: {theme_manager.PRIMARY}15;
                color: {theme_manager.PRIMARY};
                font-size: {dp(12)}px;
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                border: 1px solid {theme_manager.PRIMARY}30;
            }}
            QLabel#tech_tag_more {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                padding: {dp(4)}px;
            }}
        """)

    def _apply_card_style(self, card: QFrame):
        """应用卡片样式"""
        card.setStyleSheet(f"""
            QFrame#field_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#field_title {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#field_value {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                line-height: 1.5;
            }}
            QPushButton#edit_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: none;
                font-size: {dp(12)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton#edit_btn:hover {{
                background-color: {theme_manager.PRIMARY}20;
                border-radius: {dp(4)}px;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        # 标题样式
        for child in self.findChildren(QLabel):
            if child.objectName() == "section_title":
                child.setStyleSheet(f"""
                    QLabel#section_title {{
                        color: {theme_manager.TEXT_PRIMARY};
                        font-size: {dp(18)}px;
                        font-weight: 600;
                    }}
                """)

        # 重新生成按钮样式
        if hasattr(self, 'regenerate_btn') and self.regenerate_btn:
            self.regenerate_btn.setStyleSheet(f"""
                QPushButton#regenerate_blueprint_btn {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                }}
                QPushButton#regenerate_blueprint_btn:hover {{
                    background-color: {theme_manager.PRIMARY}15;
                }}
            """)

        for card in [
            self.summary_card,
            self.audience_card,
            self.type_card,
            self.tech_style_card,
            self.tone_card,
            self.synopsis_card
        ]:
            if card:
                self._apply_card_style(card)

        # 技术栈卡片单独应用样式
        if hasattr(self, 'tech_stack_card') and self.tech_stack_card:
            self._apply_tech_stack_style(self.tech_stack_card)

    def _on_regenerate_blueprint(self):
        """重新生成蓝图按钮点击"""
        from components.dialogs import get_regenerate_preference

        preference, ok = get_regenerate_preference(
            self,
            title="重新生成架构设计蓝图",
            message="重新生成将基于已有的需求分析对话重新设计架构。\n\n"
                    "现有的蓝图数据将被覆盖。",
            placeholder="例如：更注重微服务架构、增加缓存层设计、简化技术栈等"
        )
        if ok:
            self.regenerateBlueprintRequested.emit(preference if preference else "")

    def updateData(self, data: Dict[str, Any]):
        """更新数据"""
        super().updateData(data)

        if hasattr(self, 'summary_card') and self.summary_card:
            self.summary_card.value_label.setText(
                data.get('one_sentence_summary', '') or "暂无内容"
            )
        if hasattr(self, 'audience_card') and self.audience_card:
            self.audience_card.value_label.setText(
                data.get('target_audience', '') or "暂无内容"
            )
        if hasattr(self, 'type_card') and self.type_card:
            self.type_card.value_label.setText(
                data.get('project_type_desc', '') or "暂无内容"
            )
        if hasattr(self, 'tech_style_card') and self.tech_style_card:
            self.tech_style_card.value_label.setText(
                data.get('tech_style', '') or "暂无内容"
            )
        if hasattr(self, 'tone_card') and self.tone_card:
            self.tone_card.value_label.setText(
                data.get('project_tone', '') or "暂无内容"
            )
        if hasattr(self, 'synopsis_card') and self.synopsis_card:
            self.synopsis_card.value_label.setText(
                data.get('architecture_synopsis', '') or "暂无内容"
            )
        # 技术栈卡片需要重建（因为结构复杂）
        # 简化处理：这里不做动态更新，依赖页面刷新


__all__ = ["CodingOverviewSection"]
