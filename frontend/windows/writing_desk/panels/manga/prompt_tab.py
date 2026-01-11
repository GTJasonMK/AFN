"""
提示词Tab模块

提供分镜提示词标签页的UI创建，包含画格列表、角色外观等。
基于专业漫画分镜架构，支持按场景分组显示画格提示词。
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QGridLayout
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
        """创建画格滚动区域（网格布局）

        按页面分组，每页内按row_id分行，行内按width_ratio比例排列画格。

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

        # 获取画格和页面数据
        panels = manga_data.get('panels', [])
        # scenes字段存储的是pages数据（包含gutter信息）
        pages_info = manga_data.get('scenes', [])

        # 构建页面gutter信息映射
        page_gutter_map = {}
        for page_info in pages_info:
            pn = page_info.get('page_number')
            if pn is not None:
                page_gutter_map[pn] = {
                    'gutter_h': page_info.get('gutter_horizontal', 8),
                    'gutter_v': page_info.get('gutter_vertical', 8),
                    'mood': page_info.get('mood', ''),
                    'layout_description': page_info.get('layout_description', ''),
                }

        # 按页码分组画格
        panels_by_page: Dict[int, List] = {}
        for panel in panels:
            page_number = panel.get('page_number', 1)
            if page_number not in panels_by_page:
                panels_by_page[page_number] = []
            panels_by_page[page_number].append(panel)

        # 为每页创建网格布局
        for page_number in sorted(panels_by_page.keys()):
            page_panels = panels_by_page[page_number]
            page_info = page_gutter_map.get(page_number, {})

            # 页面标题
            page_header = self._create_page_header(page_number, page_info, len(page_panels))
            content_layout.addWidget(page_header)

            # 页面网格（按row_id分行排列）
            page_grid = self._create_page_grid(page_panels, page_info)
            content_layout.addWidget(page_grid)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)

        return scroll_area

    def _create_page_header(self, page_number: int, page_info: dict, panel_count: int) -> QFrame:
        """创建页面标题

        Args:
            page_number: 页码
            page_info: 页面信息（mood, layout_description, gutter等）
            panel_count: 画格数量

        Returns:
            页面标题Widget
        """
        s = self._styler

        header = QFrame()
        header.setObjectName(f"page_header_{page_number}")
        # 使用 bg_secondary 作为背景，确保在所有主题下都有足够对比度
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {s.bg_secondary};
                border-left: 3px solid {s.accent_color};
                border-radius: {dp(4)}px;
            }}
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(dp(10), dp(6), dp(10), dp(6))
        layout.setSpacing(dp(4))

        # 顶部行：页码 + 情感标签 + 画格数
        top_row = QHBoxLayout()
        top_row.setSpacing(dp(8))

        # 页码
        page_label = QLabel(f"第 {page_number} 页")
        page_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: bold;
            color: {s.accent_color};
        """)
        top_row.addWidget(page_label)

        top_row.addStretch()

        # 情感标签
        mood = page_info.get('mood', '')
        mood_map = {
            'calm': '平静', 'tension': '紧张', 'action': '动作',
            'emotional': '情感', 'mystery': '神秘', 'comedy': '喜剧',
            'dramatic': '戏剧', 'romantic': '浪漫', 'horror': '恐怖',
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

        # 布局描述（如果有）
        layout_desc = page_info.get('layout_description', '')
        if layout_desc:
            desc_label = QLabel(layout_desc)
            desc_label.setWordWrap(True)
            # 使用 text_primary 确保在所有主题下都清晰可见
            desc_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.text_primary};
            """)
            layout.addWidget(desc_label)

        return header

    def _create_page_grid(self, panels: List, page_info: dict) -> QFrame:
        """创建页面网格布局（支持row_span跨行）

        使用QGridLayout实现真正的跨行渲染：
        - 12列网格系统（类似Bootstrap）
        - row_span: 画格跨越多行
        - width_ratio: 映射为列跨度

        Args:
            panels: 该页的画格列表
            page_info: 页面信息

        Returns:
            网格布局Widget
        """
        s = self._styler

        # 12列网格系统，支持各种宽度组合
        GRID_COLUMNS = 12
        WIDTH_RATIO_COLS = {
            'full': 12,        # 100%
            'two_thirds': 8,   # 66.7%
            'half': 6,         # 50%
            'third': 4,        # 33.3%
        }

        container = QFrame()
        container.setObjectName("page_grid")
        container.setStyleSheet(f"""
            QFrame#page_grid {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
                padding: {dp(4)}px;
            }}
        """)

        gutter_v = page_info.get('gutter_v', 8)
        gutter_h = page_info.get('gutter_h', 8)

        grid_layout = QGridLayout(container)
        grid_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        grid_layout.setHorizontalSpacing(dp(gutter_h // 2))
        grid_layout.setVerticalSpacing(dp(gutter_v // 2))

        # 按row_id分组画格，计算最大行数
        rows_map: Dict[int, List] = {}
        max_row = 0
        for panel in panels:
            row_id = panel.get('row_id', 1)
            row_span = panel.get('row_span', 1)
            if row_id not in rows_map:
                rows_map[row_id] = []
            rows_map[row_id].append(panel)
            max_row = max(max_row, row_id + row_span - 1)

        if max_row == 0:
            max_row = 1

        # 占用矩阵：跟踪哪些单元格已被跨行画格占用
        occupied = [[False] * GRID_COLUMNS for _ in range(max_row)]

        # 按行号顺序处理画格
        for row_id in sorted(rows_map.keys()):
            row_panels = rows_map[row_id]

            for panel in row_panels:
                width_ratio = panel.get('width_ratio', 'half')
                row_span = panel.get('row_span', 1)
                col_span = WIDTH_RATIO_COLS.get(width_ratio, 6)

                # 找到第一个可用的列位置（考虑之前跨行画格的占用）
                col = 0
                while col + col_span <= GRID_COLUMNS:
                    can_place = True
                    for r in range(row_span):
                        row_idx = row_id - 1 + r
                        if row_idx >= max_row:
                            continue
                        for c in range(col_span):
                            if occupied[row_idx][col + c]:
                                can_place = False
                                break
                        if not can_place:
                            break
                    if can_place:
                        break
                    col += 1

                # 如果找不到足够空间，跳过（不应该发生在合理的布局中）
                if col + col_span > GRID_COLUMNS:
                    continue

                # 标记占用的单元格
                for r in range(row_span):
                    row_idx = row_id - 1 + r
                    if row_idx < max_row:
                        for c in range(col_span):
                            occupied[row_idx][col + c] = True

                # 创建画格卡片并添加到网格
                panel_card = self._create_panel_card_compact(panel)
                grid_layout.addWidget(panel_card, row_id - 1, col, row_span, col_span)

        # 设置列拉伸因子，使列宽度均匀分配
        for i in range(GRID_COLUMNS):
            grid_layout.setColumnStretch(i, 1)

        # 设置行拉伸因子，使行高度均匀分配
        for i in range(max_row):
            grid_layout.setRowStretch(i, 1)

        return container

    def _create_panel_card_compact(self, panel: dict) -> QFrame:
        """创建紧凑版画格卡片（用于网格布局）

        Args:
            panel: 画格数据

        Returns:
            画格卡片Widget
        """
        s = self._styler

        panel_id = panel.get('panel_id', '')
        page_number = panel.get('page_number', 0)
        panel_number = panel.get('panel_number', 1)
        row_id = panel.get('row_id', 1)
        row_span = panel.get('row_span', 1)
        width_ratio = panel.get('width_ratio', 'half')
        is_key_panel = panel.get('is_key_panel', False)
        aspect_ratio = panel.get('aspect_ratio', '1:1')

        card = QFrame()
        card.setObjectName(f"panel_compact_{panel_id}")

        # 关键画格使用强调边框
        border_color = s.accent_color if is_key_panel else s.border_light
        border_width = 2 if is_key_panel else 1
        card.setStyleSheet(f"""
            QFrame#panel_compact_{panel_id} {{
                background-color: {s.bg_secondary};
                border: {border_width}px solid {border_color};
                border-radius: {dp(4)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(6), dp(4), dp(6), dp(4))
        layout.setSpacing(dp(4))

        # 顶部行：位置标签 + 宽度比例 + 关键标记
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(4))

        # 位置标签: P{page}R{row}-{panel}
        pos_label = QLabel(f"P{page_number}R{row_id}-{panel_number}")
        pos_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(9)}px;
            color: {s.text_tertiary};
            background-color: {s.bg_card};
            padding: {dp(1)}px {dp(4)}px;
            border-radius: {dp(2)}px;
        """)
        header_layout.addWidget(pos_label)

        # 宽度比例标签
        width_labels = {'full': '100%', 'two_thirds': '2/3', 'half': '1/2', 'third': '1/3'}
        width_text = width_labels.get(width_ratio, width_ratio)
        if row_span > 1:
            width_text += f" x{row_span}行"
        width_label = QLabel(width_text)
        width_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(9)}px;
            color: {s.accent_color};
        """)
        header_layout.addWidget(width_label)

        # 宽高比
        ratio_label = QLabel(aspect_ratio)
        ratio_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(9)}px;
            color: {s.text_tertiary};
        """)
        header_layout.addWidget(ratio_label)

        header_layout.addStretch()

        # 关键画格标记
        if is_key_panel:
            key_label = QLabel("KEY")
            key_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(8)}px;
                color: {s.button_text};
                background-color: {s.accent_color};
                padding: {dp(1)}px {dp(3)}px;
                border-radius: {dp(2)}px;
            """)
            header_layout.addWidget(key_label)

        layout.addLayout(header_layout)

        # 中文描述（截断显示）
        prompt = panel.get('prompt', '')
        if prompt:
            max_len = 60
            display_text = prompt[:max_len] + '...' if len(prompt) > max_len else prompt
            zh_label = QLabel(display_text)
            zh_label.setWordWrap(True)
            zh_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_primary};
            """)
            layout.addWidget(zh_label)

        # 底部：对话/旁白简要信息 + 生成按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(dp(4))

        # 对话/旁白指示器
        dialogue = panel.get('dialogue', '')
        narration = panel.get('narration', '')
        if dialogue:
            dial_indicator = QLabel("对话")
            dial_indicator.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(8)}px;
                color: {s.text_secondary};
                background-color: {s.bg_card};
                padding: {dp(1)}px {dp(3)}px;
                border-radius: {dp(2)}px;
            """)
            bottom_layout.addWidget(dial_indicator)
        if narration:
            narr_indicator = QLabel("旁白")
            narr_indicator.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(8)}px;
                color: {s.text_tertiary};
                background-color: {s.bg_card};
                padding: {dp(1)}px {dp(3)}px;
                border-radius: {dp(2)}px;
            """)
            bottom_layout.addWidget(narr_indicator)

        bottom_layout.addStretch()

        # 查看提示词按钮
        view_btn = QPushButton("查看")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setStyleSheet(ButtonStyles.text('XS'))
        view_btn.setToolTip("查看完整提示词")
        if hasattr(self, '_on_preview_prompt') and self._on_preview_prompt:
            view_btn.clicked.connect(
                lambda checked, p=panel: self._on_preview_prompt(p)
            )
        bottom_layout.addWidget(view_btn)

        # 检查是否已生成图片
        has_image = panel.get('has_image', False)

        # 使用 QStackedWidget 切换按钮和加载状态
        btn_stack = QStackedWidget()
        btn_stack.setFixedHeight(dp(32))  # XS按钮需要足够空间

        # 状态0: 生成/重新生成按钮
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_inner_layout = QHBoxLayout(btn_container)
        btn_inner_layout.setContentsMargins(0, 0, 0, 0)
        btn_inner_layout.setSpacing(dp(4))

        if has_image:
            generated_label = QLabel("OK")
            generated_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(9)}px;
                color: {s.success};
                font-weight: bold;
            """)
            btn_inner_layout.addWidget(generated_label)

        generate_btn = QPushButton("生成" if not has_image else "重生成")
        generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_btn.setStyleSheet(ButtonStyles.text('XS') if has_image else ButtonStyles.primary('XS'))
        if self._on_generate_image:
            generate_btn.clicked.connect(
                lambda checked, p=panel: self._on_generate_image(p)
            )
        btn_inner_layout.addWidget(generate_btn)

        btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_inner_layout = QHBoxLayout(loading_container)
        loading_inner_layout.setContentsMargins(0, 0, 0, 0)
        loading_inner_layout.setSpacing(dp(4))

        spinner = CircularSpinner(size=dp(14), color=s.accent_color, auto_start=False)
        loading_inner_layout.addWidget(spinner)

        loading_label = QLabel("...")
        loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(9)}px;
            color: {s.accent_color};
        """)
        loading_inner_layout.addWidget(loading_label)
        loading_inner_layout.addStretch()

        btn_stack.addWidget(loading_container)
        btn_stack.setCurrentIndex(0)

        bottom_layout.addWidget(btn_stack)

        # 保存加载状态引用
        self._panel_card_states[panel_id] = {
            'btn_stack': btn_stack,
            'spinner': spinner,
            'loading_label': loading_label,
            'generate_btn': generate_btn,
            'has_image': has_image,
        }

        layout.addLayout(bottom_layout)

        return card

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
            copy_btn.setMinimumWidth(dp(48))
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
