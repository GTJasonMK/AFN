"""
提示词Tab模块

提供分镜提示词标签页的UI创建，包含画格列表、角色外观等。
基于专业漫画分镜架构，支持按场景分组显示画格提示词。
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget
)
from PyQt6.QtCore import Qt

from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from components.loading_spinner import CircularSpinner
from utils.dpi_utils import dp, sp


class PromptTabMixin:
    """提示词Tab功能混入类"""

    def _init_panel_loading_states(self):
        """初始化面板加载状态字典"""
        if not hasattr(self, '_panel_card_states'):
            self._panel_card_states: Dict[str, dict] = {}

    def _create_prompt_tab(self, manga_data: dict, has_content: bool, panels: list, parent: QWidget) -> QWidget:
        """创建分镜提示词标签页

        Args:
            manga_data: 漫画数据
            has_content: 是否已有内容
            panels: 画格提示词列表
            parent: 父组件

        Returns:
            提示词标签页Widget
        """
        # 初始化面板加载状态字典
        self._init_panel_loading_states()

        s = self._styler

        # 获取断点续传信息
        can_resume = manga_data.get('can_resume', False)
        resume_progress = manga_data.get('resume_progress')

        tab = QWidget()
        tab.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(dp(4), dp(8), dp(4), dp(4))
        layout.setSpacing(dp(10))

        # 顶部工具栏
        toolbar = self._create_toolbar(has_content, can_resume, resume_progress)
        layout.addWidget(toolbar)

        # 内容区域
        if not has_content or not panels:
            # 显示空状态
            if can_resume and resume_progress:
                # 有断点可恢复时显示恢复提示
                stage_label = resume_progress.get('stage_label', '处理中')
                progress_msg = resume_progress.get('message', '')
                current = resume_progress.get('current', 0)
                total = resume_progress.get('total', 0)

                # 构建更详细的描述
                description_lines = [f'检测到未完成的生成任务']
                if stage_label:
                    description_lines.append(f'当前阶段: {stage_label}')
                if progress_msg:
                    description_lines.append(progress_msg)
                if total > 0:
                    description_lines.append(f'进度: {current}/{total}')

                description = '\n'.join(description_lines)

                empty_state = EmptyStateWithIllustration(
                    illustration_char='M',
                    title='继续生成',
                    description=description,
                    parent=parent
                )
            else:
                empty_state = EmptyStateWithIllustration(
                    illustration_char='M',
                    title='漫画分镜',
                    description='将章节内容智能分割为专业漫画分镜\n每个画格生成专属的AI绘图提示词',
                    parent=parent
                )
            layout.addWidget(empty_state, stretch=1)
        else:
            # 显示画格列表
            scroll_area = self._create_panels_scroll_area(manga_data)
            layout.addWidget(scroll_area, stretch=1)

        return tab

    def _create_panels_scroll_area(self, manga_data: dict) -> QScrollArea:
        """创建画格滚动区域

        Args:
            manga_data: 漫画数据

        Returns:
            滚动区域Widget
        """
        s = self._styler

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            {s.scrollbar_style()}
        """)

        # 滚动内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, dp(8), 0)
        content_layout.setSpacing(dp(10))

        # 统计信息卡片
        total_pages = manga_data.get('total_pages', 0)
        total_panels = manga_data.get('total_panels', 0)
        style = manga_data.get('style', 'manga')
        if total_pages > 0:
            stats_card = self._create_stats_card(total_pages, total_panels, style)
            content_layout.addWidget(stats_card)

        # 角色外观卡片
        character_profiles = manga_data.get('character_profiles', {})
        if character_profiles:
            profile_card = self._create_character_profiles_card(character_profiles)
            content_layout.addWidget(profile_card)

        # 按场景分组显示画格
        panels = manga_data.get('panels', [])
        scenes = manga_data.get('scenes', [])

        # 构建场景信息映射
        scene_info_map = {}
        for scene in scenes:
            scene_info_map[scene.get('scene_id')] = scene

        # 按场景分组
        panels_by_scene = {}
        for panel in panels:
            scene_id = panel.get('scene_id', 0)
            if scene_id not in panels_by_scene:
                panels_by_scene[scene_id] = []
            panels_by_scene[scene_id].append(panel)

        # 为每个场景创建卡片组
        for scene_id in sorted(panels_by_scene.keys()):
            scene_panels = panels_by_scene[scene_id]
            scene_info = scene_info_map.get(scene_id, {})

            # 场景标题
            scene_header = self._create_scene_header(scene_id, scene_info, len(scene_panels))
            content_layout.addWidget(scene_header)

            # 该场景的画格卡片
            for panel in scene_panels:
                panel_card = self._create_panel_card(panel)
                content_layout.addWidget(panel_card)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)

        return scroll_area

    def _create_stats_card(self, total_pages: int, total_panels: int, style: str) -> QFrame:
        """创建统计信息卡片"""
        s = self._styler

        style_map = {
            'manga': '日式漫画',
            'anime': '动漫风格',
            'comic': '美式漫画',
            'webtoon': '条漫风格',
        }

        card = QFrame()
        card.setObjectName("stats_card")
        card.setStyleSheet(f"""
            QFrame#stats_card {{
                background-color: {s.bg_card};
                border: 1px solid {s.accent_color}40;
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(20))

        # 风格
        style_text = style_map.get(style, style)
        style_widget = self._create_stat_item("风格", style_text)
        layout.addWidget(style_widget)

        # 总页数
        pages_widget = self._create_stat_item("页数", f"{total_pages} 页")
        layout.addWidget(pages_widget)

        # 总格数
        panels_widget = self._create_stat_item("画格", f"{total_panels} 格")
        layout.addWidget(panels_widget)

        layout.addStretch()

        return card

    def _create_scene_header(self, scene_id: int, scene_info: dict, panel_count: int) -> QFrame:
        """创建场景标题"""
        s = self._styler

        header = QFrame()
        header.setObjectName(f"scene_header_{scene_id}")
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {s.accent_color}15;
                border-left: 3px solid {s.accent_color};
                border-radius: {dp(4)}px;
            }}
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(dp(10), dp(6), dp(10), dp(6))
        layout.setSpacing(dp(4))

        # 顶部行：场景号 + 情感标签 + 画格数
        top_row = QHBoxLayout()
        top_row.setSpacing(dp(8))

        # 场景号
        scene_label = QLabel(f"场景 {scene_id}")
        scene_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: bold;
            color: {s.accent_color};
        """)
        top_row.addWidget(scene_label)

        top_row.addStretch()

        # 情感标签
        mood = scene_info.get('mood', '')
        mood_map = {
            'calm': '平静',
            'tension': '紧张',
            'action': '动作',
            'emotional': '情感',
            'mystery': '神秘',
            'comedy': '喜剧',
            'dramatic': '戏剧',
            'romantic': '浪漫',
            'horror': '恐怖',
            'flashback': '回忆',
        }
        if mood:
            mood_text = mood_map.get(mood, mood)
            mood_label = QLabel(mood_text)
            mood_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.button_text};
                background-color: {s.accent_color};
                padding: {dp(1)}px {dp(6)}px;
                border-radius: {dp(3)}px;
            """)
            top_row.addWidget(mood_label)

        count_label = QLabel(f"{panel_count} 格")
        count_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        top_row.addWidget(count_label)

        layout.addLayout(top_row)

        # 场景摘要（单独一行，自动换行）
        summary = scene_info.get('scene_summary', '')
        if summary:
            summary_label = QLabel(summary)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
            """)
            layout.addWidget(summary_label)

        return header

    def _create_panel_card(self, panel: dict) -> QFrame:
        """创建画格卡片"""
        s = self._styler

        panel_id = panel.get('panel_id', '')
        page_number = panel.get('page_number', 0)
        slot_id = panel.get('slot_id', 0)
        is_key_panel = panel.get('is_key_panel', False)

        card = QFrame()
        card.setObjectName(f"panel_card_{panel_id}")

        border_color = s.accent_color if is_key_panel else s.border_light
        card.setStyleSheet(f"""
            QFrame#panel_card_{panel_id} {{
                background-color: {s.bg_card};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                margin-left: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # 顶部行：画格信息
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        # 页码和槽位
        pos_label = QLabel(f"P{page_number}-{slot_id}")
        pos_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
            background-color: {s.bg_secondary};
            padding: {dp(1)}px {dp(6)}px;
            border-radius: {dp(3)}px;
        """)
        header_layout.addWidget(pos_label)

        # 比例
        aspect_ratio = panel.get('aspect_ratio', '1:1')
        ratio_label = QLabel(aspect_ratio)
        ratio_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        header_layout.addWidget(ratio_label)

        # 构图和角度（限制长度，避免溢出）
        composition = panel.get('composition', '')
        camera_angle = panel.get('camera_angle', '')
        if composition or camera_angle:
            comp_text = f"{composition} / {camera_angle}" if composition and camera_angle else (composition or camera_angle)
            # 限制长度防止溢出
            if len(comp_text) > 20:
                comp_text = comp_text[:18] + '...'
            comp_label = QLabel(comp_text)
            comp_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_secondary};
            """)
            header_layout.addWidget(comp_label)

        # 关键画格标记
        if is_key_panel:
            key_label = QLabel("关键")
            key_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(9)}px;
                color: {s.button_text};
                background-color: {s.accent_color};
                padding: {dp(1)}px {dp(4)}px;
                border-radius: {dp(2)}px;
            """)
            header_layout.addWidget(key_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 中文描述
        prompt_zh = panel.get('prompt_zh', '')
        if prompt_zh:
            zh_label = QLabel(prompt_zh)
            zh_label.setWordWrap(True)
            zh_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
                line-height: 1.4;
            """)
            layout.addWidget(zh_label)

        # 英文提示词（可折叠或默认隐藏）
        prompt_en = panel.get('prompt_en', '')
        if prompt_en:
            en_container = QFrame()
            en_container.setStyleSheet(f"""
                background-color: {s.bg_secondary};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px;
            """)
            en_layout = QVBoxLayout(en_container)
            en_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            en_layout.setSpacing(dp(4))

            en_header = QHBoxLayout()
            en_title = QLabel("Prompt")
            en_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_tertiary};
            """)
            en_header.addWidget(en_title)
            en_header.addStretch()

            # 复制按钮
            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(dp(40), dp(20))
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(ButtonStyles.text('XS'))
            if self._on_copy_prompt:
                copy_btn.clicked.connect(lambda checked, p=prompt_en: self._on_copy_prompt(p))
            en_header.addWidget(copy_btn)

            en_layout.addLayout(en_header)

            en_label = QLabel(prompt_en[:200] + ('...' if len(prompt_en) > 200 else ''))
            en_label.setWordWrap(True)
            en_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_secondary};
            """)
            en_layout.addWidget(en_label)

            layout.addWidget(en_container)

        # 对话和旁白
        dialogue = panel.get('dialogue', '')
        dialogue_speaker = panel.get('dialogue_speaker', '')
        dialogue_bubble_type = panel.get('dialogue_bubble_type', 'normal')
        dialogue_emotion = panel.get('dialogue_emotion', '')
        narration = panel.get('narration', '')
        sound_effects = panel.get('sound_effects', [])
        sound_effect_details = panel.get('sound_effect_details', [])

        # 文字元素区域
        if dialogue or narration or sound_effects or sound_effect_details:
            text_container = QFrame()
            text_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border-radius: {dp(4)}px;
                    border-left: 2px solid {s.accent_color}60;
                }}
            """)
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(dp(10), dp(8), dp(10), dp(8))
            text_layout.setSpacing(dp(6))

            # 对话显示（带气泡类型和情绪标签）
            if dialogue:
                dial_row = QHBoxLayout()
                dial_row.setSpacing(dp(6))

                # 气泡类型标签
                bubble_map = {
                    'normal': ('对话', s.text_secondary),
                    'shout': ('大喊', s.error),
                    'whisper': ('低语', s.text_tertiary),
                    'thought': ('心理', s.accent_color),
                    'narration': ('叙述', s.text_secondary),
                    'electronic': ('电子', s.accent_color),
                }
                bubble_info = bubble_map.get(dialogue_bubble_type, ('对话', s.text_secondary))
                bubble_label = QLabel(bubble_info[0])
                bubble_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(9)}px;
                    color: {s.button_text};
                    background-color: {bubble_info[1]};
                    padding: {dp(1)}px {dp(4)}px;
                    border-radius: {dp(2)}px;
                """)
                dial_row.addWidget(bubble_label)

                # 情绪标签（如果有）
                if dialogue_emotion:
                    emotion_label = QLabel(dialogue_emotion)
                    emotion_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(9)}px;
                        color: {s.text_tertiary};
                        background-color: {s.bg_card};
                        padding: {dp(1)}px {dp(4)}px;
                        border-radius: {dp(2)}px;
                        border: 1px solid {s.border_light};
                    """)
                    dial_row.addWidget(emotion_label)

                dial_row.addStretch()
                text_layout.addLayout(dial_row)

                # 对话内容
                speaker_text = f"{dialogue_speaker}: " if dialogue_speaker else ""
                dial_content = QLabel(f"{speaker_text}\"{dialogue}\"")
                dial_content.setWordWrap(True)
                dial_content.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_primary};
                    font-style: italic;
                """)
                text_layout.addWidget(dial_content)

            # 旁白显示
            if narration:
                narr_row = QHBoxLayout()
                narr_row.setSpacing(dp(6))

                narr_tag = QLabel("旁白")
                narr_tag.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(9)}px;
                    color: {s.button_text};
                    background-color: {s.text_tertiary};
                    padding: {dp(1)}px {dp(4)}px;
                    border-radius: {dp(2)}px;
                """)
                narr_row.addWidget(narr_tag)
                narr_row.addStretch()
                text_layout.addLayout(narr_row)

                narr_content = QLabel(f"[{narration}]")
                narr_content.setWordWrap(True)
                narr_content.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(10)}px;
                    color: {s.text_secondary};
                """)
                text_layout.addWidget(narr_content)

            # 音效显示（优先显示详细信息）
            sfx_to_show = sound_effect_details if sound_effect_details else [{"text": sfx} for sfx in sound_effects]
            if sfx_to_show:
                sfx_row = QHBoxLayout()
                sfx_row.setSpacing(dp(6))

                sfx_tag = QLabel("音效")
                sfx_tag.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(9)}px;
                    color: {s.button_text};
                    background-color: {s.warning if hasattr(s, 'warning') else s.accent_color};
                    padding: {dp(1)}px {dp(4)}px;
                    border-radius: {dp(2)}px;
                """)
                sfx_row.addWidget(sfx_tag)

                # 显示音效内容
                for sfx_item in sfx_to_show[:3]:  # 最多显示3个
                    sfx_text = sfx_item.get('text', sfx_item) if isinstance(sfx_item, dict) else sfx_item
                    sfx_type = sfx_item.get('type', '') if isinstance(sfx_item, dict) else ''
                    sfx_intensity = sfx_item.get('intensity', '') if isinstance(sfx_item, dict) else ''

                    # 根据强度设置样式
                    intensity_style = {
                        'large': f"font-weight: bold; font-size: {sp(12)}px;",
                        'medium': f"font-size: {sp(11)}px;",
                        'small': f"font-size: {sp(9)}px; color: {s.text_tertiary};",
                    }.get(sfx_intensity, f"font-size: {sp(10)}px;")

                    sfx_label = QLabel(sfx_text)
                    sfx_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        {intensity_style}
                        color: {s.text_primary};
                        background-color: {s.bg_card};
                        padding: {dp(2)}px {dp(6)}px;
                        border-radius: {dp(3)}px;
                        border: 1px solid {s.border_light};
                    """)
                    sfx_row.addWidget(sfx_label)

                sfx_row.addStretch()
                text_layout.addLayout(sfx_row)

            layout.addWidget(text_container)

        # 底部：生成图片按钮（带加载状态）
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        # 检查是否已生成图片
        has_image = panel.get('has_image', False)
        image_count = panel.get('image_count', 0)

        # 使用 QStackedWidget 切换按钮和加载状态
        btn_stack = QStackedWidget()
        btn_stack.setFixedHeight(dp(32))

        # 状态0: 生成/重新生成按钮
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_inner_layout = QHBoxLayout(btn_container)
        btn_inner_layout.setContentsMargins(0, 0, 0, 0)
        btn_inner_layout.setSpacing(dp(8))

        if has_image:
            # 已生成状态：显示"已生成"标签 + 重新生成按钮
            generated_label = QLabel(f"已生成 ({image_count}张)")
            generated_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.success};
                font-weight: 500;
            """)
            btn_inner_layout.addWidget(generated_label)

            regenerate_btn = QPushButton("重新生成")
            regenerate_btn.setFixedHeight(dp(26))
            regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            regenerate_btn.setStyleSheet(ButtonStyles.secondary('SM'))
            if self._on_generate_image:
                negative_prompt = panel.get('negative_prompt', '')
                panel_aspect_ratio = panel.get('aspect_ratio', '16:9')
                regenerate_btn.clicked.connect(
                    lambda checked, pid=panel_id, p=prompt_en, n=negative_prompt, ar=panel_aspect_ratio:
                    self._on_generate_image(pid, p, n, ar)
                )
            btn_inner_layout.addWidget(regenerate_btn)
            generate_btn = regenerate_btn  # 保存引用用于状态控制
        else:
            # 未生成状态：显示"生成图片"按钮
            generate_btn = QPushButton("生成图片")
            generate_btn.setFixedHeight(dp(26))
            generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
            if self._on_generate_image:
                negative_prompt = panel.get('negative_prompt', '')
                panel_aspect_ratio = panel.get('aspect_ratio', '16:9')
                generate_btn.clicked.connect(
                    lambda checked, pid=panel_id, p=prompt_en, n=negative_prompt, ar=panel_aspect_ratio:
                    self._on_generate_image(pid, p, n, ar)
                )
            btn_inner_layout.addWidget(generate_btn)

        btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_inner_layout = QHBoxLayout(loading_container)
        loading_inner_layout.setContentsMargins(0, 0, 0, 0)
        loading_inner_layout.setSpacing(dp(6))

        spinner = CircularSpinner(size=dp(18), color=s.accent_color, auto_start=False)
        loading_inner_layout.addWidget(spinner)

        loading_label = QLabel("正在生成...")
        loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(11)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_inner_layout.addWidget(loading_label)
        loading_inner_layout.addStretch()

        btn_stack.addWidget(loading_container)
        btn_stack.setCurrentIndex(0)

        footer_layout.addWidget(btn_stack)

        # 保存加载状态引用，用于外部控制
        self._panel_card_states[panel_id] = {
            'btn_stack': btn_stack,
            'spinner': spinner,
            'loading_label': loading_label,
            'generate_btn': generate_btn,
            'has_image': has_image,
        }

        layout.addLayout(footer_layout)

        return card

    def _create_stat_item(self, label: str, value: str) -> QWidget:
        """创建统计项

        Args:
            label: 标签文本
            value: 值文本

        Returns:
            统计项Widget
        """
        s = self._styler

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        item_layout = QVBoxLayout(widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(dp(2))

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        item_layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: 500;
            color: {s.text_primary};
        """)
        item_layout.addWidget(value_widget)

        return widget

    def _create_character_profiles_card(self, profiles: Dict[str, str]) -> QFrame:
        """创建角色外观配置卡片"""
        s = self._styler

        card = QFrame()
        card.setObjectName("character_profiles_card")
        card.setStyleSheet(f"""
            QFrame#character_profiles_card {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # 标题
        title = QLabel("角色外观设定")
        title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        layout.addWidget(title)

        # 角色列表 - 使用垂直布局避免溢出
        for name, description in profiles.items():
            char_container = QFrame()
            char_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px;
                }}
            """)
            char_layout = QVBoxLayout(char_container)
            char_layout.setContentsMargins(dp(8), dp(6), dp(8), dp(6))
            char_layout.setSpacing(dp(4))

            # 顶部行：角色名 + 复制按钮
            top_row = QHBoxLayout()
            top_row.setSpacing(dp(8))

            name_label = QLabel(name)
            name_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                font-weight: bold;
                color: {s.text_primary};
            """)
            top_row.addWidget(name_label)
            top_row.addStretch()

            # 复制按钮
            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(dp(45), dp(22))
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(ButtonStyles.text('XS'))
            if description and self._on_copy_prompt:
                copy_btn.clicked.connect(
                    lambda checked, d=description: self._on_copy_prompt(d)
                )
            top_row.addWidget(copy_btn)

            char_layout.addLayout(top_row)

            # 描述文本（换行显示）
            desc_text = description if description else "(待生成)"
            desc_label = QLabel(desc_text)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_secondary};
            """)
            char_layout.addWidget(desc_label)

            layout.addWidget(char_container)

        return card
