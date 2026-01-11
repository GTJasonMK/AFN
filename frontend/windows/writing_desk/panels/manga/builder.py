"""
漫画面板构建器 - 主入口类

负责创建漫画分镜Tab的所有UI组件，协调各子模块工作。
基于专业漫画分镜架构，支持页面模板和画格级提示词显示。
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
from .details_tab import DetailsTabMixin


class MangaPanelBuilder(
    BasePanelBuilder,
    ToolbarMixin,
    PromptTabMixin,
    PdfTabMixin,
    SceneCardMixin,
    DetailsTabMixin,
):
    """漫画面板构建器

    职责：创建章节漫画Tab的所有UI组件
    设计模式：工厂方法模式 + Mixin组合模式

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    """

    def __init__(
        self,
        on_generate: Optional[Callable[[str, int, int, str, bool, bool, bool, Optional[str]], None]] = None,
        on_copy_prompt: Optional[Callable[[str], None]] = None,
        on_edit_scene: Optional[Callable[[int, dict], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_generate_image: Optional[Callable[[dict], None]] = None,
        on_load_images: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        on_generate_pdf: Optional[Callable[[], None]] = None,
        on_load_pdf: Optional[Callable[[], Dict[str, Any]]] = None,
        on_download_pdf: Optional[Callable[[str], None]] = None,
        on_generate_all_images: Optional[Callable[[], None]] = None,
        on_preview_prompt: Optional[Callable[[dict], None]] = None,
        on_stop_generate: Optional[Callable[[], None]] = None,
        on_stop_generate_all: Optional[Callable[[], None]] = None,
        api_base_url: str = "http://127.0.0.1:8123",
    ):
        """初始化构建器

        Args:
            on_generate: 生成漫画分镜回调函数，参数为(风格, 最少页数, 最多页数, 语言, 是否使用角色立绘, 是否自动生成缺失立绘, 是否强制重启, 起始阶段)
            on_copy_prompt: 复制提示词回调函数，参数为提示词内容
            on_edit_scene: 编辑场景回调函数，参数为(场景ID, 更新数据)
            on_delete: 删除漫画分镜回调函数
            on_generate_image: 生成图片回调函数，参数为画格完整数据字典
            on_load_images: 加载章节图片的回调函数，返回图片列表
            on_generate_pdf: 生成漫画PDF回调函数
            on_load_pdf: 加载PDF信息回调函数，返回PDF信息
            on_download_pdf: 下载PDF回调函数，参数为文件名
            on_generate_all_images: 一键生成所有图片回调函数
            on_preview_prompt: 预览实际提示词回调函数，参数为画格完整数据字典
            on_stop_generate: 停止生成分镜回调函数
            on_stop_generate_all: 停止批量生成图片回调函数
            api_base_url: 后端API基础URL，用于构造下载链接
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
        self._on_generate_all_images = on_generate_all_images
        self._on_preview_prompt = on_preview_prompt
        self._on_stop_generate = on_stop_generate
        self._on_stop_generate_all = on_stop_generate_all
        self._api_base_url = api_base_url

        # 画格加载状态记录
        self._panel_loading_states: Dict[str, bool] = {}

        # 初始化各Mixin的状态
        self._init_toolbar_state()
        self._init_pdf_state()
        self._init_scene_state()

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_manga_tab(data)

    def create_manga_tab(self, manga_data: dict, parent: QWidget = None) -> QWidget:
        """创建漫画分镜标签页

        Args:
            manga_data: 漫画数据，包含 scenes, panels, character_profiles, images, pdf_info 等字段
            parent: 父组件

        Returns:
            漫画Tab的根Widget
        """
        s = self._styler

        # 检查是否正在加载
        is_loading = manga_data.get('_is_loading', False)

        # 如果正在加载，显示加载状态
        if is_loading:
            return self._create_loading_placeholder()

        scenes = manga_data.get('scenes') or []
        panels = manga_data.get('panels') or []
        has_content = manga_data.get('has_manga_prompt', False)
        images = manga_data.get('images') or []
        pdf_info = manga_data.get('pdf_info') or {}
        total_pages = manga_data.get('total_pages', 0)
        total_panels = manga_data.get('total_panels', 0)

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

        # Tab 1: 分镜提示词
        prompt_tab = self._create_prompt_tab(manga_data, has_content, panels, parent)
        # 构建标签文本，显示生成状态
        is_complete = manga_data.get('is_complete', True)
        completed_pages = manga_data.get('completed_pages_count', 0)
        if has_content:
            if is_complete:
                tab_label = f"分镜 ({total_pages}页/{total_panels}格)"
            else:
                tab_label = f"分镜 ({completed_pages}/{total_pages}页 生成中...)"
        else:
            tab_label = "分镜"
        self._sub_tab_widget.addTab(prompt_tab, tab_label)

        # Tab 2: 漫画预览 (PDF)
        images_tab = self._create_images_tab(images, pdf_info)
        pdf_label = "漫画" if pdf_info and pdf_info.get('success') else f"漫画 ({len(images)}图)"
        self._sub_tab_widget.addTab(images_tab, pdf_label)

        # Tab 3: 详细信息（分析数据）
        details_tab = self._create_details_tab(manga_data)
        has_analysis = manga_data.get('analysis_data') is not None
        details_label = "详细信息" if has_analysis else "详细信息"
        self._sub_tab_widget.addTab(details_tab, details_label)

        main_layout.addWidget(self._sub_tab_widget)

        return container

    def _create_loading_placeholder(self) -> QWidget:
        """创建加载中的占位组件

        Returns:
            显示加载动画的Widget
        """
        from PyQt6.QtWidgets import QLabel
        from components.loading_spinner import CircularSpinner

        s = self._styler

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(16))

        # 加载动画
        spinner = CircularSpinner(size=48, auto_start=True)
        spinner_container = QWidget()
        spinner_layout = QVBoxLayout(spinner_container)
        spinner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner_layout.addWidget(spinner)
        layout.addWidget(spinner_container)

        # 加载文字
        loading_label = QLabel("正在加载漫画数据...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet(f"""
            background: transparent;
            border: none;
            font-family: {s.ui_font};
            font-size: {sp(14)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(loading_label)

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
        min_pages = self._min_pages_spin.value() if self._min_pages_spin else 8
        max_pages = self._max_pages_spin.value() if self._max_pages_spin else 15
        return {
            "style": style_map.get(style_text, "manga"),
            "min_pages": min_pages,
            "max_pages": max_pages,
        }

    def update_images(self, images: List[Dict[str, Any]], pdf_info: Dict[str, Any] = None):
        """更新图片标签页

        Args:
            images: 新的图片列表
            pdf_info: Bug 33 修复 - PDF信息，刷新时保留
        """
        if self._sub_tab_widget and self._sub_tab_widget.count() >= 2:
            # 移除旧的图片标签页
            self._sub_tab_widget.removeTab(1)
            # 创建新的图片标签页（Bug 33 修复: 传递pdf_info）
            images_tab = self._create_images_tab(images, pdf_info)
            self._sub_tab_widget.insertTab(1, images_tab, f"图片 ({len(images)})")

    def update_details_tab(self, analysis_data: Dict[str, Any]):
        """更新详细信息标签页（实时更新，不重建整个漫画Tab）

        Args:
            analysis_data: 分析数据，包含 chapter_info 和 page_plan
        """
        if not self._sub_tab_widget or self._sub_tab_widget.count() < 3:
            return

        # 保存当前选中的Tab索引
        current_index = self._sub_tab_widget.currentIndex()

        # 移除旧的详细信息Tab（索引2）
        old_details_tab = self._sub_tab_widget.widget(2)
        if old_details_tab:
            self._sub_tab_widget.removeTab(2)
            old_details_tab.deleteLater()

        # 创建新的详细信息Tab
        manga_data = {'analysis_data': analysis_data}
        new_details_tab = self._create_details_tab(manga_data)
        has_analysis = analysis_data is not None
        details_label = "详细信息" if has_analysis else "详细信息"
        self._sub_tab_widget.insertTab(2, new_details_tab, details_label)

        # 恢复之前选中的Tab索引
        self._sub_tab_widget.setCurrentIndex(current_index)

    # ==================== 画格加载状态控制 ====================

    def _parse_scene_id_from_panel_id(self, panel_id: str) -> int:
        """从panel_id解析出scene_id

        Args:
            panel_id: 画格ID，格式如 "scene1_page1_panel1"

        Returns:
            场景ID整数，解析失败返回0
        """
        try:
            parts = panel_id.split('_')
            return int(parts[0].replace('scene', ''))
        except (ValueError, IndexError):
            return 0

    def set_panel_loading(self, panel_id: str, loading: bool, message: str = "正在生成图片..."):
        """设置画格的加载状态

        Args:
            panel_id: 画格ID
            loading: 是否显示加载状态
            message: 加载时显示的消息
        """
        self._panel_loading_states[panel_id] = loading

        # 方式1: 尝试从 _scene_cards 获取（新方式）
        if hasattr(self, '_scene_cards') and panel_id in self._scene_cards:
            card = self._scene_cards[panel_id]
            if hasattr(card, 'set_loading'):
                card.set_loading(loading, message)
                return

        # 方式2: 尝试从 _panel_card_states 获取（PromptTab方式）
        if hasattr(self, '_panel_card_states') and panel_id in self._panel_card_states:
            state = self._panel_card_states[panel_id]
            btn_stack = state.get('btn_stack')
            spinner = state.get('spinner')
            loading_label = state.get('loading_label')

            if btn_stack:
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
            return

        # 方式3: 解析scene_id，使用 _scene_loading_states（场景卡片方式）
        scene_id = self._parse_scene_id_from_panel_id(panel_id)
        if scene_id > 0 and hasattr(self, '_scene_loading_states') and scene_id in self._scene_loading_states:
            # 使用 SceneCardMixin 中的方法
            state = self._scene_loading_states[scene_id]
            btn_stack = state.get('btn_stack')
            spinner = state.get('spinner')
            loading_label = state.get('loading_label')

            if btn_stack:
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

    def set_panel_success(self, panel_id: str, message: str = "生成成功"):
        """设置画格生成成功状态

        Args:
            panel_id: 画格ID
            message: 成功消息
        """
        self._panel_loading_states[panel_id] = False

        # 方式1: 尝试从 _scene_cards 获取
        if hasattr(self, '_scene_cards') and panel_id in self._scene_cards:
            card = self._scene_cards[panel_id]
            if hasattr(card, 'set_success'):
                card.set_success(message)
                return

        # 方式2: 尝试从 _panel_card_states 获取（PromptTab方式）
        if hasattr(self, '_panel_card_states') and panel_id in self._panel_card_states:
            state = self._panel_card_states[panel_id]
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
            QTimer.singleShot(2000, lambda pid=panel_id: self._restore_panel_button_state(pid))
            return

        # 方式3: 使用 _scene_loading_states
        scene_id = self._parse_scene_id_from_panel_id(panel_id)
        if scene_id > 0 and hasattr(self, '_scene_loading_states') and scene_id in self._scene_loading_states:
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
            QTimer.singleShot(2000, lambda sid=scene_id: self._restore_button_state(sid))

    def set_panel_error(self, panel_id: str, message: str = "生成失败"):
        """设置画格生成失败状态

        Args:
            panel_id: 画格ID
            message: 错误消息
        """
        self._panel_loading_states[panel_id] = False

        # 方式1: 尝试从 _scene_cards 获取
        if hasattr(self, '_scene_cards') and panel_id in self._scene_cards:
            card = self._scene_cards[panel_id]
            if hasattr(card, 'set_error'):
                card.set_error(message)
                return

        # 方式2: 尝试从 _panel_card_states 获取（PromptTab方式）
        if hasattr(self, '_panel_card_states') and panel_id in self._panel_card_states:
            state = self._panel_card_states[panel_id]
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
            QTimer.singleShot(3000, lambda pid=panel_id: self._restore_panel_button_state(pid))
            return

        # 方式3: 使用 _scene_loading_states
        scene_id = self._parse_scene_id_from_panel_id(panel_id)
        if scene_id > 0 and hasattr(self, '_scene_loading_states') and scene_id in self._scene_loading_states:
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
            QTimer.singleShot(3000, lambda sid=scene_id: self._restore_button_state(sid))

    def _restore_panel_button_state(self, panel_id: str):
        """恢复画格卡片按钮状态（PromptTab方式）"""
        if not hasattr(self, '_panel_card_states') or panel_id not in self._panel_card_states:
            return

        state = self._panel_card_states[panel_id]
        btn_stack = state.get('btn_stack')
        loading_label = state.get('loading_label')

        if loading_label:
            s = self._styler
            loading_label.setText("正在生成...")
            loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)

        if btn_stack:
            btn_stack.setCurrentIndex(0)

    # ==================== 兼容旧API ====================

    def set_scene_loading(self, scene_id: int, loading: bool, message: str = "正在生成图片..."):
        """兼容旧API: 设置场景的加载状态"""
        panel_id = f"scene{scene_id}_page1_panel1"
        self.set_panel_loading(panel_id, loading, message)

    def set_scene_success(self, scene_id: int, message: str = "生成成功"):
        """兼容旧API: 设置场景生成成功状态"""
        panel_id = f"scene{scene_id}_page1_panel1"
        self.set_panel_success(panel_id, message)

    def set_scene_error(self, scene_id: int, message: str = "生成失败"):
        """兼容旧API: 设置场景生成失败状态"""
        panel_id = f"scene{scene_id}_page1_panel1"
        self.set_panel_error(panel_id, message)
