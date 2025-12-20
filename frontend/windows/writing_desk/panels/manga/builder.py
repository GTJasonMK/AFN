"""
漫画面板构建器 - 主入口类

负责创建漫画提示词生成Tab的所有UI组件，协调各子模块工作。
"""

from typing import Callable, Optional, List, Dict, Any
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTabWidget
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from ..base import BasePanelBuilder

from .toolbar import ToolbarMixin
from .prompt_tab import PromptTabMixin
from .pdf_tab import PdfTabMixin
from .scene_card import SceneCardMixin
from .state_mixin import StateMixin


class MangaPanelBuilder(
    BasePanelBuilder,
    ToolbarMixin,
    PromptTabMixin,
    PdfTabMixin,
    SceneCardMixin,
    StateMixin,
):
    """漫画面板构建器

    职责：创建章节漫画Tab的所有UI组件
    设计模式：工厂方法模式 + Mixin组合模式

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    """

    def __init__(
        self,
        on_generate: Optional[Callable[[str, int, str, bool], None]] = None,
        on_copy_prompt: Optional[Callable[[str], None]] = None,
        on_edit_scene: Optional[Callable[[int, dict], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_generate_image: Optional[Callable[[int, str, str], None]] = None,
        on_load_images: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        on_generate_pdf: Optional[Callable[[], None]] = None,
        on_load_pdf: Optional[Callable[[], Dict[str, Any]]] = None,
        on_download_pdf: Optional[Callable[[str], None]] = None,
    ):
        """初始化构建器

        Args:
            on_generate: 生成漫画提示词回调函数，参数为(风格, 场景数, 对话语言, 是否从检查点继续)
            on_copy_prompt: 复制提示词回调函数，参数为提示词内容
            on_edit_scene: 编辑场景回调函数，参数为(场景ID, 更新数据)
            on_delete: 删除漫画提示词回调函数
            on_generate_image: 生成图片回调函数，参数为(场景ID, 提示词, 负面提示词)
            on_load_images: 加载章节图片的回调函数，返回图片列表
            on_generate_pdf: 生成漫画PDF回调函数
            on_load_pdf: 加载PDF信息回调函数，返回PDF信息
            on_download_pdf: 下载PDF回调函数，参数为文件名
        """
        super().__init__()
        self._on_generate = on_generate
        self._on_copy_prompt = on_copy_prompt
        self._on_edit_scene = on_edit_scene
        self._on_delete = on_delete
        self._on_generate_image = on_generate_image
        self._on_load_images = on_load_images
        self._on_generate_pdf = on_generate_pdf
        self._on_load_pdf = on_load_pdf
        self._on_download_pdf = on_download_pdf

        # 初始化各Mixin的状态
        self._init_toolbar_state()
        self._init_pdf_state()
        self._init_scene_state()
        self._init_checkpoint_state()

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_manga_tab(data)

    def create_manga_tab(self, manga_data: dict, parent: QWidget = None) -> QWidget:
        """创建漫画提示词标签页

        Args:
            manga_data: 漫画数据，包含 scenes, character_profiles, style_guide, images, pdf_info 等字段
            parent: 父组件

        Returns:
            漫画Tab的根Widget
        """
        s = self._styler
        scenes = manga_data.get('scenes') or []
        has_content = manga_data.get('has_manga_prompt', False)
        images = manga_data.get('images') or []
        pdf_info = manga_data.get('pdf_info') or {}

        # 创建主容器
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        main_layout.setSpacing(dp(8))

        # 创建子标签页
        self._sub_tab_widget = QTabWidget()
        self._sub_tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {s.text_secondary};
                padding: {dp(6)}px {dp(16)}px;
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                border-bottom: 2px solid transparent;
                margin-right: {dp(4)}px;
            }}
            QTabBar::tab:selected {{
                color: {s.accent_color};
                border-bottom: 2px solid {s.accent_color};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                color: {s.text_primary};
            }}
        """)

        # Tab 1: 提示词
        prompt_tab = self._create_prompt_tab(manga_data, has_content, scenes, parent)
        self._sub_tab_widget.addTab(prompt_tab, "提示词")

        # Tab 2: 漫画预览 (PDF)
        images_tab = self._create_images_tab(images, pdf_info)
        pdf_label = "漫画" if pdf_info and pdf_info.get('success') else f"漫画 ({len(images)}图)"
        self._sub_tab_widget.addTab(images_tab, pdf_label)

        main_layout.addWidget(self._sub_tab_widget)

        return container

    def get_current_settings(self) -> dict:
        """获取当前设置"""
        style_map = {
            "漫画": "manga",
            "动漫": "anime",
            "美漫": "comic",
            "条漫": "webtoon",
        }
        style_text = self._style_combo.currentText() if self._style_combo else "漫画"
        scene_count = self._scene_count_combo.currentData() if self._scene_count_combo else None
        dialogue_language = self._language_combo.currentData() if self._language_combo else "chinese"
        return {
            "style": style_map.get(style_text, "manga"),
            "scene_count": scene_count,
            "dialogue_language": dialogue_language,
        }

    def update_images(self, images: List[Dict[str, Any]]):
        """更新图片标签页

        Args:
            images: 新的图片列表
        """
        if self._sub_tab_widget and self._sub_tab_widget.count() >= 2:
            # 移除旧的图片标签页
            self._sub_tab_widget.removeTab(1)
            # 创建新的图片标签页
            images_tab = self._create_images_tab(images)
            self._sub_tab_widget.insertTab(1, images_tab, f"图片 ({len(images)})")
