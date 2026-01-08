"""
漫画详细信息Tab

显示漫画分镜生成过程中的详细分析结果：
- 角色分析：角色外观、性格、关系
- 事件列表：事件类型、参与者、重要性
- 对话提取：对话内容、说话人、情绪
- 场景信息：地点、时间、氛围
- 情绪曲线：章节情绪变化轨迹
- 页面规划：节奏分配、高潮页码
"""

from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QGridLayout, QGroupBox,
)
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class DetailsTabMixin:
    """详细信息Tab的Mixin"""

    def _create_details_tab(self, manga_data: dict) -> QWidget:
        """创建详细信息标签页

        Args:
            manga_data: 漫画数据，包含 analysis_data 字段

        Returns:
            详细信息Tab的Widget
        """
        s = self._styler

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                width: {dp(8)}px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {s.border_light};
                border-radius: {dp(4)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {s.text_secondary};
            }}
        """)

        # 滚动区域内容
        content_widget = QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                color: {s.text_primary};
            }}
        """)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(16))

        # 获取分析数据
        analysis_data = manga_data.get('analysis_data')

        if not analysis_data:
            # 无分析数据时显示提示
            empty_label = QLabel("暂无详细信息\n\n重新生成漫画分镜后将显示分析结果")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                color: {s.text_secondary};
                padding: {dp(40)}px;
            """)
            layout.addWidget(empty_label)
            layout.addStretch()
        else:
            # 解析分析数据
            chapter_info = analysis_data.get('chapter_info', {})
            page_plan = analysis_data.get('page_plan', {})

            # 1. 章节概述
            if chapter_info:
                summary_group = self._create_summary_section(chapter_info)
                layout.addWidget(summary_group)

            # 2. 角色信息
            characters = chapter_info.get('characters', {})
            if characters:
                char_group = self._create_characters_section(characters)
                layout.addWidget(char_group)

            # 3. 事件列表
            events = chapter_info.get('events', [])
            if events:
                events_group = self._create_events_section(events)
                layout.addWidget(events_group)

            # 4. 场景信息
            scenes = chapter_info.get('scenes', [])
            if scenes:
                scenes_group = self._create_scenes_section(scenes)
                layout.addWidget(scenes_group)

            # 5. 情绪曲线
            mood_progression = chapter_info.get('mood_progression', [])
            if mood_progression:
                mood_group = self._create_mood_section(mood_progression)
                layout.addWidget(mood_group)

            # 6. 页面规划
            if page_plan:
                plan_group = self._create_page_plan_section(page_plan)
                layout.addWidget(plan_group)

            layout.addStretch()

        scroll_area.setWidget(content_widget)
        return scroll_area

    def _create_group_box(self, title: str) -> QGroupBox:
        """创建统一样式的分组框"""
        s = self._styler

        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {s.serif_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_primary};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                margin-top: {dp(12)}px;
                padding-top: {dp(8)}px;
                background: {s.bg_secondary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {dp(12)}px;
                padding: 0 {dp(4)}px;
            }}
        """)
        return group

    def _create_summary_section(self, chapter_info: dict) -> QGroupBox:
        """创建章节概述区域"""
        s = self._styler

        group = self._create_group_box("章节概述")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 章节摘要
        summary = chapter_info.get('chapter_summary', '')
        if summary:
            summary_label = QLabel(summary)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(13)}px;
                color: {s.text_primary};
                line-height: 1.6;
            """)
            layout.addWidget(summary_label)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(dp(24))

        stats = [
            ("角色", len(chapter_info.get('characters', {}))),
            ("事件", len(chapter_info.get('events', []))),
            ("对话", len(chapter_info.get('dialogues', []))),
            ("场景", len(chapter_info.get('scenes', []))),
            ("物品", len(chapter_info.get('items', []))),
        ]

        for label, count in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(dp(2))

            count_label = QLabel(str(count))
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(18)}px;
                font-weight: bold;
                color: {s.accent_color};
            """)
            stat_layout.addWidget(count_label)

            name_label = QLabel(label)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
            """)
            stat_layout.addWidget(name_label)

            stats_layout.addWidget(stat_widget)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        return group

    def _create_characters_section(self, characters: dict) -> QGroupBox:
        """创建角色信息区域"""
        s = self._styler

        group = self._create_group_box(f"角色分析 ({len(characters)})")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(12))

        for name, char in characters.items():
            char_frame = QFrame()
            char_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_primary};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px;
                }}
            """)
            char_layout = QVBoxLayout(char_frame)
            char_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
            char_layout.setSpacing(dp(4))

            # 角色名和角色定位
            header_layout = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_primary};
            """)
            header_layout.addWidget(name_label)

            role = char.get('role', 'minor')
            role_map = {
                'protagonist': '主角',
                'antagonist': '反派',
                'supporting': '配角',
                'minor': '次要',
                'background': '背景',
            }
            role_text = role_map.get(role, role)
            role_label = QLabel(role_text)
            role_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_secondary};
                background: {s.border_light};
                padding: {dp(2)}px {dp(6)}px;
                border-radius: {dp(4)}px;
            """)
            header_layout.addWidget(role_label)
            header_layout.addStretch()
            char_layout.addLayout(header_layout)

            # 外观描述
            appearance_zh = char.get('appearance_zh', '') or char.get('appearance', '')
            if appearance_zh:
                app_label = QLabel(f"外观: {appearance_zh}")
                app_label.setWordWrap(True)
                app_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(12)}px;
                    color: {s.text_secondary};
                """)
                char_layout.addWidget(app_label)

            # 性格
            personality = char.get('personality', '')
            if personality:
                pers_label = QLabel(f"性格: {personality}")
                pers_label.setWordWrap(True)
                pers_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(12)}px;
                    color: {s.text_secondary};
                """)
                char_layout.addWidget(pers_label)

            layout.addWidget(char_frame)

        return group

    def _create_events_section(self, events: List[dict]) -> QGroupBox:
        """创建事件列表区域"""
        s = self._styler

        group = self._create_group_box(f"事件列表 ({len(events)})")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 事件类型翻译
        type_map = {
            'dialogue': '对话',
            'action': '动作',
            'reaction': '反应',
            'transition': '过渡',
            'revelation': '揭示',
            'conflict': '冲突',
            'resolution': '解决',
            'description': '描述',
            'internal': '内心',
        }

        # 重要性颜色
        importance_colors = {
            'critical': s.error,
            'high': s.warning,
            'normal': s.text_primary,
            'low': s.text_secondary,
        }

        for i, event in enumerate(events[:20]):  # 最多显示20个
            event_frame = QFrame()
            event_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_primary};
                    border-left: 3px solid {importance_colors.get(event.get('importance', 'normal'), s.text_primary)};
                    padding: {dp(4)}px {dp(8)}px;
                }}
            """)
            event_layout = QHBoxLayout(event_frame)
            event_layout.setContentsMargins(dp(8), dp(4), dp(8), dp(4))
            event_layout.setSpacing(dp(8))

            # 事件序号
            index_label = QLabel(f"#{event.get('index', i+1)}")
            index_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
                min-width: {dp(30)}px;
            """)
            event_layout.addWidget(index_label)

            # 事件类型
            event_type = type_map.get(event.get('type', 'description'), event.get('type', ''))
            type_label = QLabel(event_type)
            type_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.accent_color};
                background: {s.primary_pale};
                padding: {dp(1)}px {dp(4)}px;
                border-radius: {dp(3)}px;
                min-width: {dp(40)}px;
            """)
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            event_layout.addWidget(type_label)

            # 事件描述
            desc = event.get('description', '')
            desc_label = QLabel(desc[:80] + "..." if len(desc) > 80 else desc)
            desc_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_primary};
            """)
            event_layout.addWidget(desc_label, stretch=1)

            # 高潮标记
            if event.get('is_climax'):
                climax_label = QLabel("高潮")
                climax_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(10)}px;
                    color: white;
                    background: {s.error};
                    padding: {dp(1)}px {dp(4)}px;
                    border-radius: {dp(3)}px;
                """)
                event_layout.addWidget(climax_label)

            layout.addWidget(event_frame)

        if len(events) > 20:
            more_label = QLabel(f"... 还有 {len(events) - 20} 个事件")
            more_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
                padding: {dp(8)}px;
            """)
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(more_label)

        return group

    def _create_scenes_section(self, scenes: List[dict]) -> QGroupBox:
        """创建场景信息区域"""
        s = self._styler

        group = self._create_group_box(f"场景信息 ({len(scenes)})")
        layout = QGridLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(8))

        for i, scene in enumerate(scenes):
            col = i % 2
            row = i // 2

            scene_frame = QFrame()
            scene_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_primary};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px;
                }}
            """)
            scene_layout = QVBoxLayout(scene_frame)
            scene_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
            scene_layout.setSpacing(dp(4))

            # 场景地点
            location = scene.get('location', '未知地点')
            location_label = QLabel(f"#{scene.get('index', i+1)} {location}")
            location_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {s.text_primary};
            """)
            scene_layout.addWidget(location_label)

            # 场景属性
            attrs = []
            time_of_day = scene.get('time_of_day', '')
            if time_of_day:
                time_map = {
                    'morning': '早晨', 'afternoon': '下午', 'evening': '傍晚',
                    'night': '夜晚', 'dawn': '黎明', 'dusk': '黄昏', 'day': '白天'
                }
                attrs.append(time_map.get(time_of_day, time_of_day))

            indoor_outdoor = scene.get('indoor_outdoor', '')
            if indoor_outdoor:
                attrs.append('室内' if indoor_outdoor == 'indoor' else '室外')

            atmosphere = scene.get('atmosphere', '')
            if atmosphere:
                attrs.append(atmosphere)

            if attrs:
                attr_label = QLabel(" | ".join(attrs))
                attr_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_secondary};
                """)
                scene_layout.addWidget(attr_label)

            layout.addWidget(scene_frame, row, col)

        return group

    def _create_mood_section(self, mood_progression: List[str]) -> QGroupBox:
        """创建情绪曲线区域"""
        s = self._styler

        group = self._create_group_box("情绪曲线")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(4))

        for i, mood in enumerate(mood_progression):
            mood_label = QLabel(mood)
            mood_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
                background: {s.primary_pale};
                padding: {dp(4)}px {dp(8)}px;
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(mood_label)

            # 添加箭头（除了最后一个）
            if i < len(mood_progression) - 1:
                arrow_label = QLabel("->")
                arrow_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_secondary};
                """)
                layout.addWidget(arrow_label)

        layout.addStretch()
        return group

    def _create_page_plan_section(self, page_plan: dict) -> QGroupBox:
        """创建页面规划区域"""
        s = self._styler

        total_pages = page_plan.get('total_pages', 0)
        climax_pages = page_plan.get('climax_pages', [])
        pacing_notes = page_plan.get('pacing_notes', '')

        group = self._create_group_box(f"页面规划 ({total_pages}页)")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 节奏说明
        if pacing_notes:
            notes_label = QLabel(pacing_notes)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                font-style: italic;
            """)
            layout.addWidget(notes_label)

        # 高潮页码
        if climax_pages:
            climax_layout = QHBoxLayout()
            climax_title = QLabel("高潮页码:")
            climax_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_primary};
            """)
            climax_layout.addWidget(climax_title)

            for page_num in climax_pages:
                page_label = QLabel(f"P{page_num}")
                page_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: white;
                    background: {s.error};
                    padding: {dp(2)}px {dp(8)}px;
                    border-radius: {dp(4)}px;
                """)
                climax_layout.addWidget(page_label)

            climax_layout.addStretch()
            layout.addLayout(climax_layout)

        # 页面规划列表
        pages = page_plan.get('pages', [])
        if pages:
            pages_grid = QGridLayout()
            pages_grid.setSpacing(dp(8))

            role_map = {
                'opening': '开场',
                'setup': '铺垫',
                'rising': '上升',
                'climax': '高潮',
                'falling': '下降',
                'resolution': '收尾',
                'transition': '过渡',
            }

            pacing_map = {
                'slow': '慢',
                'medium': '中',
                'fast': '快',
                'explosive': '爆发',
            }

            for i, page in enumerate(pages[:12]):  # 最多显示12页
                col = i % 4
                row = i // 4

                page_frame = QFrame()
                role = page.get('role', 'setup')
                is_climax = page.get('page_number') in climax_pages

                bg_color = s.error if is_climax else s.bg_primary
                border_color = s.error if is_climax else s.border_light

                page_frame.setStyleSheet(f"""
                    QFrame {{
                        background: {bg_color if is_climax else s.bg_primary};
                        border: 1px solid {border_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(4)}px;
                    }}
                """)
                page_layout = QVBoxLayout(page_frame)
                page_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
                page_layout.setSpacing(dp(2))

                # 页码
                page_num_label = QLabel(f"P{page.get('page_number', i+1)}")
                page_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                text_color = 'white' if is_climax else s.text_primary
                page_num_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(12)}px;
                    font-weight: bold;
                    color: {text_color};
                """)
                page_layout.addWidget(page_num_label)

                # 角色和节奏
                role_text = role_map.get(role, role)
                pacing = pacing_map.get(page.get('pacing', 'medium'), '')
                info_label = QLabel(f"{role_text}/{pacing}")
                info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                info_color = 'rgba(255,255,255,0.8)' if is_climax else s.text_secondary
                info_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(9)}px;
                    color: {info_color};
                """)
                page_layout.addWidget(info_label)

                pages_grid.addWidget(page_frame, row, col)

            layout.addLayout(pages_grid)

            if len(pages) > 12:
                more_label = QLabel(f"... 还有 {len(pages) - 12} 页")
                more_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_secondary};
                """)
                more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(more_label)

        return group
