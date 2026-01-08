"""
分析面板构建器 - 章节分析Tab的UI构建逻辑

从 WDWorkspace 中提取，负责创建章节分析Tab的所有UI组件。
包含角色状态、伏笔追踪、关键事件等结构化信息的展示。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from components.empty_state import EmptyStateWithIllustration
from components.flow_layout import FlowLayout
from utils.dpi_utils import dp, sp
from .base import BasePanelBuilder


class AnalysisPanelBuilder(BasePanelBuilder):
    """分析面板构建器

    职责：创建章节分析Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中
    继承自 BasePanelBuilder，使用缓存的 styler 属性减少 theme_manager 调用。
    """

    def __init__(self):
        """初始化构建器"""
        super().__init__()  # 初始化 BasePanelBuilder，获取 _styler

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_analysis_tab(data)

    def create_analysis_tab(self, chapter_data: dict) -> QWidget:
        """创建章节分析标签页 - 展示结构化分析数据

        Args:
            chapter_data: 章节数据，包含 analysis_data 字段

        Returns:
            分析Tab的根Widget
        """
        s = self._styler  # 使用缓存的样式器属性

        analysis_data = chapter_data.get('analysis_data')

        # 如果没有分析数据，显示空状态
        if not analysis_data:
            return self._create_panel_empty_state()

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("analysis_scroll_area")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {s.scrollbar_style()}
        """)

        # 创建内容容器
        container = QWidget()
        container.setObjectName("analysis_container")
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(16))

        # 说明卡片
        info_card = self._create_info_card()
        layout.addWidget(info_card)

        # 1. 分级摘要区域
        summaries = analysis_data.get('summaries')
        if summaries:
            summaries_section = self._create_summaries_section(summaries)
            layout.addWidget(summaries_section)

        # 2. 元数据区域（角色、地点、物品、标签等）
        metadata = analysis_data.get('metadata')
        if metadata:
            metadata_section = self._create_metadata_section(metadata)
            layout.addWidget(metadata_section)

        # 3. 角色状态区域
        character_states = analysis_data.get('character_states')
        if character_states:
            char_section = self._create_character_states_section(character_states)
            layout.addWidget(char_section)

        # 4. 关键事件区域
        key_events = analysis_data.get('key_events')
        if key_events:
            events_section = self._create_key_events_section(key_events)
            layout.addWidget(events_section)

        # 5. 伏笔追踪区域
        foreshadowing = analysis_data.get('foreshadowing')
        if foreshadowing:
            foreshadow_section = self._create_foreshadowing_section(foreshadowing)
            layout.addWidget(foreshadow_section)

        # 添加底部弹性空间
        layout.addStretch()

        scroll_area.setWidget(container)
        return scroll_area

    def _create_panel_empty_state(self) -> QWidget:
        """创建空状态Widget"""
        s = self._styler

        empty_widget = QWidget()
        empty_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(dp(32), dp(32), dp(32), dp(32))
        empty_layout.setSpacing(dp(24))

        empty_state = EmptyStateWithIllustration(
            illustration_char='A',
            title='暂无章节分析',
            description='选择版本后系统会自动分析章节内容，提取角色状态、伏笔、关键事件等结构化信息',
            parent=empty_widget
        )
        empty_layout.addWidget(empty_state)

        return empty_widget

    def _create_info_card(self) -> QFrame:
        """创建分析说明卡片"""
        s = self._styler

        info_card = QFrame()
        info_card.setObjectName("analysis_info_card")
        info_card.setStyleSheet(f"""
            QFrame#analysis_info_card {{
                background-color: {s.info_bg};
                border: 1px solid {s.info};
                border-left: 4px solid {s.info};
                border-radius: {dp(4)}px;
                padding: {dp(12)}px;
            }}
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        info_layout.setSpacing(dp(4))

        info_title = QLabel("章节深度分析")
        info_title.setObjectName("analysis_info_title")
        info_title.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {s.text_info};
        """)
        info_layout.addWidget(info_title)

        info_desc = QLabel("AI自动提取的结构化信息，包括角色状态、伏笔追踪、关键事件等，用于确保后续章节的连贯性。")
        info_desc.setObjectName("analysis_info_desc")
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        info_layout.addWidget(info_desc)

        return info_card

    def _create_section_card(self, title: str, icon_char: str, section_id: str = None):
        """创建通用分区卡片

        Args:
            title: 分区标题
            icon_char: 图标字符
            section_id: 分区ID（用于objectName）

        Returns:
            (card, layout) 元组
        """
        s = self._styler
        card_id = section_id or title.lower().replace(" ", "_")

        card = QFrame()
        card.setObjectName(f"analysis_section_{card_id}")
        card.setStyleSheet(f"""
            QFrame#analysis_section_{card_id} {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon_label = QLabel(icon_char)
        icon_label.setObjectName(f"section_icon_{card_id}")
        icon_label.setStyleSheet(f"""
            font-size: {sp(16)}px;
            color: {s.accent_color};
        """)
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName(f"section_title_{card_id}")
        title_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(14)}px;
            font-weight: 600;
            color: {s.text_primary};
        """)
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)

        return card, layout

    def _create_tag_widget(self, text: str, tag_type: str = "default") -> QLabel:
        """创建标签/徽章组件

        Args:
            text: 标签文本
            tag_type: 标签类型 (default/character/location/item/keyword/tag)
        """
        s = self._styler

        # 截断过长的文本
        display_text = text if len(text) <= 20 else text[:18] + "..."
        tag = QLabel(display_text)
        if len(text) > 20:
            tag.setToolTip(text)  # 完整文本显示在tooltip

        # 根据类型选择边框颜色
        type_colors = {
            "character": s.success,
            "location": s.info,
            "item": s.warning,
            "keyword": s.accent_color,
            "tag": s.primary,
            "default": s.border_color,
        }

        tag_border = type_colors.get(tag_type, s.border_color)

        tag.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
            background-color: transparent;
            border: 1px solid {tag_border};
            border-radius: {dp(4)}px;
            padding: {dp(4)}px {dp(8)}px;
        """)
        return tag

    def _create_flow_layout(self, items: list, tag_type: str = "default") -> QWidget:
        """创建流式布局的标签组（自动换行）

        Args:
            items: 标签文本列表
            tag_type: 标签类型
        """
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = FlowLayout(spacing=dp(6))
        container.setLayout(layout)

        max_items = 10
        for item in items[:max_items]:
            tag = self._create_tag_widget(str(item), tag_type)
            layout.addWidget(tag)

        if len(items) > max_items:
            more_tag = self._create_tag_widget(f"+{len(items) - max_items}", "default")
            layout.addWidget(more_tag)

        return container

    def _create_summaries_section(self, summaries: dict) -> QFrame:
        """创建分级摘要区域"""
        s = self._styler
        card, layout = self._create_section_card("分级摘要", "[S]", section_id="summaries")

        # 一句话概括
        one_line = summaries.get('one_line', '')
        if one_line:
            one_line_label = QLabel("一句话概括")
            one_line_label.setObjectName("analysis_label_one_line")
            one_line_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {s.text_secondary};
            """)
            layout.addWidget(one_line_label)

            one_line_text = QLabel(one_line)
            one_line_text.setObjectName("analysis_highlight_one_line")
            one_line_text.setWordWrap(True)
            one_line_text.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(14)}px;
                color: {s.accent_color};
                font-weight: 500;
                padding: {dp(10)}px;
                background-color: transparent;
                border: 1px solid {s.accent_color};
                border-left: 3px solid {s.accent_color};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(one_line_text)

        # 压缩摘要
        compressed = summaries.get('compressed', '')
        if compressed:
            compressed_label = QLabel("压缩摘要")
            compressed_label.setObjectName("analysis_label_compressed")
            compressed_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {s.text_secondary};
                margin-top: {dp(8)}px;
                background-color: transparent;
            """)
            layout.addWidget(compressed_label)

            compressed_text = QLabel(compressed)
            compressed_text.setObjectName("analysis_text_compressed")
            compressed_text.setWordWrap(True)
            compressed_text.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(13)}px;
                color: {s.text_primary};
                line-height: 1.6;
                background-color: transparent;
            """)
            layout.addWidget(compressed_text)

        # 关键词
        keywords = summaries.get('keywords', [])
        if keywords:
            keywords_label = QLabel("关键词")
            keywords_label.setObjectName("analysis_label_keywords")
            keywords_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                font-weight: 600;
                color: {s.text_secondary};
                margin-top: {dp(8)}px;
                background-color: transparent;
            """)
            layout.addWidget(keywords_label)

            keywords_flow = self._create_flow_layout(keywords, "keyword")
            layout.addWidget(keywords_flow)

        return card

    def _create_metadata_section(self, metadata: dict) -> QFrame:
        """创建元数据区域"""
        s = self._styler
        card, layout = self._create_section_card("章节元素", "[M]", section_id="metadata")

        # 情感基调和时间标记（横向排列）
        meta_row = QHBoxLayout()
        meta_row.setSpacing(dp(16))

        tone = metadata.get('tone', '')
        if tone:
            tone_widget = self._create_meta_item("情感基调", tone, s.text_tertiary, s.text_warning)
            meta_row.addWidget(tone_widget)

        timeline = metadata.get('timeline_marker', '')
        if timeline:
            timeline_widget = self._create_meta_item("时间标记", timeline, s.text_tertiary, s.text_info)
            meta_row.addWidget(timeline_widget)

        meta_row.addStretch()
        if tone or timeline:
            layout.addLayout(meta_row)

        # 出场角色
        characters = metadata.get('characters', [])
        if characters:
            self._add_tag_section(layout, "出场角色", characters, "character")

        # 场景地点
        locations = metadata.get('locations', [])
        if locations:
            self._add_tag_section(layout, "场景地点", locations, "location", margin_top=True)

        # 重要物品
        items = metadata.get('items', [])
        if items:
            self._add_tag_section(layout, "重要物品", items, "item", margin_top=True)

        # 章节标签
        tags = metadata.get('tags', [])
        if tags:
            self._add_tag_section(layout, "章节类型", tags, "tag", margin_top=True)

        return card

    def _create_meta_item(self, label: str, value: str, label_color: str, value_color: str) -> QWidget:
        """创建元数据项"""
        s = self._styler

        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(11)}px;
            color: {label_color};
            background-color: transparent;
        """)
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(13)}px;
            font-weight: 600;
            color: {value_color};
            background-color: transparent;
        """)
        layout.addWidget(value_widget)

        return widget

    def _add_tag_section(self, layout: QVBoxLayout, title: str, items: list, tag_type: str,
                         margin_top: bool = False):
        """添加标签分区"""
        s = self._styler

        label = QLabel(title)
        label.setObjectName(f"analysis_label_{tag_type}")
        style = f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {s.text_secondary};
            background-color: transparent;
        """
        if margin_top:
            style += f"margin-top: {dp(8)}px;"
        label.setStyleSheet(style)
        layout.addWidget(label)

        flow = self._create_flow_layout(items, tag_type)
        layout.addWidget(flow)

    def _create_character_states_section(self, character_states: dict) -> QFrame:
        """创建角色状态区域"""
        s = self._styler
        card, layout = self._create_section_card("角色状态快照", "[C]", section_id="character_states")

        char_index = 0
        for char_name, state in character_states.items():
            if not isinstance(state, dict):
                continue

            char_card = QFrame()
            char_card.setObjectName(f"char_state_card_{char_index}")
            char_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(6)}px;
                    padding: {dp(10)}px;
                }}
            """)
            char_layout = QVBoxLayout(char_card)
            char_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
            char_layout.setSpacing(dp(6))

            # 角色名
            name_label = QLabel(char_name)
            name_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                font-weight: 700;
                color: {s.accent_color};
                background-color: transparent;
            """)
            char_layout.addWidget(name_label)

            # 位置和状态
            details = []
            if state.get('location'):
                details.append(f"位置: {state['location']}")
            if state.get('status'):
                details.append(f"状态: {state['status']}")

            if details:
                details_label = QLabel(" | ".join(details))
                details_label.setWordWrap(True)
                details_label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(12)}px;
                    color: {s.text_secondary};
                    background-color: transparent;
                """)
                char_layout.addWidget(details_label)

            # 变化
            changes = state.get('changes', [])
            if changes:
                changes_label = QLabel("本章变化:")
                changes_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_tertiary};
                    margin-top: {dp(4)}px;
                    background-color: transparent;
                """)
                char_layout.addWidget(changes_label)

                for change in changes[:3]:
                    change_item = QLabel(f"  - {change}")
                    change_item.setWordWrap(True)
                    change_item.setStyleSheet(f"""
                        font-family: {s.serif_font};
                        font-size: {sp(12)}px;
                        color: {s.text_success};
                        background-color: transparent;
                    """)
                    char_layout.addWidget(change_item)

            layout.addWidget(char_card)
            char_index += 1

        return card

    def _create_key_events_section(self, key_events: list) -> QFrame:
        """创建关键事件区域"""
        s = self._styler
        card, layout = self._create_section_card("关键事件", "[E]", section_id="key_events")

        event_type_names = {
            'battle': '战斗', 'revelation': '揭示', 'relationship': '关系',
            'discovery': '发现', 'decision': '决策', 'death': '死亡',
            'arrival': '到来', 'departure': '离开',
        }

        importance_border_colors = {
            'high': s.error,
            'medium': s.warning,
            'low': s.border_default,
        }

        importance_text_colors = {
            'high': s.text_error,
            'medium': s.text_warning,
            'low': s.text_tertiary,
        }

        max_events = 5
        event_index = 0
        for event in key_events[:max_events]:
            if not isinstance(event, dict):
                continue

            importance = event.get('importance', 'medium')
            event_card = QFrame()
            event_card.setObjectName(f"event_card_{event_index}")
            event_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border-left: 3px solid {importance_border_colors.get(importance, s.warning)};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)
            event_layout = QVBoxLayout(event_card)
            event_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            event_layout.setSpacing(dp(4))

            # 事件类型和重要性
            header_row = QHBoxLayout()
            header_row.setSpacing(dp(8))

            event_type = event.get('type', '')
            type_text = event_type_names.get(event_type, event_type)
            type_label = QLabel(f"[{type_text}]")
            type_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                font-weight: 600;
                color: {s.accent_color};
            """)
            header_row.addWidget(type_label)

            imp_text = {'high': '重要', 'medium': '一般', 'low': '次要'}.get(importance, importance)
            imp_label = QLabel(imp_text)
            imp_text_color = importance_text_colors.get(importance, s.text_tertiary)
            imp_border_color = importance_border_colors.get(importance, s.border_default)
            imp_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {imp_text_color};
                background-color: {imp_border_color}15;
                border-radius: {dp(2)}px;
                padding: {dp(2)}px {dp(6)}px;
            """)
            header_row.addWidget(imp_label)
            header_row.addStretch()

            event_layout.addLayout(header_row)

            # 事件描述
            description = event.get('description', '')
            if description:
                desc_label = QLabel(description)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(13)}px;
                    color: {s.text_primary};
                """)
                event_layout.addWidget(desc_label)

            # 涉及角色
            involved = event.get('involved_characters', [])
            if involved:
                involved_text = "涉及: " + ", ".join(involved[:4])
                if len(involved) > 4:
                    involved_text += f" 等{len(involved)}人"
                involved_label = QLabel(involved_text)
                involved_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_tertiary};
                """)
                event_layout.addWidget(involved_label)

            layout.addWidget(event_card)
            event_index += 1

        return card

    def _create_foreshadowing_section(self, foreshadowing: dict) -> QFrame:
        """创建伏笔追踪区域"""
        s = self._styler
        card, layout = self._create_section_card("伏笔追踪", "[F]", section_id="foreshadowing")

        # 埋下的伏笔
        planted = foreshadowing.get('planted', [])
        if planted:
            self._add_planted_foreshadowing(layout, planted)

        # 回收的伏笔
        resolved = foreshadowing.get('resolved', [])
        if resolved:
            self._add_resolved_foreshadowing(layout, resolved)

        # 未解决的悬念
        tensions = foreshadowing.get('tensions', [])
        if tensions:
            self._add_tensions(layout, tensions)

        return card

    def _add_planted_foreshadowing(self, layout: QVBoxLayout, planted: list):
        """添加埋下的伏笔"""
        s = self._styler

        planted_label = QLabel("本章埋下的伏笔")
        planted_label.setObjectName("analysis_label_planted")
        planted_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {s.text_warning};
        """)
        layout.addWidget(planted_label)

        is_light = theme_manager.is_light_mode()
        priority_border_colors = {
            'high': theme_manager.ERROR_DARK if is_light else s.error,
            'medium': theme_manager.WARNING_DARK if is_light else s.warning,
            'low': theme_manager.BORDER_DARK if is_light else s.border_default,
        }
        foreshadow_bg = s.warning_bg if is_light else f"{s.warning}15"

        max_items = 5
        fs_index = 0
        for item in planted[:max_items]:
            if not isinstance(item, dict):
                continue

            foreshadow_card = QFrame()
            foreshadow_card.setObjectName(f"foreshadow_card_{fs_index}")
            priority = item.get('priority', 'medium')
            foreshadow_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {foreshadow_bg};
                    border-left: 3px solid {priority_border_colors.get(priority, theme_manager.WARNING_DARK)};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)
            fs_layout = QVBoxLayout(foreshadow_card)
            fs_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            fs_layout.setSpacing(dp(4))

            # 描述
            desc = item.get('description', '')
            if desc:
                desc_label = QLabel(desc)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(13)}px;
                    color: {s.text_primary};
                """)
                fs_layout.addWidget(desc_label)

            # 原文引用
            original = item.get('original_text', '')
            if original:
                orig_label = QLabel(f'"{original}"')
                orig_label.setWordWrap(True)
                orig_label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(12)}px;
                    font-style: italic;
                    color: {s.text_secondary};
                """)
                fs_layout.addWidget(orig_label)

            layout.addWidget(foreshadow_card)
            fs_index += 1

    def _add_resolved_foreshadowing(self, layout: QVBoxLayout, resolved: list):
        """添加回收的伏笔"""
        s = self._styler

        resolved_label = QLabel("本章回收的伏笔")
        resolved_label.setObjectName("analysis_label_resolved")
        resolved_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {s.text_success};
            margin-top: {dp(12)}px;
        """)
        layout.addWidget(resolved_label)

        for item in resolved[:3]:
            if isinstance(item, dict):
                resolution = item.get('resolution', str(item))
            else:
                resolution = str(item)

            res_label = QLabel(f"  - {resolution}")
            res_label.setWordWrap(True)
            res_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {s.text_success};
            """)
            layout.addWidget(res_label)

    def _add_tensions(self, layout: QVBoxLayout, tensions: list):
        """添加未解决的悬念"""
        s = self._styler

        tensions_label = QLabel("未解决的悬念")
        tensions_label.setObjectName("analysis_label_tensions")
        tensions_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {s.text_error};
            margin-top: {dp(12)}px;
        """)
        layout.addWidget(tensions_label)

        for tension in tensions[:3]:
            tension_label = QLabel(f"  ? {tension}")
            tension_label.setWordWrap(True)
            tension_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {s.text_error};
            """)
            layout.addWidget(tension_label)
