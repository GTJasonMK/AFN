"""
编程项目概览Section - 增强版

显示：
- 项目进度指示器
- 项目摘要卡片
- 技术栈信息
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget,
    QGridLayout, QProgressBar
)
from PyQt6.QtCore import Qt

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

logger = logging.getLogger(__name__)


# 工作流程步骤定义（两层结构：系统 -> 模块）
WORKFLOW_STEPS = [
    {'id': 'blueprint', 'label': '蓝图', 'key': 'has_blueprint'},
    {'id': 'systems', 'label': '系统', 'key': 'systems'},
    {'id': 'modules', 'label': '模块', 'key': 'modules'},
    {'id': 'directory', 'label': '目录', 'key': 'directory_tree'},
    {'id': 'prompts', 'label': 'Prompt', 'key': 'generated_count'},
]


class CodingOverviewSection(BaseSection):
    """编程项目概览Section - 增强版

    展示：
    - 项目进度指示器（工作流程步骤）
    - 项目摘要卡片
    - 技术栈信息
    """

    def __init__(self, data: Dict[str, Any] = None, editable: bool = True, project_id: str = None, parent=None):
        self.project_id = project_id
        super().__init__(data, editable, parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = self._create_scroll_container_layout(spacing=dp(20))

        # 1. 项目进度Section
        self.progress_section = self._create_progress_section()
        layout.addWidget(self.progress_section)

        # 2. 项目摘要Section
        self.summary_section = self._create_summary_section()
        layout.addWidget(self.summary_section)

        # 3. 技术栈Section
        tech_stack = self._data.get('tech_stack', {}) if self._data else {}
        self.tech_stack_section = self._create_tech_stack_section(tech_stack)
        layout.addWidget(self.tech_stack_section)

        layout.addStretch()

    def _create_progress_section(self) -> QFrame:
        """创建项目进度Section"""
        section = QFrame()
        section.setObjectName("progress_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(16))

        # 标题行
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("项目进度")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 计算完成百分比
        progress_percent = self._calculate_progress()
        self.progress_percent_label = QLabel(f"{progress_percent}%")
        self.progress_percent_label.setObjectName("progress_percent")
        header_layout.addWidget(self.progress_percent_label)

        layout.addWidget(header)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("workflow_progress")
        self.progress_bar.setFixedHeight(dp(8))
        self.progress_bar.setValue(progress_percent)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 步骤指示器
        steps_widget = QWidget()
        steps_layout = QHBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, dp(8), 0, 0)
        steps_layout.setSpacing(dp(4))

        self._step_labels = []
        for i, step in enumerate(WORKFLOW_STEPS):
            step_widget = self._create_step_indicator(step, i)
            steps_layout.addWidget(step_widget, 1)
            if i < len(WORKFLOW_STEPS) - 1:
                # 连接线
                connector = QLabel("--")
                connector.setObjectName("step_connector")
                connector.setAlignment(Qt.AlignmentFlag.AlignCenter)
                steps_layout.addWidget(connector)

        layout.addWidget(steps_widget)

        self._apply_progress_style(section)
        return section

    def _create_step_indicator(self, step: dict, index: int) -> QWidget:
        """创建单个步骤指示器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 判断步骤是否完成
        is_completed = self._is_step_completed(step['key'])

        # 步骤图标/数字
        icon_label = QLabel(str(index + 1))
        icon_label.setObjectName("step_icon_completed" if is_completed else "step_icon_pending")
        icon_label.setFixedSize(dp(24), dp(24))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 步骤标签
        label = QLabel(step['label'])
        label.setObjectName("step_label_completed" if is_completed else "step_label_pending")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self._step_labels.append((icon_label, label, step['key']))

        return widget

    def _is_step_completed(self, key: str) -> bool:
        """判断步骤是否完成"""
        if not self._data:
            return False

        if key == 'has_blueprint':
            # 检查蓝图是否存在
            return bool(self._data.get('one_sentence_summary') or self._data.get('architecture_synopsis'))
        elif key in ['systems', 'modules']:
            # 检查列表是否非空
            items = self._data.get(key, [])
            return len(items) > 0
        elif key == 'directory_tree':
            # 检查目录树是否存在
            return bool(self._data.get('directory_tree'))
        elif key == 'generated_count':
            # 检查是否有已生成内容
            return self._data.get('generated_count', 0) > 0

        return False

    def _calculate_progress(self) -> int:
        """计算项目进度百分比"""
        if not self._data:
            return 0

        completed = 0
        for step in WORKFLOW_STEPS:
            if self._is_step_completed(step['key']):
                completed += 1

        return int((completed / len(WORKFLOW_STEPS)) * 100)

    def _create_summary_section(self) -> QFrame:
        """创建项目摘要Section"""
        section = QFrame()
        section.setObjectName("summary_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 标题行
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("项目摘要")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        header_layout.addStretch()
        layout.addWidget(header)

        # 一句话摘要
        summary = self._data.get('one_sentence_summary', '') if self._data else ''
        self.summary_label = QLabel(summary or "暂无摘要，请先生成蓝图")
        self.summary_label.setObjectName("summary_text")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # 信息网格
        info_grid = QWidget()
        grid_layout = QGridLayout(info_grid)
        grid_layout.setContentsMargins(0, dp(8), 0, 0)
        grid_layout.setSpacing(dp(12))

        # 项目类型
        self.type_label = self._create_info_item(
            "项目类型",
            self._data.get('project_type_desc', '未定义') if self._data else '未定义'
        )
        grid_layout.addWidget(self.type_label, 0, 0)

        # 目标受众
        self.audience_label = self._create_info_item(
            "目标受众",
            self._data.get('target_audience', '未定义') if self._data else '未定义'
        )
        grid_layout.addWidget(self.audience_label, 0, 1)

        # 技术风格
        self.style_label = self._create_info_item(
            "技术风格",
            self._data.get('tech_style', '未定义') if self._data else '未定义'
        )
        grid_layout.addWidget(self.style_label, 1, 0)

        # 项目调性
        self.tone_label = self._create_info_item(
            "项目调性",
            self._data.get('project_tone', '未定义') if self._data else '未定义'
        )
        grid_layout.addWidget(self.tone_label, 1, 1)

        layout.addWidget(info_grid)

        # 架构概述
        synopsis = self._data.get('architecture_synopsis', '') if self._data else ''
        if synopsis:
            synopsis_title = QLabel("架构概述")
            synopsis_title.setObjectName("info_label")
            layout.addWidget(synopsis_title)

            self.synopsis_label = QLabel(synopsis)
            self.synopsis_label.setObjectName("synopsis_text")
            self.synopsis_label.setWordWrap(True)
            layout.addWidget(self.synopsis_label)

        self._apply_summary_style(section)
        return section

    def _create_info_item(self, label: str, value: str) -> QWidget:
        """创建信息项"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        label_widget = QLabel(label)
        label_widget.setObjectName("info_label")
        layout.addWidget(label_widget)

        value_widget = QLabel(value or "未定义")
        value_widget.setObjectName("info_value")
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget)

        # 保存引用用于更新
        widget.value_label = value_widget

        return widget

    def _create_tech_stack_section(self, tech_stack: dict) -> QFrame:
        """创建技术栈Section"""
        section = QFrame()
        section.setObjectName("tech_stack_section")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 标题
        title = QLabel("技术栈")
        title.setObjectName("section_title")
        layout.addWidget(title)

        if not tech_stack:
            empty_label = QLabel("暂无技术栈信息，请先生成蓝图")
            empty_label.setObjectName("empty_text")
            layout.addWidget(empty_label)
        else:
            # 核心约束
            core_constraints = tech_stack.get('core_constraints', '')
            if core_constraints:
                constraints_label = QLabel(f"核心约束: {core_constraints}")
                constraints_label.setObjectName("constraints_text")
                constraints_label.setWordWrap(True)
                layout.addWidget(constraints_label)

            # 技术组件标签
            components = tech_stack.get('components', [])
            if components:
                tags_widget = QWidget()
                tags_layout = QHBoxLayout(tags_widget)
                tags_layout.setContentsMargins(0, 0, 0, 0)
                tags_layout.setSpacing(dp(8))

                for comp in components[:8]:
                    name = comp.get('name', '') if isinstance(comp, dict) else str(comp)
                    desc = comp.get('description', '') if isinstance(comp, dict) else ''

                    tag = QLabel(name)
                    tag.setObjectName("tech_tag")
                    if desc:
                        tag.setToolTip(desc)
                    tags_layout.addWidget(tag)

                if len(components) > 8:
                    more = QLabel(f"+{len(components) - 8}")
                    more.setObjectName("tech_tag_more")
                    tags_layout.addWidget(more)

                tags_layout.addStretch()
                layout.addWidget(tags_widget)

        self._apply_tech_stack_style(section)
        return section

    # ========== 样式方法 ==========

    def _apply_progress_style(self, section: QFrame):
        """应用进度样式"""
        section.setStyleSheet(f"""
            QFrame#progress_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QLabel#progress_percent {{
                color: {theme_manager.PRIMARY};
                font-size: {sp(16)}px;
                font-weight: bold;
            }}
            QProgressBar#workflow_progress {{
                background-color: {theme_manager.BORDER_DEFAULT};
                border: none;
                border-radius: {dp(4)}px;
            }}
            QProgressBar#workflow_progress::chunk {{
                background-color: {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
            }}
            QLabel#step_connector {{
                color: {theme_manager.BORDER_DEFAULT};
                font-size: {sp(10)}px;
            }}
            QLabel#step_icon_completed {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                font-size: {sp(11)}px;
                font-weight: bold;
                border-radius: {dp(12)}px;
            }}
            QLabel#step_icon_pending {{
                background-color: {theme_manager.BORDER_DEFAULT};
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(11)}px;
                font-weight: bold;
                border-radius: {dp(12)}px;
            }}
            QLabel#step_label_completed {{
                color: {theme_manager.SUCCESS};
                font-size: {sp(11)}px;
            }}
            QLabel#step_label_pending {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(11)}px;
            }}
        """)

    def _apply_summary_style(self, section: QFrame):
        """应用摘要样式"""
        section.setStyleSheet(f"""
            QFrame#summary_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QLabel#summary_text {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(14)}px;
                line-height: 1.5;
            }}
            QLabel#info_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(11)}px;
            }}
            QLabel#info_value {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(13)}px;
            }}
            QLabel#synopsis_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(13)}px;
                line-height: 1.5;
            }}
        """)

    def _apply_tech_stack_style(self, section: QFrame):
        """应用技术栈样式"""
        section.setStyleSheet(f"""
            QFrame#tech_stack_section {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(15)}px;
                font-weight: 600;
            }}
            QLabel#empty_text {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(13)}px;
            }}
            QLabel#constraints_text {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(13)}px;
            }}
            QLabel#tech_tag {{
                background-color: {theme_manager.PRIMARY}15;
                color: {theme_manager.PRIMARY};
                font-size: {sp(12)}px;
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                border: 1px solid {theme_manager.PRIMARY}30;
            }}
            QLabel#tech_tag_more {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {sp(11)}px;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        if hasattr(self, 'progress_section'):
            self._apply_progress_style(self.progress_section)
        if hasattr(self, 'summary_section'):
            self._apply_summary_style(self.summary_section)
        if hasattr(self, 'tech_stack_section'):
            self._apply_tech_stack_style(self.tech_stack_section)

    def updateData(self, data: Dict[str, Any]):
        """更新数据"""
        super().updateData(data)

        # 更新进度
        progress_percent = self._calculate_progress()
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(progress_percent)
        if hasattr(self, 'progress_percent_label'):
            self.progress_percent_label.setText(f"{progress_percent}%")

        # 更新步骤状态
        if hasattr(self, '_step_labels'):
            for icon_label, text_label, key in self._step_labels:
                is_completed = self._is_step_completed(key)
                icon_label.setObjectName("step_icon_completed" if is_completed else "step_icon_pending")
                text_label.setObjectName("step_label_completed" if is_completed else "step_label_pending")
            # 重新应用样式
            if hasattr(self, 'progress_section'):
                self._apply_progress_style(self.progress_section)

        # 更新摘要
        if hasattr(self, 'summary_label'):
            self.summary_label.setText(
                data.get('one_sentence_summary', '') or "暂无摘要，请先生成蓝图"
            )

        # 更新信息项
        if hasattr(self, 'type_label') and hasattr(self.type_label, 'value_label'):
            self.type_label.value_label.setText(data.get('project_type_desc', '未定义') or '未定义')
        if hasattr(self, 'audience_label') and hasattr(self.audience_label, 'value_label'):
            self.audience_label.value_label.setText(data.get('target_audience', '未定义') or '未定义')
        if hasattr(self, 'style_label') and hasattr(self.style_label, 'value_label'):
            self.style_label.value_label.setText(data.get('tech_style', '未定义') or '未定义')
        if hasattr(self, 'tone_label') and hasattr(self.tone_label, 'value_label'):
            self.tone_label.value_label.setText(data.get('project_tone', '未定义') or '未定义')

        # 架构概述
        if hasattr(self, 'synopsis_label'):
            self.synopsis_label.setText(data.get('architecture_synopsis', '') or '')


__all__ = ["CodingOverviewSection"]
