"""
漫画面板构建器 - 章节漫画Tab的UI构建逻辑

负责创建漫画提示词生成Tab的所有UI组件。
包含场景卡片显示、提示词复制、编辑等功能。
"""

from typing import Callable, Optional, List, Dict
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QTextEdit, QPushButton, QScrollArea, QComboBox,
    QSpinBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from themes.theme_manager import theme_manager
from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from utils.dpi_utils import dp, sp
from .base import BasePanelBuilder


class MangaPanelBuilder(BasePanelBuilder):
    """漫画面板构建器

    职责：创建章节漫画Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    """

    def __init__(
        self,
        on_generate: Optional[Callable[[str, int], None]] = None,
        on_copy_prompt: Optional[Callable[[str], None]] = None,
        on_edit_scene: Optional[Callable[[int, dict], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_generate_image: Optional[Callable[[int, str, str], None]] = None,
    ):
        """初始化构建器

        Args:
            on_generate: 生成漫画提示词回调函数，参数为(风格, 场景数)
            on_copy_prompt: 复制提示词回调函数，参数为提示词内容
            on_edit_scene: 编辑场景回调函数，参数为(场景ID, 更新数据)
            on_delete: 删除漫画提示词回调函数
            on_generate_image: 生成图片回调函数，参数为(场景ID, 提示词, 负面提示词)
        """
        super().__init__()
        self._on_generate = on_generate
        self._on_copy_prompt = on_copy_prompt
        self._on_edit_scene = on_edit_scene
        self._on_delete = on_delete
        self._on_generate_image = on_generate_image

        # 存储控件引用
        self._style_combo: Optional[QComboBox] = None
        self._scene_count_combo: Optional[QComboBox] = None  # 改为ComboBox支持"自动"选项

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_manga_tab(data)

    def create_manga_tab(self, manga_data: dict, parent: QWidget = None) -> QWidget:
        """创建漫画提示词标签页

        Args:
            manga_data: 漫画数据，包含 scenes, character_profiles, style_guide 等字段
                如果为空或没有scenes，显示生成界面
            parent: 父组件

        Returns:
            漫画Tab的根Widget
        """
        s = self._styler
        scenes = manga_data.get('scenes') or []
        has_content = manga_data.get('has_manga_prompt', False)

        # 创建主容器
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        main_layout.setSpacing(dp(12))

        # 顶部工具栏
        toolbar = self._create_toolbar(has_content)
        main_layout.addWidget(toolbar)

        # 内容区域
        if not has_content or not scenes:
            # 显示空状态
            empty_state = EmptyStateWithIllustration(
                illustration_char='M',
                title='漫画提示词',
                description='将章节内容智能分割为漫画场景\n生成可用于AI绘图的提示词',
                parent=parent
            )
            main_layout.addWidget(empty_state, stretch=1)
        else:
            # 显示场景列表
            scroll_area = self._create_scenes_scroll_area(manga_data)
            main_layout.addWidget(scroll_area, stretch=1)

        return container

    def _create_toolbar(self, has_content: bool) -> QFrame:
        """创建顶部工具栏

        Args:
            has_content: 是否已有漫画提示词内容

        Returns:
            工具栏Frame
        """
        s = self._styler

        toolbar = QFrame()
        toolbar.setObjectName("manga_toolbar")
        toolbar.setStyleSheet(f"""
            QFrame#manga_toolbar {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px;
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
        layout.setSpacing(dp(12))

        # 风格选择
        style_label = QLabel("风格:")
        style_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(style_label)

        self._style_combo = QComboBox()
        self._style_combo.addItems(["漫画", "动漫", "美漫", "条漫"])
        self._style_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {s.serif_font};
                background-color: {s.bg_secondary};
                color: {s.text_primary};
                padding: {dp(4)}px {dp(8)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
            }}
            QComboBox:focus {{
                border: 1px solid {s.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(4)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {s.bg_card};
                color: {s.text_primary};
                selection-background-color: {s.accent_color};
                selection-color: {s.button_text};
            }}
        """)
        self._style_combo.setFixedWidth(dp(80))
        layout.addWidget(self._style_combo)

        # 场景数选择 - 使用ComboBox支持"自动"选项
        scene_label = QLabel("场景数:")
        scene_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(scene_label)

        self._scene_count_combo = QComboBox()
        # 添加"自动"选项和具体数字选项
        self._scene_count_combo.addItem("自动", None)  # 值为None表示自动
        for i in range(5, 21):
            self._scene_count_combo.addItem(str(i), i)
        self._scene_count_combo.setCurrentIndex(0)  # 默认选择"自动"
        self._scene_count_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {s.serif_font};
                background-color: {s.bg_secondary};
                color: {s.text_primary};
                padding: {dp(4)}px {dp(8)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
            }}
            QComboBox:focus {{
                border: 1px solid {s.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(4)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {s.bg_card};
                color: {s.text_primary};
                selection-background-color: {s.accent_color};
                selection-color: {s.button_text};
            }}
        """)
        self._scene_count_combo.setFixedWidth(dp(70))
        layout.addWidget(self._scene_count_combo)

        layout.addStretch()

        # 生成/重新生成按钮
        if has_content:
            generate_btn = QPushButton("重新生成")
            generate_btn.setObjectName("manga_regenerate_btn")
        else:
            generate_btn = QPushButton("生成提示词")
            generate_btn.setObjectName("manga_generate_btn")

        generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
        generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(generate_btn)

        # 删除按钮（仅当有内容时显示）
        if has_content:
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("manga_delete_btn")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet(ButtonStyles.danger('SM'))
            if self._on_delete:
                delete_btn.clicked.connect(self._on_delete)
            layout.addWidget(delete_btn)

        return toolbar

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
        content_layout.setSpacing(dp(12))

        # 角色外观卡片（折叠）
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

    def _create_character_profiles_card(self, profiles: Dict[str, str]) -> QFrame:
        """创建角色外观配置卡片

        Args:
            profiles: 角色外观字典

        Returns:
            角色外观卡片Frame
        """
        s = self._styler

        card = QFrame()
        card.setObjectName("character_profiles_card")
        card.setStyleSheet(f"""
            QFrame#character_profiles_card {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 标题
        title = QLabel("角色外观设定")
        title.setObjectName("profiles_title")
        title.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        layout.addWidget(title)

        # 角色列表
        for name, description in profiles.items():
            char_layout = QHBoxLayout()
            char_layout.setSpacing(dp(8))

            name_label = QLabel(f"{name}:")
            name_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                font-weight: bold;
                color: {s.text_secondary};
            """)
            name_label.setFixedWidth(dp(80))
            char_layout.addWidget(name_label)

            desc_label = QLabel(description if description else "(待生成)")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            """)
            char_layout.addWidget(desc_label, stretch=1)

            # 复制按钮
            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(dp(50), dp(24))
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setStyleSheet(ButtonStyles.text('XS'))
            if description and self._on_copy_prompt:
                copy_btn.clicked.connect(
                    lambda checked, d=description: self._on_copy_prompt(d)
                )
            char_layout.addWidget(copy_btn)

            layout.addLayout(char_layout)

        return card

    def _create_scene_card(self, index: int, scene: dict, total: int) -> QFrame:
        """创建单个场景卡片

        Args:
            index: 场景索引
            scene: 场景数据
            total: 总场景数

        Returns:
            场景卡片Frame
        """
        s = self._styler
        scene_id = scene.get('scene_id', index + 1)
        prompt_en = scene.get('prompt_en', '')
        negative_prompt = scene.get('negative_prompt', '')

        card = QFrame()
        card.setObjectName(f"scene_card_{scene_id}")
        card.setStyleSheet(f"""
            QFrame#scene_card_{scene_id} {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(10))

        # 顶部：场景号和操作按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        scene_num = QLabel(f"场景 {scene_id}/{total}")
        scene_num.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        header_layout.addWidget(scene_num)

        # 构图和情感标签
        composition = scene.get('composition', '')
        emotion = scene.get('emotion', '')
        if composition or emotion:
            tags_text = " | ".join(filter(None, [composition, emotion]))
            tags_label = QLabel(tags_text)
            tags_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(11)}px;
                color: {s.text_tertiary};
                padding: {dp(2)}px {dp(6)}px;
                background-color: {s.bg_secondary};
                border-radius: {dp(4)}px;
            """)
            header_layout.addWidget(tags_label)

        header_layout.addStretch()

        # 生成图片按钮
        if prompt_en and self._on_generate_image:
            generate_img_btn = QPushButton("生成图片")
            generate_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            generate_img_btn.setStyleSheet(ButtonStyles.primary('XS'))
            generate_img_btn.clicked.connect(
                lambda checked, sid=scene_id, p=prompt_en, np=negative_prompt:
                    self._on_generate_image(sid, p, np)
            )
            header_layout.addWidget(generate_img_btn)

        # 复制按钮
        copy_btn = QPushButton("复制提示词")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(ButtonStyles.secondary('XS'))
        if prompt_en and self._on_copy_prompt:
            copy_btn.clicked.connect(
                lambda checked, p=prompt_en: self._on_copy_prompt(p)
            )
        header_layout.addWidget(copy_btn)

        layout.addLayout(header_layout)

        # 场景简述
        scene_summary = scene.get('scene_summary', '')
        if scene_summary:
            summary_label = QLabel(scene_summary)
            summary_label.setWordWrap(True)
            summary_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(13)}px;
                color: {s.text_primary};
                padding: {dp(8)}px;
                background-color: {s.bg_secondary};
                border-radius: {dp(4)}px;
            """)
            layout.addWidget(summary_label)

        # 原文片段
        original_text = scene.get('original_text', '')
        if original_text:
            original_container = QFrame()
            original_container.setObjectName(f"original_{scene_id}")
            original_container.setStyleSheet(f"""
                QFrame#original_{scene_id} {{
                    background-color: {s.bg_secondary};
                    border-left: 3px solid {s.primary};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)
            original_layout = QVBoxLayout(original_container)
            original_layout.setContentsMargins(dp(12), dp(8), dp(8), dp(8))
            original_layout.setSpacing(dp(4))

            original_title = QLabel("原文:")
            original_title.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(11)}px;
                color: {s.text_tertiary};
            """)
            original_layout.addWidget(original_title)

            original_label = QLabel(original_text[:200] + "..." if len(original_text) > 200 else original_text)
            original_label.setWordWrap(True)
            original_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                font-style: italic;
            """)
            original_layout.addWidget(original_label)

            layout.addWidget(original_container)

        # 英文提示词
        prompt_en = scene.get('prompt_en', '')
        if prompt_en:
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
            prompt_layout.setContentsMargins(dp(12), dp(8), dp(12), dp(8))
            prompt_layout.setSpacing(dp(4))

            prompt_title = QLabel("Prompt (EN):")
            prompt_title.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(11)}px;
                color: {s.text_tertiary};
            """)
            prompt_layout.addWidget(prompt_title)

            prompt_text = QTextEdit()
            prompt_text.setPlainText(prompt_en)
            prompt_text.setReadOnly(True)
            prompt_text.setMaximumHeight(dp(100))
            prompt_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: transparent;
                    border: none;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: {sp(12)}px;
                    color: {s.text_primary};
                }}
            """)
            prompt_layout.addWidget(prompt_text)

            layout.addWidget(prompt_container)

        # 负面提示词
        if negative_prompt:
            neg_layout = QHBoxLayout()
            neg_layout.setSpacing(dp(4))

            neg_title = QLabel("Negative:")
            neg_title.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(11)}px;
                color: {s.text_tertiary};
            """)
            neg_layout.addWidget(neg_title)

            neg_label = QLabel(negative_prompt[:100] + "..." if len(negative_prompt) > 100 else negative_prompt)
            neg_label.setWordWrap(True)
            neg_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(11)}px;
                color: {s.text_secondary};
            """)
            neg_layout.addWidget(neg_label, stretch=1)

            # 复制负面提示词按钮
            copy_neg_btn = QPushButton("复制")
            copy_neg_btn.setFixedSize(dp(40), dp(20))
            copy_neg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_neg_btn.setStyleSheet(ButtonStyles.text('XS'))
            if self._on_copy_prompt:
                copy_neg_btn.clicked.connect(
                    lambda checked, p=negative_prompt: self._on_copy_prompt(p)
                )
            neg_layout.addWidget(copy_neg_btn)

            layout.addLayout(neg_layout)

        return card

    def _on_generate_clicked(self):
        """生成按钮点击处理"""
        if self._on_generate and self._style_combo and self._scene_count_combo:
            # 映射风格选择到英文
            style_map = {
                "漫画": "manga",
                "动漫": "anime",
                "美漫": "comic",
                "条漫": "webtoon",
            }
            style_text = self._style_combo.currentText()
            style = style_map.get(style_text, "manga")
            # currentData() 返回 None（自动）或具体的整数值
            scene_count = self._scene_count_combo.currentData()
            self._on_generate(style, scene_count)

    def get_current_settings(self) -> dict:
        """获取当前设置

        Returns:
            包含style和scene_count的字典，scene_count为None表示自动
        """
        style_map = {
            "漫画": "manga",
            "动漫": "anime",
            "美漫": "comic",
            "条漫": "webtoon",
        }
        style_text = self._style_combo.currentText() if self._style_combo else "漫画"
        # currentData() 返回 None（自动）或具体的整数值
        scene_count = self._scene_count_combo.currentData() if self._scene_count_combo else None
        return {
            "style": style_map.get(style_text, "manga"),
            "scene_count": scene_count,
        }
