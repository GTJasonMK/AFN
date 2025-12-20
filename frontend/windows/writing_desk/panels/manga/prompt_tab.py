"""
提示词Tab模块

提供提示词标签页的UI创建，包含场景列表、排版信息、角色外观等。
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt

from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from utils.dpi_utils import dp, sp


class PromptTabMixin:
    """提示词Tab功能混入类"""

    def _create_prompt_tab(self, manga_data: dict, has_content: bool, scenes: list, parent: QWidget) -> QWidget:
        """创建提示词标签页

        Args:
            manga_data: 漫画数据
            has_content: 是否已有内容
            scenes: 场景列表
            parent: 父组件

        Returns:
            提示词标签页Widget
        """
        s = self._styler

        tab = QWidget()
        tab.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(dp(4), dp(8), dp(4), dp(4))
        layout.setSpacing(dp(10))

        # 顶部工具栏
        toolbar = self._create_toolbar(has_content)
        layout.addWidget(toolbar)

        # 内容区域
        if not has_content or not scenes:
            # 显示空状态
            empty_state = EmptyStateWithIllustration(
                illustration_char='M',
                title='漫画提示词',
                description='将章节内容智能分割为漫画场景\n生成可用于AI绘图的提示词',
                parent=parent
            )
            layout.addWidget(empty_state, stretch=1)
        else:
            # 显示场景列表
            scroll_area = self._create_scenes_scroll_area(manga_data)
            layout.addWidget(scroll_area, stretch=1)

        return tab

    def _create_scenes_scroll_area(self, manga_data: dict) -> QScrollArea:
        """创建场景滚动区域

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

        # 排版信息卡片
        layout_info = manga_data.get('layout_info', {})
        if layout_info:
            layout_card = self._create_layout_info_card(layout_info)
            content_layout.addWidget(layout_card)

        # 角色外观卡片
        character_profiles = manga_data.get('character_profiles', {})
        if character_profiles:
            profile_card = self._create_character_profiles_card(character_profiles)
            content_layout.addWidget(profile_card)

        # 场景卡片列表
        scenes = manga_data.get('scenes', [])
        for idx, scene in enumerate(scenes):
            scene_card = self._create_scene_card(idx, scene, len(scenes))
            content_layout.addWidget(scene_card)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)

        return scroll_area

    def _create_layout_info_card(self, layout_info: Dict[str, Any]) -> QFrame:
        """创建排版信息卡片

        Args:
            layout_info: 排版信息数据

        Returns:
            排版信息卡片Frame
        """
        s = self._styler

        card = QFrame()
        card.setObjectName("layout_info_card")
        card.setStyleSheet(f"""
            QFrame#layout_info_card {{
                background-color: {s.bg_card};
                border: 1px solid {s.accent_color}40;
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # 标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        title = QLabel("专业排版")
        title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {s.accent_color};
        """)
        header_layout.addWidget(title)

        # 排版类型标签
        layout_type = layout_info.get('layout_type', 'traditional_manga')
        layout_type_map = {
            'traditional_manga': '传统漫画',
            'comic': '美漫',
            'webtoon': '条漫',
            'grid': '网格',
        }
        type_text = layout_type_map.get(layout_type, layout_type)
        type_label = QLabel(type_text)
        type_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_on_primary};
            background-color: {s.accent_color};
            padding: {dp(2)}px {dp(8)}px;
            border-radius: {dp(3)}px;
        """)
        header_layout.addWidget(type_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 统计信息行
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(dp(16))

        # 页面尺寸
        page_size = layout_info.get('page_size', 'A4')
        size_widget = self._create_stat_item("页面", page_size)
        stats_layout.addWidget(size_widget)

        # 总页数
        total_pages = layout_info.get('total_pages', 0)
        pages_widget = self._create_stat_item("页数", f"{total_pages} 页")
        stats_layout.addWidget(pages_widget)

        # 总格数
        total_panels = layout_info.get('total_panels', 0)
        panels_widget = self._create_stat_item("格数", f"{total_panels} 格")
        stats_layout.addWidget(panels_widget)

        # 阅读方向
        reading_dir = layout_info.get('reading_direction', 'ltr')
        dir_text = "从左到右" if reading_dir == 'ltr' else "从右到左"
        dir_widget = self._create_stat_item("阅读", dir_text)
        stats_layout.addWidget(dir_widget)

        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # 排版分析（如果有）
        layout_analysis = layout_info.get('layout_analysis', '')
        if layout_analysis:
            analysis_label = QLabel(layout_analysis)
            analysis_label.setWordWrap(True)
            analysis_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
                padding: {dp(6)}px;
                background-color: {s.bg_secondary};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(analysis_label)

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
        layout.setSpacing(dp(6))

        # 标题
        title = QLabel("角色外观设定")
        title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        layout.addWidget(title)

        # 角色列表
        for name, description in profiles.items():
            char_layout = QHBoxLayout()
            char_layout.setSpacing(dp(6))

            name_label = QLabel(f"{name}:")
            name_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                font-weight: bold;
                color: {s.text_secondary};
            """)
            name_label.setFixedWidth(dp(70))
            char_layout.addWidget(name_label)

            desc_label = QLabel(description if description else "(待生成)")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
            """)
            char_layout.addWidget(desc_label, stretch=1)

            # 复制按钮
            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(dp(45), dp(22))
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(ButtonStyles.text('XS'))
            if description and self._on_copy_prompt:
                copy_btn.clicked.connect(
                    lambda checked, d=description: self._on_copy_prompt(d)
                )
            char_layout.addWidget(copy_btn)

            layout.addLayout(char_layout)

        return card
