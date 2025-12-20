"""
场景卡片模块

提供单个漫画场景卡片的UI创建，包含提示词显示、复制、图片生成等功能。
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QTextEdit, QPushButton, QStackedWidget
)
from PyQt6.QtCore import Qt

from themes.button_styles import ButtonStyles
from components.loading_spinner import CircularSpinner
from utils.dpi_utils import dp, sp


class SceneCardMixin:
    """场景卡片功能混入类"""

    def _init_scene_state(self):
        """初始化场景相关状态"""
        self._scene_loading_states: Dict[int, dict] = {}

    def _create_scene_card(self, index: int, scene: dict, total: int) -> QFrame:
        """创建单个场景卡片"""
        s = self._styler
        scene_id = scene.get('scene_id', index + 1)
        prompt_en = scene.get('prompt_en', '')
        negative_prompt = scene.get('negative_prompt', '')
        generated_count = scene.get('generated_count', 0)

        card = QFrame()
        card.setObjectName(f"scene_card_{scene_id}")
        card.setStyleSheet(f"""
            QFrame#scene_card_{scene_id} {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # 顶部：场景号和操作按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(6))

        scene_num = QLabel(f"场景 {scene_id}/{total}")
        scene_num.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        header_layout.addWidget(scene_num)

        # 已生成图片标记
        if generated_count > 0:
            generated_label = QLabel(f"已生成 {generated_count} 张")
            generated_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.success};
                padding: {dp(2)}px {dp(6)}px;
                background-color: {s.success_bg};
                border-radius: {dp(3)}px;
                font-weight: 500;
            """)
            header_layout.addWidget(generated_label)

        # 构图和情感标签
        composition = scene.get('composition', '')
        emotion = scene.get('emotion', '')
        if composition or emotion:
            tags_text = " | ".join(filter(None, [composition, emotion]))
            tags_label = QLabel(tags_text)
            tags_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_tertiary};
                padding: {dp(2)}px {dp(5)}px;
                background-color: {s.bg_secondary};
                border-radius: {dp(3)}px;
            """)
            header_layout.addWidget(tags_label)

        header_layout.addStretch()

        # 生成图片按钮容器
        btn_stack = QStackedWidget()
        btn_stack.setFixedHeight(dp(26))

        # 状态0: 生成图片按钮
        generate_img_btn = None
        if prompt_en and self._on_generate_image and generated_count == 0:
            generate_img_btn = QPushButton("生成图片")
            generate_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            generate_img_btn.setStyleSheet(ButtonStyles.primary('XS'))
            generate_img_btn.clicked.connect(
                lambda checked, sid=scene_id, p=prompt_en, np=negative_prompt:
                    self._on_generate_image(sid, p, np)
            )
            btn_stack.addWidget(generate_img_btn)
        else:
            btn_text = "已生成" if generated_count > 0 else "生成图片"
            placeholder_btn = QPushButton(btn_text)
            placeholder_btn.setEnabled(False)
            placeholder_btn.setStyleSheet(ButtonStyles.primary('XS'))
            btn_stack.addWidget(placeholder_btn)

        # 状态1: 加载中状态
        loading_widget = QWidget()
        loading_layout = QHBoxLayout(loading_widget)
        loading_layout.setContentsMargins(dp(6), 0, dp(6), 0)
        loading_layout.setSpacing(dp(5))

        spinner = CircularSpinner(size=dp(16), color=s.accent_color, auto_start=False)
        loading_layout.addWidget(spinner)

        loading_label = QLabel("生成中...")
        loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_layout.addWidget(loading_label)
        loading_layout.addStretch()

        btn_stack.addWidget(loading_widget)
        btn_stack.setCurrentIndex(0)

        header_layout.addWidget(btn_stack)

        # 存储加载状态控件引用
        self._scene_loading_states[scene_id] = {
            'card': card,
            'btn_stack': btn_stack,
            'generate_btn': generate_img_btn,
            'spinner': spinner,
            'loading_label': loading_label,
        }

        # 复制按钮
        copy_btn = QPushButton("复制")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(ButtonStyles.secondary('XS'))
        if prompt_en and self._on_copy_prompt:
            copy_btn.clicked.connect(
                lambda checked, p=prompt_en: self._on_copy_prompt(p)
            )
        header_layout.addWidget(copy_btn)

        layout.addLayout(header_layout)

        # 排版信息行（如果有panel_info）
        panel_info = scene.get('panel_info', {})
        if panel_info:
            panel_row = self._create_panel_info_row(panel_info)
            layout.addWidget(panel_row)

        # 场景简述
        scene_summary = scene.get('scene_summary', '')
        if scene_summary:
            summary_label = QLabel(scene_summary)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {s.text_primary};
                padding: {dp(6)}px;
                background-color: {s.bg_secondary};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(summary_label)

        # 原文片段（折叠显示）
        original_text = scene.get('original_text', '')
        if original_text:
            original_container = self._create_original_text_section(scene_id, original_text)
            layout.addWidget(original_container)

        # 英文提示词
        if prompt_en:
            prompt_container = self._create_prompt_section(scene_id, prompt_en)
            layout.addWidget(prompt_container)

        # 负面提示词
        if negative_prompt:
            neg_layout = self._create_negative_prompt_row(negative_prompt)
            layout.addLayout(neg_layout)

        return card

    def _create_panel_info_row(self, panel_info: Dict[str, Any]) -> QFrame:
        """创建场景排版信息行

        Args:
            panel_info: 排版信息

        Returns:
            排版信息行Frame
        """
        s = self._styler

        row = QFrame()
        row.setObjectName("panel_info_row")
        row.setStyleSheet(f"""
            QFrame#panel_info_row {{
                background-color: {s.accent_color}10;
                border: 1px solid {s.accent_color}30;
                border-radius: {dp(4)}px;
                padding: {dp(3)}px;
            }}
        """)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(dp(8), dp(4), dp(8), dp(4))
        row_layout.setSpacing(dp(12))

        # 页码
        page_number = panel_info.get('page_number', 1)
        page_label = QLabel(f"P{page_number}")
        page_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            font-weight: bold;
            color: {s.accent_color};
            background-color: {s.accent_color}20;
            padding: {dp(2)}px {dp(6)}px;
            border-radius: {dp(3)}px;
        """)
        row_layout.addWidget(page_label)

        # 重要性
        importance = panel_info.get('importance', 'standard')
        importance_map = {
            'hero': ('主视觉', s.error),
            'major': ('重要', s.warning),
            'standard': ('标准', s.text_secondary),
            'minor': ('辅助', s.text_tertiary),
        }
        imp_text, imp_color = importance_map.get(importance, ('标准', s.text_secondary))
        importance_label = QLabel(imp_text)
        importance_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {imp_color};
            font-weight: 500;
        """)
        row_layout.addWidget(importance_label)

        # 宽高比
        aspect_ratio = panel_info.get('aspect_ratio', '1:1')
        ratio_label = QLabel(f"比例 {aspect_ratio}")
        ratio_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_secondary};
        """)
        row_layout.addWidget(ratio_label)

        # 镜头角度（如果有）
        camera_angle = panel_info.get('camera_angle')
        if camera_angle:
            angle_label = QLabel(camera_angle)
            angle_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_tertiary};
                font-style: italic;
            """)
            row_layout.addWidget(angle_label)

        row_layout.addStretch()

        return row

    def _create_original_text_section(self, scene_id: int, original_text: str) -> QFrame:
        """创建原文片段区域"""
        s = self._styler

        original_container = QFrame()
        original_container.setObjectName(f"original_{scene_id}")
        original_container.setStyleSheet(f"""
            QFrame#original_{scene_id} {{
                background-color: {s.bg_secondary};
                border-left: 2px solid {s.primary};
                border-radius: {dp(3)}px;
            }}
        """)
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(dp(10), dp(6), dp(6), dp(6))
        original_layout.setSpacing(dp(3))

        original_title = QLabel("原文:")
        original_title.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        original_layout.addWidget(original_title)

        display_text = original_text[:150] + "..." if len(original_text) > 150 else original_text
        original_label = QLabel(display_text)
        original_label.setWordWrap(True)
        original_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(11)}px;
            color: {s.text_secondary};
            font-style: italic;
        """)
        original_layout.addWidget(original_label)

        return original_container

    def _create_prompt_section(self, scene_id: int, prompt_en: str) -> QFrame:
        """创建提示词区域"""
        s = self._styler

        prompt_container = QFrame()
        prompt_container.setObjectName(f"prompt_{scene_id}")
        prompt_container.setStyleSheet(f"""
            QFrame#prompt_{scene_id} {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
            }}
        """)
        prompt_layout = QVBoxLayout(prompt_container)
        prompt_layout.setContentsMargins(dp(10), dp(6), dp(10), dp(6))
        prompt_layout.setSpacing(dp(3))

        prompt_title = QLabel("Prompt:")
        prompt_title.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        prompt_layout.addWidget(prompt_title)

        prompt_text = QTextEdit()
        prompt_text.setPlainText(prompt_en)
        prompt_text.setReadOnly(True)
        prompt_text.setMaximumHeight(dp(80))
        prompt_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(11)}px;
                color: {s.text_primary};
            }}
        """)
        prompt_layout.addWidget(prompt_text)

        return prompt_container

    def _create_negative_prompt_row(self, negative_prompt: str) -> QHBoxLayout:
        """创建负面提示词行"""
        s = self._styler

        neg_layout = QHBoxLayout()
        neg_layout.setSpacing(dp(4))

        neg_title = QLabel("Neg:")
        neg_title.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_tertiary};
        """)
        neg_layout.addWidget(neg_title)

        neg_label = QLabel(negative_prompt[:80] + "..." if len(negative_prompt) > 80 else negative_prompt)
        neg_label.setWordWrap(True)
        neg_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(10)}px;
            color: {s.text_secondary};
        """)
        neg_layout.addWidget(neg_label, stretch=1)

        copy_neg_btn = QPushButton("复制")
        copy_neg_btn.setFixedSize(dp(35), dp(18))
        copy_neg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_neg_btn.setStyleSheet(ButtonStyles.text('XS'))
        if self._on_copy_prompt:
            copy_neg_btn.clicked.connect(
                lambda checked, p=negative_prompt: self._on_copy_prompt(p)
            )
        neg_layout.addWidget(copy_neg_btn)

        return neg_layout

    # ==================== 场景加载状态控制 ====================

    def set_scene_loading(self, scene_id: int, loading: bool, message: str = "生成中..."):
        """设置场景卡片的加载状态"""
        if scene_id not in self._scene_loading_states:
            return

        state = self._scene_loading_states[scene_id]
        btn_stack = state.get('btn_stack')
        spinner = state.get('spinner')
        loading_label = state.get('loading_label')

        if not btn_stack:
            return

        if loading:
            btn_stack.setCurrentIndex(1)
            if loading_label and message:
                loading_label.setText(message)
            if spinner:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, spinner.start)
        else:
            btn_stack.setCurrentIndex(0)
            if spinner:
                spinner.stop()

    def set_scene_success(self, scene_id: int, message: str = "生成成功"):
        """设置场景生成成功状态"""
        if scene_id not in self._scene_loading_states:
            return

        state = self._scene_loading_states[scene_id]
        spinner = state.get('spinner')
        loading_label = state.get('loading_label')

        if spinner:
            spinner.stop()

        if loading_label:
            s = self._styler
            loading_label.setText(message)
            loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.success};
                font-weight: 500;
            """)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._restore_button_state(scene_id))

    def set_scene_error(self, scene_id: int, message: str = "生成失败"):
        """设置场景生成失败状态"""
        if scene_id not in self._scene_loading_states:
            return

        state = self._scene_loading_states[scene_id]
        spinner = state.get('spinner')
        loading_label = state.get('loading_label')

        if spinner:
            spinner.stop()

        if loading_label:
            s = self._styler
            loading_label.setText(message)
            loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.error};
                font-weight: 500;
            """)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._restore_button_state(scene_id))

    def _restore_button_state(self, scene_id: int):
        """恢复按钮状态"""
        if scene_id not in self._scene_loading_states:
            return

        state = self._scene_loading_states[scene_id]
        btn_stack = state.get('btn_stack')
        loading_label = state.get('loading_label')

        if loading_label:
            s = self._styler
            loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)
            loading_label.setText("生成中...")

        if btn_stack:
            btn_stack.setCurrentIndex(0)
