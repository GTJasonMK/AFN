"""
漫画详细信息Tab

展示各个生成步骤的提取结果，以可读格式呈现：
- 步骤1：信息提取（角色、事件、对话、场景、物品）
- 步骤2：页面规划（页数分配、事件分布）
"""

import json
from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QTextEdit, QPushButton, QSizePolicy, QGridLayout,
)
from PyQt6.QtCore import Qt

from themes.book_theme_styler import BookThemeStyler
from utils.dpi_utils import dp, sp


class CollapsibleSection(QFrame):
    """可折叠的区域"""

    def __init__(self, title: str, styler: BookThemeStyler = None, parent=None):
        super().__init__(parent)
        self._is_expanded = True
        self._title = title
        self._content_widget = None
        self._toggle_btn = None
        self._styler = styler or BookThemeStyler()
        self._setup_ui()

    def _setup_ui(self):
        s = self._styler
        self.setStyleSheet(f"""
            QFrame {{
                background: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {s.bg_card};
                border: none;
                border-radius: {dp(6)}px {dp(6)}px 0 0;
                padding: {dp(8)}px {dp(12)}px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        header_layout.setSpacing(dp(8))

        # 折叠按钮
        self._toggle_btn = QPushButton("v")
        self._toggle_btn.setFixedSize(dp(20), dp(20))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            }}
            QPushButton:hover {{
                color: {s.accent_color};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self._toggle_btn)

        # 标题
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {s.text_primary};
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addWidget(header)

        # 内容区域
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent; border: none;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(12))
        self._content_layout.setSpacing(dp(8))
        layout.addWidget(self._content_widget)

        # 让header可点击
        header.mousePressEvent = lambda e: self._toggle()

    def _toggle(self):
        self._is_expanded = not self._is_expanded
        self._content_widget.setVisible(self._is_expanded)
        self._toggle_btn.setText("v" if self._is_expanded else ">")

    def add_content(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def set_expanded(self, expanded: bool):
        self._is_expanded = expanded
        self._content_widget.setVisible(expanded)
        self._toggle_btn.setText("v" if expanded else ">")


class DetailsTabMixin:
    """详细信息Tab的Mixin"""

    def _create_details_tab(self, manga_data: dict) -> QWidget:
        """创建详细信息标签页"""
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
        layout.setSpacing(dp(12))

        # 获取分析数据
        analysis_data = manga_data.get('analysis_data')

        if not analysis_data:
            # 无分析数据时显示提示
            empty_label = QLabel("暂无详细信息\n\n生成漫画分镜后将显示各步骤的提取结果")
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

            # ==================== 步骤1：信息提取 ====================
            if chapter_info:
                extraction_section = CollapsibleSection("步骤1: 信息提取", styler=s)
                extraction_section.set_expanded(True)

                # 1.0 章节摘要
                summary = chapter_info.get('chapter_summary', '')
                if summary:
                    summary_widget = self._create_summary_widget(summary)
                    extraction_section.add_content(summary_widget)

                # 1.1 角色信息
                characters = chapter_info.get('characters', {})
                if characters:
                    char_widget = self._create_characters_widget(characters)
                    extraction_section.add_content(char_widget)

                # 1.2 事件列表
                events = chapter_info.get('events', [])
                if events:
                    events_widget = self._create_events_widget(events)
                    extraction_section.add_content(events_widget)

                # 1.3 对话列表
                dialogues = chapter_info.get('dialogues', [])
                if dialogues:
                    dialogues_widget = self._create_dialogues_widget(dialogues)
                    extraction_section.add_content(dialogues_widget)

                # 1.4 场景列表
                scenes = chapter_info.get('scenes', [])
                if scenes:
                    scenes_widget = self._create_scenes_widget(scenes)
                    extraction_section.add_content(scenes_widget)

                # 1.5 物品列表
                items = chapter_info.get('items', [])
                if items:
                    items_widget = self._create_items_widget(items)
                    extraction_section.add_content(items_widget)

                # 1.6 情绪曲线
                mood = chapter_info.get('mood_progression', [])
                climax = chapter_info.get('climax_event_indices', [])
                if mood or climax:
                    mood_widget = self._create_mood_widget(mood, climax)
                    extraction_section.add_content(mood_widget)

                layout.addWidget(extraction_section)

            # ==================== 步骤2：页面规划 ====================
            if page_plan:
                planning_section = CollapsibleSection("步骤2: 页面规划", styler=s)
                planning_section.set_expanded(True)

                pages = page_plan.get('pages', [])
                if pages:
                    pages_widget = self._create_pages_plan_widget(pages)
                    planning_section.add_content(pages_widget)

                layout.addWidget(planning_section)

            # ==================== 原始JSON（默认折叠） ====================
            raw_section = CollapsibleSection("原始数据 (JSON)", styler=s)
            raw_section.set_expanded(False)

            raw_text = self._create_json_text_edit(analysis_data)
            raw_section.add_content(raw_text)

            layout.addWidget(raw_section)
            layout.addStretch()

        scroll_area.setWidget(content_widget)
        return scroll_area

    def _create_summary_widget(self, summary: str) -> QFrame:
        """创建章节摘要展示"""
        s = self._styler
        frame = self._create_section_frame("章节摘要")
        layout = frame.layout()

        label = QLabel(summary)
        label.setWordWrap(True)
        label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_primary};
            background: transparent;
            border: none;
            line-height: 1.6;
        """)
        layout.addWidget(label)
        return frame

    def _create_characters_widget(self, characters: dict) -> QFrame:
        """创建角色信息展示"""
        s = self._styler
        frame = self._create_section_frame(f"角色信息 ({len(characters)})")
        layout = frame.layout()

        for name, char_data in characters.items():
            char_frame = QFrame()
            char_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_card};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(4)}px;
                    margin-bottom: {dp(4)}px;
                }}
            """)
            char_layout = QVBoxLayout(char_frame)
            char_layout.setContentsMargins(dp(10), dp(8), dp(10), dp(8))
            char_layout.setSpacing(dp(4))

            # 角色名
            name_label = QLabel(name)
            name_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {s.accent_color};
                background: transparent;
                border: none;
            """)
            char_layout.addWidget(name_label)

            # 外貌描述
            if isinstance(char_data, dict):
                appearance = char_data.get('appearance', '')
                role = char_data.get('role', '')
                if role:
                    role_label = QLabel(f"[{role}]")
                    role_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(11)}px;
                        color: {s.text_secondary};
                        background: transparent;
                        border: none;
                    """)
                    char_layout.addWidget(role_label)
                if appearance:
                    app_label = QLabel(appearance)
                    app_label.setWordWrap(True)
                    app_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(11)}px;
                        color: {s.text_primary};
                        background: transparent;
                        border: none;
                    """)
                    char_layout.addWidget(app_label)
            elif isinstance(char_data, str):
                app_label = QLabel(char_data)
                app_label.setWordWrap(True)
                app_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                """)
                char_layout.addWidget(app_label)

            layout.addWidget(char_frame)
        return frame

    def _create_events_widget(self, events: list) -> QFrame:
        """创建事件列表展示"""
        s = self._styler
        frame = self._create_section_frame(f"事件列表 ({len(events)})")
        layout = frame.layout()

        for i, event in enumerate(events):
            event_frame = QFrame()
            event_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_card};
                    border-left: 3px solid {s.accent_color};
                    border-radius: 0;
                    margin-bottom: {dp(4)}px;
                    padding-left: {dp(8)}px;
                }}
            """)
            event_layout = QHBoxLayout(event_frame)
            event_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            event_layout.setSpacing(dp(8))

            # 序号
            num_label = QLabel(f"{i+1}")
            num_label.setFixedWidth(dp(24))
            num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                font-weight: bold;
                color: {s.accent_color};
                background: {s.bg_secondary};
                border-radius: {dp(12)}px;
                padding: {dp(2)}px;
            """)
            event_layout.addWidget(num_label)

            # 事件描述
            if isinstance(event, dict):
                desc = event.get('description', str(event))
                importance = event.get('importance', '')
                text = desc
                if importance:
                    text = f"[{importance}] {desc}"
            else:
                text = str(event)

            desc_label = QLabel(text)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
                background: transparent;
                border: none;
            """)
            event_layout.addWidget(desc_label, 1)

            layout.addWidget(event_frame)
        return frame

    def _create_dialogues_widget(self, dialogues: list) -> QFrame:
        """创建对话列表展示"""
        s = self._styler
        frame = self._create_section_frame(f"对话列表 ({len(dialogues)})")
        layout = frame.layout()

        for dialogue in dialogues:
            dlg_frame = QFrame()
            dlg_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_card};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(4)}px;
                    margin-bottom: {dp(4)}px;
                }}
            """)
            dlg_layout = QVBoxLayout(dlg_frame)
            dlg_layout.setContentsMargins(dp(10), dp(6), dp(10), dp(6))
            dlg_layout.setSpacing(dp(2))

            if isinstance(dialogue, dict):
                speaker = dialogue.get('speaker', '???')
                content = dialogue.get('content', '')
                emotion = dialogue.get('emotion', '')

                # 说话者
                speaker_text = f"{speaker}"
                if emotion:
                    speaker_text += f" ({emotion})"
                speaker_label = QLabel(speaker_text)
                speaker_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    font-weight: bold;
                    color: {s.accent_color};
                    background: transparent;
                    border: none;
                """)
                dlg_layout.addWidget(speaker_label)

                # 内容
                content_label = QLabel(f'"{content}"')
                content_label.setWordWrap(True)
                content_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                    font-style: italic;
                """)
                dlg_layout.addWidget(content_label)
            else:
                label = QLabel(str(dialogue))
                label.setWordWrap(True)
                label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                """)
                dlg_layout.addWidget(label)

            layout.addWidget(dlg_frame)
        return frame

    def _create_scenes_widget(self, scenes: list) -> QFrame:
        """创建场景列表展示"""
        s = self._styler
        frame = self._create_section_frame(f"场景列表 ({len(scenes)})")
        layout = frame.layout()

        for i, scene in enumerate(scenes):
            scene_frame = QFrame()
            scene_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_card};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(4)}px;
                    margin-bottom: {dp(4)}px;
                }}
            """)
            scene_layout = QVBoxLayout(scene_frame)
            scene_layout.setContentsMargins(dp(10), dp(6), dp(10), dp(6))
            scene_layout.setSpacing(dp(2))

            if isinstance(scene, dict):
                location = scene.get('location', f'场景 {i+1}')
                description = scene.get('description', '')
                time = scene.get('time', '')
                atmosphere = scene.get('atmosphere', '')

                # 场景名/位置
                header_text = location
                if time:
                    header_text += f" - {time}"
                header_label = QLabel(header_text)
                header_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(12)}px;
                    font-weight: bold;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                """)
                scene_layout.addWidget(header_label)

                # 描述
                if description:
                    desc_label = QLabel(description)
                    desc_label.setWordWrap(True)
                    desc_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(11)}px;
                        color: {s.text_secondary};
                        background: transparent;
                        border: none;
                    """)
                    scene_layout.addWidget(desc_label)

                # 氛围
                if atmosphere:
                    atm_label = QLabel(f"氛围: {atmosphere}")
                    atm_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(10)}px;
                        color: {s.text_secondary};
                        background: transparent;
                        border: none;
                        font-style: italic;
                    """)
                    scene_layout.addWidget(atm_label)
            else:
                label = QLabel(str(scene))
                label.setWordWrap(True)
                label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                """)
                scene_layout.addWidget(label)

            layout.addWidget(scene_frame)
        return frame

    def _create_items_widget(self, items: list) -> QFrame:
        """创建物品列表展示"""
        s = self._styler
        frame = self._create_section_frame(f"物品列表 ({len(items)})")
        layout = frame.layout()

        # 使用网格布局，每行2个
        grid = QGridLayout()
        grid.setSpacing(dp(6))

        for i, item in enumerate(items):
            item_label = QLabel()
            if isinstance(item, dict):
                name = item.get('name', '未知物品')
                desc = item.get('description', '')
                text = f"- {name}"
                if desc:
                    text += f": {desc}"
            else:
                text = f"- {item}"

            item_label.setText(text)
            item_label.setWordWrap(True)
            item_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
                background: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(3)}px;
                padding: {dp(4)}px {dp(8)}px;
            """)
            grid.addWidget(item_label, i // 2, i % 2)

        layout.addLayout(grid)
        return frame

    def _create_mood_widget(self, mood: list, climax: list) -> QFrame:
        """创建情绪曲线展示"""
        s = self._styler
        frame = self._create_section_frame("情绪与节奏")
        layout = frame.layout()

        if mood:
            mood_text = " -> ".join(mood)
            mood_label = QLabel(f"情绪曲线: {mood_text}")
            mood_label.setWordWrap(True)
            mood_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
                background: transparent;
                border: none;
            """)
            layout.addWidget(mood_label)

        if climax:
            climax_text = ", ".join([f"事件{i+1}" for i in climax])
            climax_label = QLabel(f"高潮事件: {climax_text}")
            climax_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.accent_color};
                background: transparent;
                border: none;
            """)
            layout.addWidget(climax_label)

        return frame

    def _create_pages_plan_widget(self, pages: list) -> QFrame:
        """创建页面规划展示（紧凑网格布局）"""
        s = self._styler
        frame = self._create_section_frame(f"页面分配 ({len(pages)} 页)")
        layout = frame.layout()

        # 使用网格布局，每行3个页面卡片
        grid = QGridLayout()
        grid.setSpacing(dp(6))
        grid.setContentsMargins(0, 0, 0, 0)

        columns = 3  # 每行3个

        for i, page in enumerate(pages):
            page_frame = QFrame()
            page_frame.setStyleSheet(f"""
                QFrame {{
                    background: {s.bg_card};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(4)}px;
                }}
            """)
            page_layout = QVBoxLayout(page_frame)
            page_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            page_layout.setSpacing(dp(2))

            if isinstance(page, dict):
                page_num = page.get('page_number', '?')
                event_indices = page.get('event_indices', [])
                panel_count = page.get('suggested_panel_count', 0)
                pacing = page.get('pacing', '')
                focus = page.get('focus', '')

                # 第一行：页码 + 画格数
                header_layout = QHBoxLayout()
                header_layout.setSpacing(dp(4))
                header_layout.setContentsMargins(0, 0, 0, 0)

                page_label = QLabel(f"P{page_num}")
                page_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(12)}px;
                    font-weight: bold;
                    color: {s.accent_color};
                    background: transparent;
                    border: none;
                """)
                header_layout.addWidget(page_label)

                if panel_count:
                    panel_badge = QLabel(f"{panel_count}格")
                    panel_badge.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(9)}px;
                        color: {s.button_text};
                        background: {s.accent_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(1)}px {dp(4)}px;
                    """)
                    header_layout.addWidget(panel_badge)

                if pacing:
                    pacing_label = QLabel(pacing)
                    pacing_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(9)}px;
                        color: {s.text_secondary};
                        background: transparent;
                        border: none;
                    """)
                    header_layout.addWidget(pacing_label)

                header_layout.addStretch()
                page_layout.addLayout(header_layout)

                # 第二行：事件索引（紧凑显示）
                if event_indices:
                    events_text = "E:" + ",".join([str(i+1) for i in event_indices])
                    events_label = QLabel(events_text)
                    events_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(10)}px;
                        color: {s.text_secondary};
                        background: transparent;
                        border: none;
                    """)
                    page_layout.addWidget(events_label)

                # 第三行：焦点（截断显示）
                if focus:
                    # 截断过长的焦点文本
                    display_focus = focus[:20] + "..." if len(focus) > 20 else focus
                    focus_label = QLabel(display_focus)
                    focus_label.setToolTip(focus)  # 完整内容显示在提示框
                    focus_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(10)}px;
                        color: {s.text_primary};
                        background: transparent;
                        border: none;
                    """)
                    page_layout.addWidget(focus_label)
            else:
                label = QLabel(str(page)[:30])
                label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(10)}px;
                    color: {s.text_primary};
                    background: transparent;
                    border: none;
                """)
                page_layout.addWidget(label)

            # 添加到网格
            row = i // columns
            col = i % columns
            grid.addWidget(page_frame, row, col)

        layout.addLayout(grid)
        return frame

    def _create_section_frame(self, title: str) -> QFrame:
        """创建通用的区块Frame"""
        s = self._styler

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {s.bg_primary};
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(dp(10), dp(8), dp(10), dp(10))
        layout.setSpacing(dp(6))

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: bold;
            color: {s.accent_color};
            background: transparent;
            border: none;
            border-bottom: 1px solid {s.border_light};
            padding-bottom: {dp(4)}px;
            margin-bottom: {dp(4)}px;
        """)
        layout.addWidget(title_label)

        return frame

    def _create_json_text_edit(self, data: Any, max_height: int = None) -> QTextEdit:
        """创建JSON文本展示控件"""
        s = self._styler

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        # 格式化JSON
        try:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            json_str = str(data)

        text_edit.setPlainText(json_str)

        # 样式
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {s.bg_card};
                color: {s.text_primary};
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: {sp(11)}px;
                line-height: 1.4;
            }}
            QScrollBar:vertical {{
                width: {dp(6)}px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {s.border_light};
                border-radius: {dp(3)}px;
                min-height: {dp(20)}px;
            }}
        """)

        # 根据内容动态调整高度
        line_count = json_str.count('\n') + 1
        line_height = sp(11) * 1.4
        content_height = int(line_count * line_height + dp(20))

        if max_height:
            content_height = min(content_height, max_height)
        else:
            content_height = min(content_height, dp(400))

        text_edit.setMinimumHeight(dp(100))
        text_edit.setMaximumHeight(content_height)
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        return text_edit
