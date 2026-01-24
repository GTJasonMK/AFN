"""
项目规划Section

显示编程项目的规划信息：核心需求、技术挑战、非功能需求、风险评估、里程碑。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget,
    QGridLayout
)
from PyQt6.QtCore import Qt

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class ProjectPlanningSection(BaseSection):
    """项目规划Section

    显示：
    - 核心需求列表
    - 技术挑战与解决方案
    - 非功能需求
    - 风险评估
    - 里程碑
    """

    def __init__(self, data: Dict[str, Any] = None, editable: bool = True, parent=None):
        super().__init__(data, editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = self._create_scroll_container_layout()

        # 1. 核心需求卡片
        requirements = self._data.get('core_requirements', []) if self._data else []
        self.requirements_card = self._create_requirements_card(requirements)
        layout.addWidget(self.requirements_card)

        # 2. 技术挑战卡片
        challenges = self._data.get('technical_challenges', []) if self._data else []
        self.challenges_card = self._create_challenges_card(challenges)
        layout.addWidget(self.challenges_card)

        # 3. 非功能需求卡片
        nfr = self._data.get('non_functional_requirements') if self._data else None
        self.nfr_card = self._create_nfr_card(nfr)
        layout.addWidget(self.nfr_card)

        # 4. 风险评估卡片
        risks = self._data.get('risks', []) if self._data else []
        self.risks_card = self._create_risks_card(risks)
        layout.addWidget(self.risks_card)

        # 5. 里程碑卡片
        milestones = self._data.get('milestones', []) if self._data else []
        self.milestones_card = self._create_milestones_card(milestones)
        layout.addWidget(self.milestones_card)

        layout.addStretch()

    def _create_requirements_card(self, requirements: List[Dict]) -> QFrame:
        """创建核心需求卡片"""
        card = self._create_card_frame("核心需求")
        layout = card.layout()

        if not requirements:
            layout.addWidget(self._create_empty_label("暂无核心需求"))
        else:
            # 表格：分类、需求描述、优先级
            grid = QGridLayout()
            grid.setSpacing(dp(8))

            headers = ['分类', '需求描述', '优先级']
            for col, header in enumerate(headers):
                label = QLabel(header)
                label.setObjectName("grid_header")
                grid.addWidget(label, 0, col)

            for row, req in enumerate(requirements, start=1):
                # 分类
                category = req.get('category', '-')
                grid.addWidget(self._create_cell_label(category), row, 0)

                # 需求描述
                requirement = req.get('requirement', '-')
                grid.addWidget(self._create_cell_label(requirement, wrap=True), row, 1)

                # 优先级
                priority = req.get('priority', 'should-have')
                priority_label = self._create_priority_label(priority)
                grid.addWidget(priority_label, row, 2)

            # 设置列宽比例
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 4)
            grid.setColumnStretch(2, 1)

            layout.addLayout(grid)

        self._apply_card_style(card)
        return card

    def _create_challenges_card(self, challenges: List[Dict]) -> QFrame:
        """创建技术挑战卡片"""
        card = self._create_card_frame("技术挑战")
        layout = card.layout()

        if not challenges:
            layout.addWidget(self._create_empty_label("暂无技术挑战"))
        else:
            # 表格：挑战、影响、解决方向
            grid = QGridLayout()
            grid.setSpacing(dp(8))

            headers = ['挑战', '影响程度', '解决方向']
            for col, header in enumerate(headers):
                label = QLabel(header)
                label.setObjectName("grid_header")
                grid.addWidget(label, 0, col)

            for row, ch in enumerate(challenges, start=1):
                # 挑战描述
                challenge = ch.get('challenge', '-')
                grid.addWidget(self._create_cell_label(challenge, wrap=True), row, 0)

                # 影响程度
                impact = ch.get('impact', 'medium')
                impact_label = self._create_impact_label(impact)
                grid.addWidget(impact_label, row, 1)

                # 解决方向
                solution = ch.get('solution_direction', '-')
                grid.addWidget(self._create_cell_label(solution, wrap=True), row, 2)

            grid.setColumnStretch(0, 2)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(2, 2)

            layout.addLayout(grid)

        self._apply_card_style(card)
        return card

    def _create_nfr_card(self, nfr: Optional[Dict]) -> QFrame:
        """创建非功能需求卡片"""
        card = self._create_card_frame("非功能需求")
        layout = card.layout()

        if not nfr:
            layout.addWidget(self._create_empty_label("暂无非功能需求"))
        else:
            # 性能要求
            performance = nfr.get('performance', '')
            if performance:
                layout.addWidget(self._create_field_group("性能要求", performance))

            # 安全要求
            security = nfr.get('security', '')
            if security:
                layout.addWidget(self._create_field_group("安全要求", security))

            # 可扩展性
            scalability = nfr.get('scalability', '')
            if scalability:
                layout.addWidget(self._create_field_group("可扩展性", scalability))

            # 可靠性
            reliability = nfr.get('reliability', '')
            if reliability:
                layout.addWidget(self._create_field_group("可靠性", reliability))

            # 可维护性
            maintainability = nfr.get('maintainability', '')
            if maintainability:
                layout.addWidget(self._create_field_group("可维护性", maintainability))

            # 如果全部为空
            if not any([performance, security, scalability, reliability, maintainability]):
                layout.addWidget(self._create_empty_label("暂无非功能需求"))

        self._apply_card_style(card)
        return card

    def _create_risks_card(self, risks: List[Dict]) -> QFrame:
        """创建风险评估卡片"""
        card = self._create_card_frame("风险评估")
        layout = card.layout()

        if not risks:
            layout.addWidget(self._create_empty_label("暂无风险评估"))
        else:
            # 表格：风险、可能性、影响、缓解措施
            grid = QGridLayout()
            grid.setSpacing(dp(8))

            headers = ['风险描述', '可能性', '缓解措施']
            for col, header in enumerate(headers):
                label = QLabel(header)
                label.setObjectName("grid_header")
                grid.addWidget(label, 0, col)

            for row, risk in enumerate(risks, start=1):
                # 风险描述
                desc = risk.get('risk', '-')
                grid.addWidget(self._create_cell_label(desc, wrap=True), row, 0)

                # 可能性
                probability = risk.get('probability', 'medium')
                grid.addWidget(self._create_level_label(probability), row, 1)

                # 缓解措施
                mitigation = risk.get('mitigation', '-')
                grid.addWidget(self._create_cell_label(mitigation, wrap=True), row, 2)

            grid.setColumnStretch(0, 2)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(2, 2)

            layout.addLayout(grid)

        self._apply_card_style(card)
        return card

    def _create_milestones_card(self, milestones: List[Dict]) -> QFrame:
        """创建里程碑卡片"""
        card = self._create_card_frame("里程碑")
        layout = card.layout()

        if not milestones:
            layout.addWidget(self._create_empty_label("暂无里程碑"))
        else:
            for idx, ms in enumerate(milestones):
                ms_widget = self._create_milestone_item(idx + 1, ms)
                layout.addWidget(ms_widget)

        self._apply_card_style(card)
        return card

    # ==================== 辅助方法 ====================

    def _create_card_frame(self, title: str) -> QFrame:
        """创建卡片框架"""
        card = QFrame()
        card.setObjectName("planning_card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        layout.addWidget(title_label)

        return card

    def _create_empty_label(self, text: str) -> QLabel:
        """创建空状态标签"""
        label = QLabel(text)
        label.setObjectName("empty_label")
        return label

    def _create_cell_label(self, text: str, wrap: bool = False) -> QLabel:
        """创建单元格标签"""
        label = QLabel(str(text) if text else "-")
        label.setObjectName("grid_cell")
        if wrap:
            label.setWordWrap(True)
        return label

    def _create_field_group(self, title: str, value: str) -> QWidget:
        """创建字段组（标题+内容）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, dp(8))
        layout.setSpacing(dp(4))

        title_label = QLabel(title)
        title_label.setObjectName("field_title")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("field_value")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        return widget

    def _create_priority_label(self, priority: str) -> QLabel:
        """创建优先级标签"""
        label = QLabel(self._format_priority(priority))
        label.setObjectName("priority_label")
        label.setProperty("level", priority.lower().replace('-', '_'))
        return label

    def _create_impact_label(self, impact: str) -> QLabel:
        """创建影响程度标签"""
        label = QLabel(self._format_impact(impact))
        label.setObjectName("impact_label")
        label.setProperty("level", impact.lower())
        return label

    def _create_level_label(self, level: str) -> QLabel:
        """创建级别标签（通用）"""
        display = {'high': '高', 'medium': '中', 'low': '低'}.get(level.lower(), level)
        label = QLabel(display)
        label.setObjectName("level_label")
        label.setProperty("level", level.lower())
        return label

    def _create_milestone_item(self, index: int, milestone: Dict) -> QWidget:
        """创建里程碑项"""
        widget = QFrame()
        widget.setObjectName("milestone_item")

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        layout.setSpacing(dp(12))

        # 序号
        index_label = QLabel(f"M{index}")
        index_label.setObjectName("milestone_index")
        index_label.setFixedWidth(dp(32))
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(index_label)

        # 内容区
        content_layout = QVBoxLayout()
        content_layout.setSpacing(dp(4))

        # 阶段名称
        phase = milestone.get('phase', f'阶段 {index}')
        phase_label = QLabel(phase)
        phase_label.setObjectName("milestone_name")
        content_layout.addWidget(phase_label)

        # 目标列表
        goals = milestone.get('goals', [])
        if goals:
            goals_text = "、".join(goals[:3])
            if len(goals) > 3:
                goals_text += f" 等{len(goals)}项"
            goals_label = QLabel(f"目标: {goals_text}")
            goals_label.setObjectName("milestone_desc")
            goals_label.setWordWrap(True)
            content_layout.addWidget(goals_label)

        # 关键交付物
        deliverables = milestone.get('key_deliverables', [])
        if deliverables:
            deliverables_text = "、".join(deliverables[:3])
            if len(deliverables) > 3:
                deliverables_text += f" 等{len(deliverables)}项"
            del_label = QLabel(f"交付物: {deliverables_text}")
            del_label.setObjectName("milestone_deliverables")
            del_label.setWordWrap(True)
            content_layout.addWidget(del_label)

        layout.addLayout(content_layout, 1)

        return widget

    def _format_priority(self, priority: str) -> str:
        """格式化优先级显示"""
        mapping = {
            'must-have': '必须',
            'should-have': '应该',
            'nice-to-have': '可选',
            'must_have': '必须',
            'should_have': '应该',
            'nice_to_have': '可选',
        }
        return mapping.get(priority.lower(), priority)

    def _format_impact(self, impact: str) -> str:
        """格式化影响程度显示"""
        mapping = {
            'high': '高',
            'medium': '中',
            'low': '低',
        }
        return mapping.get(impact.lower(), impact)

    def _apply_card_style(self, card: QFrame):
        """应用卡片样式"""
        # 获取级别对应的颜色
        high_color = "#E53935"  # 红色
        medium_color = "#FB8C00"  # 橙色
        low_color = "#43A047"  # 绿色

        card.setStyleSheet(f"""
            QFrame#planning_card {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#card_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                font-weight: 600;
            }}
            QLabel#empty_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                font-style: italic;
                padding: {dp(8)}px 0;
            }}
            QLabel#grid_header {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-weight: 600;
                padding: {dp(4)}px;
                background-color: {theme_manager.book_bg_primary()};
                border-radius: {dp(4)}px;
            }}
            QLabel#grid_cell {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
                padding: {dp(6)}px {dp(4)}px;
            }}
            QLabel#field_title {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QLabel#field_value {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
            }}
            QLabel#priority_label, QLabel#impact_label, QLabel#level_label {{
                font-size: {dp(12)}px;
                font-weight: 500;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
            }}
            QLabel#priority_label[level="must_have"],
            QLabel#impact_label[level="high"],
            QLabel#level_label[level="high"] {{
                color: white;
                background-color: {high_color};
            }}
            QLabel#priority_label[level="should_have"],
            QLabel#impact_label[level="medium"],
            QLabel#level_label[level="medium"] {{
                color: white;
                background-color: {medium_color};
            }}
            QLabel#priority_label[level="nice_to_have"],
            QLabel#impact_label[level="low"],
            QLabel#level_label[level="low"] {{
                color: white;
                background-color: {low_color};
            }}
            QFrame#milestone_item {{
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                margin-bottom: {dp(4)}px;
            }}
            QLabel#milestone_index {{
                color: white;
                background-color: {theme_manager.PRIMARY};
                font-size: {dp(12)}px;
                font-weight: bold;
                border-radius: {dp(4)}px;
            }}
            QLabel#milestone_name {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
                font-weight: 500;
            }}
            QLabel#milestone_desc {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
            QLabel#milestone_deliverables {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
            }}
        """)

    def _apply_scroll_style(self, scroll: QScrollArea):
        """应用滚动区域样式"""
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(8)}px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        for card in [
            self.requirements_card,
            self.challenges_card,
            self.nfr_card,
            self.risks_card,
            self.milestones_card
        ]:
            if card:
                self._apply_card_style(card)

    def updateData(self, data: Dict[str, Any]):
        """更新数据 - 需要重建UI"""
        super().updateData(data)
        # 由于包含复杂列表，简单重建UI
        # 实际项目中可以做更精细的增量更新


__all__ = ["ProjectPlanningSection"]
