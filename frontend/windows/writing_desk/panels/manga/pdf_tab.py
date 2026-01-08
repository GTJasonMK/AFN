"""
PDF预览Tab模块

提供漫画PDF预览和图片管理的UI。
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QPushButton, QScrollArea, QGridLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage

from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from components.loading_spinner import CircularSpinner
from utils.dpi_utils import dp, sp


class PdfTabMixin:
    """PDF预览Tab功能混入类"""

    def _init_pdf_state(self):
        """初始化PDF相关状态"""
        self._images_container: Optional[QWidget] = None
        self._images_grid: Optional[QGridLayout] = None
        self._pdf_scroll_area: Optional[QScrollArea] = None
        self._pdf_container: Optional[QWidget] = None
        self._current_pdf_path: Optional[str] = None
        # PDF按钮加载状态相关
        self._pdf_btn_stack: Optional[QStackedWidget] = None
        self._pdf_generate_btn: Optional[QPushButton] = None
        self._pdf_spinner: Optional[CircularSpinner] = None
        self._pdf_loading_label: Optional[QLabel] = None
        self._pdf_restore_timer: Optional[QTimer] = None

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

        # 按钮容器（支持加载状态切换）
        self._pdf_btn_stack = QStackedWidget()
        self._pdf_btn_stack.setFixedHeight(dp(32))

        # 状态0: 按钮容器
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(8))

        # 生成/刷新PDF按钮
        self._pdf_generate_btn = QPushButton("生成PDF" if not pdf_info or not pdf_info.get('success') else "刷新PDF")
        self._pdf_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pdf_generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
        self._pdf_generate_btn.clicked.connect(self._on_generate_pdf_clicked)
        btn_layout.addWidget(self._pdf_generate_btn)

        # 下载按钮（仅当有PDF时显示）
        if pdf_info and pdf_info.get('success') and pdf_info.get('file_name'):
            download_btn = QPushButton("下载")
            download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            download_btn.setStyleSheet(ButtonStyles.secondary('SM'))
            download_btn.clicked.connect(
                lambda: self._on_download_pdf(pdf_info.get('file_name')) if self._on_download_pdf else None
            )
            btn_layout.addWidget(download_btn)

        self._pdf_btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_layout = QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(dp(8), 0, dp(8), 0)
        loading_layout.setSpacing(dp(8))

        self._pdf_spinner = CircularSpinner(size=dp(20), color=s.accent_color, auto_start=False)
        loading_layout.addWidget(self._pdf_spinner)

        self._pdf_loading_label = QLabel("生成中...")
        self._pdf_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_layout.addWidget(self._pdf_loading_label)
        loading_layout.addStretch()

        self._pdf_btn_stack.addWidget(loading_container)
        self._pdf_btn_stack.setCurrentIndex(0)

        toolbar_layout.addWidget(self._pdf_btn_stack)

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

    def _on_generate_pdf_clicked(self):
        """生成PDF按钮点击处理"""
        if self._on_generate_pdf:
            self._on_generate_pdf()

    # ==================== PDF按钮加载状态控制 ====================

    def set_pdf_loading(self, loading: bool, message: str = "生成中..."):
        """设置PDF按钮的加载状态

        Args:
            loading: 是否显示加载状态
            message: 加载时显示的消息
        """
        if not self._pdf_btn_stack:
            return

        if loading:
            self._pdf_btn_stack.setCurrentIndex(1)
            if self._pdf_loading_label:
                self._pdf_loading_label.setText(message)
            if self._pdf_spinner:
                QTimer.singleShot(50, self._pdf_spinner.start)
        else:
            self._pdf_btn_stack.setCurrentIndex(0)
            if self._pdf_spinner:
                self._pdf_spinner.stop()

    def set_pdf_success(self, message: str = "生成成功"):
        """设置PDF生成成功状态"""
        if not self._pdf_btn_stack or not self._pdf_loading_label:
            return

        s = self._styler
        if self._pdf_spinner:
            self._pdf_spinner.stop()

        self._pdf_loading_label.setText(message)
        self._pdf_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.success};
            font-weight: 500;
        """)

        # 取消之前的定时器
        if self._pdf_restore_timer:
            self._pdf_restore_timer.stop()
        self._pdf_restore_timer = QTimer()
        self._pdf_restore_timer.setSingleShot(True)
        self._pdf_restore_timer.timeout.connect(self._restore_pdf_btn_state)
        self._pdf_restore_timer.start(2000)

    def set_pdf_error(self, message: str = "生成失败"):
        """设置PDF生成失败状态"""
        if not self._pdf_btn_stack or not self._pdf_loading_label:
            return

        s = self._styler
        if self._pdf_spinner:
            self._pdf_spinner.stop()

        self._pdf_loading_label.setText(message)
        self._pdf_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.error};
            font-weight: 500;
        """)

        # 取消之前的定时器
        if self._pdf_restore_timer:
            self._pdf_restore_timer.stop()
        self._pdf_restore_timer = QTimer()
        self._pdf_restore_timer.setSingleShot(True)
        self._pdf_restore_timer.timeout.connect(self._restore_pdf_btn_state)
        self._pdf_restore_timer.start(3000)

    def _restore_pdf_btn_state(self):
        """恢复PDF按钮状态"""
        if not self._pdf_btn_stack:
            return

        s = self._styler

        if self._pdf_loading_label:
            self._pdf_loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)
            self._pdf_loading_label.setText("生成中...")

        self._pdf_btn_stack.setCurrentIndex(0)

    def _create_pdf_preview(self, pdf_path: str) -> QScrollArea:
        """创建PDF预览区域

        使用PyMuPDF将PDF页面渲染为缩略图显示，便于快速浏览整体布局。
        采用紧凑的网格布局，每行显示多个页面缩略图。

        Args:
            pdf_path: PDF文件路径

        Returns:
            滚动区域Widget
        """
        s = self._styler

        # 缩略图配置
        THUMBNAIL_WIDTH = dp(160)
        THUMBNAILS_PER_ROW = 3

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
        main_layout = QVBoxLayout(self._pdf_container)
        main_layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        main_layout.setSpacing(dp(8))

        # 尝试加载PDF
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # 页面标题
            title_label = QLabel(f"漫画预览 ({page_count} 页)")
            title_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {s.text_primary};
                padding: {dp(4)}px;
            """)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(title_label)

            # 使用网格布局显示缩略图
            grid_widget = QWidget()
            grid_widget.setStyleSheet("background: transparent;")
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(dp(6))

            # 渲染每一页为缩略图
            for page_num in range(page_count):
                page = doc[page_num]

                # 使用较小的缩放因子生成缩略图
                page_rect = page.rect
                scale = THUMBNAIL_WIDTH / page_rect.width
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat)

                # 转换为QImage
                img_data = pix.tobytes("ppm")
                qimage = QImage.fromData(img_data)
                pixmap = QPixmap.fromImage(qimage)

                # 创建缩略图容器
                thumb_frame = QFrame()
                thumb_frame.setObjectName(f"pdf_thumb_{page_num}")
                thumb_frame.setStyleSheet(f"""
                    QFrame#pdf_thumb_{page_num} {{
                        background-color: white;
                        border: 1px solid {s.border_light};
                        border-radius: {dp(3)}px;
                    }}
                    QFrame#pdf_thumb_{page_num}:hover {{
                        border-color: {s.accent_color};
                    }}
                """)
                thumb_frame.setFixedWidth(THUMBNAIL_WIDTH + dp(6))

                thumb_layout = QVBoxLayout(thumb_frame)
                thumb_layout.setContentsMargins(dp(3), dp(3), dp(3), dp(3))
                thumb_layout.setSpacing(dp(2))

                # 图片标签
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setScaledContents(False)
                thumb_layout.addWidget(img_label)

                # 页码标签
                page_num_label = QLabel(f"P{page_num + 1}")
                page_num_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(9)}px;
                    color: {s.text_tertiary};
                """)
                page_num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb_layout.addWidget(page_num_label)

                # 计算网格位置
                row = page_num // THUMBNAILS_PER_ROW
                col = page_num % THUMBNAILS_PER_ROW
                grid_layout.addWidget(thumb_frame, row, col, Qt.AlignmentFlag.AlignCenter)

            doc.close()

            # 添加网格到主布局
            main_layout.addWidget(grid_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        except ImportError:
            # PyMuPDF未安装
            error_label = QLabel("PDF预览需要安装PyMuPDF\npip install PyMuPDF")
            error_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.error};
                padding: {dp(12)}px;
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(error_label)

        except Exception as e:
            # 其他错误
            error_label = QLabel(f"PDF加载失败:\n{str(e)}")
            error_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.error};
                padding: {dp(12)}px;
            """)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setWordWrap(True)
            main_layout.addWidget(error_label)

        main_layout.addStretch()
        scroll_area.setWidget(self._pdf_container)

        return scroll_area

    def _on_refresh_images(self):
        """刷新图片列表"""
        if self._on_load_images:
            images = self._on_load_images()
            # Bug 33 修复: 同时刷新PDF信息，避免重建Tab时丢失
            pdf_info = None
            if hasattr(self, '_on_load_pdf') and self._on_load_pdf:
                pdf_info = self._on_load_pdf()
            self.update_images(images, pdf_info)

    def _on_image_clicked(self, image_data: Dict[str, Any]):
        """图片点击事件处理

        Args:
            image_data: 图片数据
        """
        file_path = image_data.get('local_path') or image_data.get('file_path', '')
        if file_path:
            import subprocess
            import platform
            try:
                if platform.system() == 'Windows':
                    subprocess.Popen(['start', '', file_path], shell=True)
                elif platform.system() == 'Darwin':
                    subprocess.Popen(['open', file_path])
                else:
                    subprocess.Popen(['xdg-open', file_path])
            except Exception:
                pass
