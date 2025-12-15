"""
漫画面板构建器 - 章节漫画Tab的UI构建逻辑

负责创建漫画提示词生成Tab的所有UI组件。
包含场景卡片显示、提示词复制、编辑、PDF预览等功能。
"""

from typing import Callable, Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QTextEdit, QPushButton, QScrollArea, QComboBox,
    QSpinBox, QApplication, QSizePolicy, QStackedWidget,
    QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor, QPixmap, QImage
from themes.theme_manager import theme_manager
from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from components.loading_spinner import CircularSpinner
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
        on_generate: Optional[Callable[[str, int, str], None]] = None,
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
            on_generate: 生成漫画提示词回调函数，参数为(风格, 场景数, 对话语言)
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

        # 存储控件引用
        self._style_combo: Optional[QComboBox] = None
        self._scene_count_combo: Optional[QComboBox] = None
        self._language_combo: Optional[QComboBox] = None
        self._dialogue_checkbox: Optional[QPushButton] = None
        self._sfx_checkbox: Optional[QPushButton] = None
        self._images_container: Optional[QWidget] = None
        self._images_grid: Optional[QGridLayout] = None
        self._sub_tab_widget: Optional[QTabWidget] = None
        self._pdf_scroll_area: Optional[QScrollArea] = None
        self._pdf_container: Optional[QWidget] = None
        self._pdf_loading_spinner: Optional[CircularSpinner] = None
        self._current_pdf_path: Optional[str] = None

        # 工具栏生成按钮相关控件
        self._toolbar_btn_stack: Optional[QStackedWidget] = None
        self._toolbar_generate_btn: Optional[QPushButton] = None
        self._toolbar_spinner: Optional[CircularSpinner] = None
        self._toolbar_loading_label: Optional[QLabel] = None

        # 存储场景卡片的加载状态控件引用
        self._scene_loading_states: Dict[int, dict] = {}

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

    def _create_images_tab(self, images: List[Dict[str, Any]], pdf_info: Dict[str, Any] = None) -> QWidget:
        """创建PDF预览标签页

        Args:
            images: 图片列表（用于判断是否有内容）
            pdf_info: PDF信息，包含 file_path, file_name 等

        Returns:
            PDF预览标签页Widget
        """
        s = self._styler

        tab = QWidget()
        tab.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(dp(4), dp(8), dp(4), dp(4))
        layout.setSpacing(dp(8))

        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setObjectName("pdf_toolbar")
        toolbar.setStyleSheet(f"""
            QFrame#pdf_toolbar {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
                padding: {dp(6)}px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(dp(12), dp(6), dp(12), dp(6))
        toolbar_layout.setSpacing(dp(8))

        # 状态标签
        status_text = "暂无PDF" if not pdf_info or not pdf_info.get('success') else f"共 {len(images)} 张图片"
        status_label = QLabel(status_text)
        status_label.setObjectName("pdf_status_label")
        status_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(13)}px;
            color: {s.text_secondary};
        """)
        toolbar_layout.addWidget(status_label)

        toolbar_layout.addStretch()

        # 生成/刷新PDF按钮
        generate_pdf_btn = QPushButton("生成PDF" if not pdf_info or not pdf_info.get('success') else "刷新PDF")
        generate_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_pdf_btn.setStyleSheet(ButtonStyles.primary('SM'))
        generate_pdf_btn.clicked.connect(self._on_generate_pdf_clicked)
        toolbar_layout.addWidget(generate_pdf_btn)

        # 下载按钮（仅当有PDF时显示）
        if pdf_info and pdf_info.get('success') and pdf_info.get('file_name'):
            download_btn = QPushButton("下载")
            download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            download_btn.setStyleSheet(ButtonStyles.secondary('SM'))
            download_btn.clicked.connect(
                lambda: self._on_download_pdf(pdf_info.get('file_name')) if self._on_download_pdf else None
            )
            toolbar_layout.addWidget(download_btn)

        layout.addWidget(toolbar)

        # 内容区域
        if not images:
            # 显示空状态
            empty_state = EmptyStateWithIllustration(
                illustration_char='P',
                title='暂无图片',
                description='先在提示词标签页生成场景图片\n然后点击"生成PDF"生成漫画',
                parent=tab
            )
            layout.addWidget(empty_state, stretch=1)
        elif not pdf_info or not pdf_info.get('success'):
            # 有图片但没有PDF，提示生成
            empty_state = EmptyStateWithIllustration(
                illustration_char='D',
                title='准备就绪',
                description=f'已有 {len(images)} 张图片\n点击"生成PDF"生成漫画预览',
                parent=tab
            )
            layout.addWidget(empty_state, stretch=1)
        else:
            # 显示PDF预览
            pdf_path = pdf_info.get('file_path', '')
            self._current_pdf_path = pdf_path
            pdf_scroll = self._create_pdf_preview(pdf_path)
            layout.addWidget(pdf_scroll, stretch=1)

        return tab

    def _create_pdf_preview(self, pdf_path: str) -> QScrollArea:
        """创建PDF预览区域

        使用PyMuPDF将PDF页面渲染为图片显示

        Args:
            pdf_path: PDF文件路径

        Returns:
            滚动区域Widget
        """
        s = self._styler

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {s.bg_secondary};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {s.bg_secondary};
            }}
            {s.scrollbar_style()}
        """)

        # 滚动内容容器
        self._pdf_container = QWidget()
        self._pdf_container.setStyleSheet(f"background-color: {s.bg_secondary};")
        content_layout = QVBoxLayout(self._pdf_container)
        content_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        content_layout.setSpacing(dp(12))
        content_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # 尝试加载PDF
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # 页面标题
            title_label = QLabel(f"漫画预览 ({page_count} 页)")
            title_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(16)}px;
                font-weight: bold;
                color: {s.text_primary};
                padding: {dp(8)}px;
            """)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(title_label)

            # 渲染每一页
            for page_num in range(page_count):
                page = doc[page_num]

                # 缩放因子（适配显示）
                zoom = 1.5  # 150% 缩放
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # 转换为QImage
                img_data = pix.tobytes("ppm")
                qimage = QImage.fromData(img_data)
                pixmap = QPixmap.fromImage(qimage)

                # 创建页面容器
                page_frame = QFrame()
                page_frame.setObjectName(f"pdf_page_{page_num}")
                page_frame.setStyleSheet(f"""
                    QFrame#pdf_page_{page_num} {{
                        background-color: white;
                        border: 1px solid {s.border_light};
                        border-radius: {dp(4)}px;
                    }}
                """)

                page_layout = QVBoxLayout(page_frame)
                page_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
                page_layout.setSpacing(dp(4))

                # 图片标签
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setScaledContents(False)
                page_layout.addWidget(img_label)

                # 页码标签
                page_num_label = QLabel(f"第 {page_num + 1} 页")
                page_num_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.text_tertiary};
                    padding: {dp(2)}px;
                """)
                page_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                page_layout.addWidget(page_num_label)

                content_layout.addWidget(page_frame)

            doc.close()

        except ImportError:
            # PyMuPDF未安装
            error_label = QLabel("PDF预览需要安装PyMuPDF\npip install PyMuPDF")
            error_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                color: {s.error};
                padding: {dp(20)}px;
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(error_label)

        except Exception as e:
            # 其他错误
            error_label = QLabel(f"PDF加载失败:\n{str(e)}")
            error_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                color: {s.error};
                padding: {dp(20)}px;
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setWordWrap(True)
            content_layout.addWidget(error_label)

        content_layout.addStretch()
        scroll_area.setWidget(self._pdf_container)

        return scroll_area

    def _on_generate_pdf_clicked(self):
        """生成PDF按钮点击处理"""
        if self._on_generate_pdf:
            self._on_generate_pdf()

    def _create_images_scroll_area(self, images: List[Dict[str, Any]]) -> QScrollArea:
        """创建图片滚动区域

        Args:
            images: 图片列表

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
        self._images_container = QWidget()
        self._images_container.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(self._images_container)
        content_layout.setContentsMargins(0, 0, dp(8), 0)
        content_layout.setSpacing(dp(12))

        # 按场景分组显示图片
        images_by_scene: Dict[int, List[Dict]] = {}
        for img in images:
            scene_id = img.get('scene_id', 0)
            if scene_id not in images_by_scene:
                images_by_scene[scene_id] = []
            images_by_scene[scene_id].append(img)

        # 按场景ID排序
        for scene_id in sorted(images_by_scene.keys()):
            scene_images = images_by_scene[scene_id]
            scene_card = self._create_scene_images_card(scene_id, scene_images)
            content_layout.addWidget(scene_card)

        content_layout.addStretch()
        scroll_area.setWidget(self._images_container)

        return scroll_area

    def _create_scene_images_card(self, scene_id: int, images: List[Dict[str, Any]]) -> QFrame:
        """创建单个场景的图片卡片

        Args:
            scene_id: 场景ID
            images: 该场景的图片列表

        Returns:
            场景图片卡片Frame
        """
        s = self._styler

        card = QFrame()
        card.setObjectName(f"scene_images_card_{scene_id}")
        card.setStyleSheet(f"""
            QFrame#scene_images_card_{scene_id} {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(10))

        # 场景标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        scene_label = QLabel(f"场景 {scene_id}")
        scene_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {s.text_primary};
        """)
        header_layout.addWidget(scene_label)

        count_label = QLabel(f"({len(images)} 张)")
        count_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_tertiary};
        """)
        header_layout.addWidget(count_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 图片网格（每行3张）
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(dp(8))

        columns = 3
        for idx, img in enumerate(images):
            row = idx // columns
            col = idx % columns
            image_widget = self._create_image_thumbnail(img)
            grid_layout.addWidget(image_widget, row, col)

        layout.addWidget(grid_widget)

        return card

    def _create_image_thumbnail(self, image_data: Dict[str, Any]) -> QFrame:
        """创建图片缩略图组件

        Args:
            image_data: 图片数据

        Returns:
            图片缩略图Frame
        """
        s = self._styler

        frame = QFrame()
        frame.setObjectName("image_thumbnail")
        frame.setStyleSheet(f"""
            QFrame#image_thumbnail {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
            }}
            QFrame#image_thumbnail:hover {{
                border-color: {s.accent_color};
            }}
        """)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        layout.setSpacing(dp(4))

        # 图片显示
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumSize(dp(120), dp(120))
        image_label.setMaximumSize(dp(200), dp(200))
        image_label.setScaledContents(False)
        image_label.setStyleSheet(f"""
            background-color: {s.bg_secondary};
            border-radius: {dp(4)}px;
        """)

        # 尝试加载图片
        file_path = image_data.get('local_path') or image_data.get('file_path', '')
        if file_path:
            try:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # 缩放图片保持比例
                    scaled_pixmap = pixmap.scaled(
                        dp(180), dp(180),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("加载失败")
                    image_label.setStyleSheet(f"""
                        background-color: {s.bg_secondary};
                        color: {s.text_tertiary};
                        font-size: {sp(11)}px;
                    """)
            except Exception:
                image_label.setText("加载失败")
        else:
            image_label.setText("无路径")

        layout.addWidget(image_label)

        # 图片信息
        info_layout = QHBoxLayout()
        info_layout.setSpacing(dp(4))

        # 创建时间或其他信息
        created_at = image_data.get('created_at', '')
        if created_at:
            # 只显示时间部分
            time_str = str(created_at).split('T')[-1][:8] if 'T' in str(created_at) else str(created_at)[-8:]
            time_label = QLabel(time_str)
            time_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(10)}px;
                color: {s.text_tertiary};
            """)
            info_layout.addWidget(time_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 存储图片数据用于点击事件
        frame.setProperty("image_data", image_data)
        # 点击查看大图（可以后续扩展）
        frame.mousePressEvent = lambda e, data=image_data: self._on_image_clicked(data)

        return frame

    def _on_image_clicked(self, image_data: Dict[str, Any]):
        """图片点击事件处理

        Args:
            image_data: 图片数据
        """
        # 可以后续扩展为显示大图预览对话框
        file_path = image_data.get('local_path') or image_data.get('file_path', '')
        if file_path:
            # 使用系统默认程序打开图片
            import subprocess
            import platform
            try:
                if platform.system() == 'Windows':
                    subprocess.Popen(['start', '', file_path], shell=True)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.Popen(['open', file_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', file_path])
            except Exception:
                pass

    def _on_refresh_images(self):
        """刷新图片列表"""
        if self._on_load_images:
            images = self._on_load_images()
            self.update_images(images)

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
                border-radius: {dp(6)}px;
                padding: {dp(6)}px;
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(dp(12), dp(6), dp(12), dp(6))
        layout.setSpacing(dp(10))

        # 风格选择
        style_label = QLabel("风格:")
        style_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(style_label)

        self._style_combo = QComboBox()
        self._style_combo.addItems(["漫画", "动漫", "美漫", "条漫"])
        self._style_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {s.ui_font};
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
        self._style_combo.setFixedWidth(dp(75))
        layout.addWidget(self._style_combo)

        # 场景数选择
        scene_label = QLabel("场景:")
        scene_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(scene_label)

        self._scene_count_combo = QComboBox()
        self._scene_count_combo.addItem("自动", None)
        for i in range(5, 21):
            self._scene_count_combo.addItem(str(i), i)
        self._scene_count_combo.setCurrentIndex(0)
        self._scene_count_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {s.ui_font};
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
        self._scene_count_combo.setFixedWidth(dp(65))
        layout.addWidget(self._scene_count_combo)

        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"background-color: {s.border_light}; max-width: 1px;")
        layout.addWidget(separator1)

        # 语言选择
        lang_label = QLabel("语言:")
        lang_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(lang_label)

        self._language_combo = QComboBox()
        self._language_combo.addItem("中文", "chinese")
        self._language_combo.addItem("日文", "japanese")
        self._language_combo.addItem("英文", "english")
        self._language_combo.addItem("韩文", "korean")
        self._language_combo.addItem("无文字", "none")
        self._language_combo.setCurrentIndex(0)
        self._language_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {s.ui_font};
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
        self._language_combo.setFixedWidth(dp(70))
        layout.addWidget(self._language_combo)

        layout.addStretch()

        # 生成按钮容器（使用 QStackedWidget 切换按钮/加载状态）
        self._toolbar_btn_stack = QStackedWidget()
        self._toolbar_btn_stack.setFixedHeight(dp(32))

        # 状态0: 生成/重新生成按钮
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(8))

        if has_content:
            self._toolbar_generate_btn = QPushButton("重新生成")
            self._toolbar_generate_btn.setObjectName("manga_regenerate_btn")
        else:
            self._toolbar_generate_btn = QPushButton("生成提示词")
            self._toolbar_generate_btn.setObjectName("manga_generate_btn")

        self._toolbar_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
        self._toolbar_generate_btn.clicked.connect(self._on_generate_clicked)
        btn_layout.addWidget(self._toolbar_generate_btn)

        # 删除按钮（仅当有内容时显示）
        if has_content:
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("manga_delete_btn")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet(ButtonStyles.danger('SM'))
            if self._on_delete:
                delete_btn.clicked.connect(self._on_delete)
            btn_layout.addWidget(delete_btn)

        self._toolbar_btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_layout = QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(dp(8), 0, dp(8), 0)
        loading_layout.setSpacing(dp(8))

        self._toolbar_spinner = CircularSpinner(size=dp(20), color=s.accent_color, auto_start=False)
        loading_layout.addWidget(self._toolbar_spinner)

        self._toolbar_loading_label = QLabel("正在生成提示词...")
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_layout.addWidget(self._toolbar_loading_label)
        loading_layout.addStretch()

        self._toolbar_btn_stack.addWidget(loading_container)
        self._toolbar_btn_stack.setCurrentIndex(0)

        layout.addWidget(self._toolbar_btn_stack)

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

    def _create_scene_card(self, index: int, scene: dict, total: int) -> QFrame:
        """创建单个场景卡片"""
        s = self._styler
        scene_id = scene.get('scene_id', index + 1)
        prompt_en = scene.get('prompt_en', '')
        negative_prompt = scene.get('negative_prompt', '')
        generated_count = scene.get('generated_count', 0)  # 已生成图片数量

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
        if prompt_en and self._on_generate_image:
            generate_img_btn = QPushButton("生成图片")
            generate_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            generate_img_btn.setStyleSheet(ButtonStyles.primary('XS'))
            generate_img_btn.clicked.connect(
                lambda checked, sid=scene_id, p=prompt_en, np=negative_prompt:
                    self._on_generate_image(sid, p, np)
            )
            btn_stack.addWidget(generate_img_btn)
        else:
            placeholder_btn = QPushButton("生成图片")
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

            layout.addWidget(original_container)

        # 英文提示词
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

            layout.addWidget(prompt_container)

        # 负面提示词
        if negative_prompt:
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

            layout.addLayout(neg_layout)

        return card

    def _on_generate_clicked(self):
        """生成按钮点击处理"""
        if self._on_generate and self._style_combo and self._scene_count_combo:
            style_map = {
                "漫画": "manga",
                "动漫": "anime",
                "美漫": "comic",
                "条漫": "webtoon",
            }
            style_text = self._style_combo.currentText()
            style = style_map.get(style_text, "manga")
            scene_count = self._scene_count_combo.currentData()
            # 获取语言设置
            dialogue_language = self._language_combo.currentData() if self._language_combo else "chinese"
            self._on_generate(style, scene_count, dialogue_language)

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

    # ==================== 工具栏加载状态控制 ====================

    def set_toolbar_loading(self, loading: bool, message: str = "正在生成提示词..."):
        """设置工具栏的加载状态

        Args:
            loading: 是否显示加载状态
            message: 加载时显示的消息
        """
        if not self._toolbar_btn_stack:
            return

        if loading:
            # 切换到加载状态
            self._toolbar_btn_stack.setCurrentIndex(1)
            if self._toolbar_loading_label:
                self._toolbar_loading_label.setText(message)
            if self._toolbar_spinner:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self._toolbar_spinner.start)
        else:
            # 切换回按钮状态
            self._toolbar_btn_stack.setCurrentIndex(0)
            if self._toolbar_spinner:
                self._toolbar_spinner.stop()

    def set_toolbar_success(self, message: str = "生成成功"):
        """设置工具栏生成成功状态"""
        if not self._toolbar_btn_stack or not self._toolbar_loading_label:
            return

        s = self._styler
        if self._toolbar_spinner:
            self._toolbar_spinner.stop()

        self._toolbar_loading_label.setText(message)
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.success};
            font-weight: 500;
        """)

        # 2秒后恢复按钮状态
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self._restore_toolbar_state)

    def set_toolbar_error(self, message: str = "生成失败"):
        """设置工具栏生成失败状态"""
        if not self._toolbar_btn_stack or not self._toolbar_loading_label:
            return

        s = self._styler
        if self._toolbar_spinner:
            self._toolbar_spinner.stop()

        self._toolbar_loading_label.setText(message)
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.error};
            font-weight: 500;
        """)

        # 3秒后恢复按钮状态
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._restore_toolbar_state)

    def _restore_toolbar_state(self):
        """恢复工具栏按钮状态"""
        if not self._toolbar_btn_stack:
            return

        s = self._styler

        # 恢复加载标签样式
        if self._toolbar_loading_label:
            self._toolbar_loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)
            self._toolbar_loading_label.setText("正在生成提示词...")

        # 切换回按钮状态
        self._toolbar_btn_stack.setCurrentIndex(0)
