"""
图片选择器组件

提供背景图片选择功能，支持预览、选择和清除。
"""

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ImagePickerWidget(QWidget):
    """图片选择器组件

    布局：
    +-------------------------------------------+
    | [预览图] [路径...            ] [选择] [清除]|
    +-------------------------------------------+

    - 左侧图片缩略图预览
    - 中间文件路径显示
    - 右侧选择和清除按钮
    """

    # 图片变更信号，参数为图片路径，空字符串表示清除
    image_changed = pyqtSignal(str)

    # 支持的图片格式
    IMAGE_FILTERS = "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)"

    def __init__(self, parent: Optional[QWidget] = None, label: str = "背景图片"):
        super().__init__(parent)
        self._image_path = ""
        self._label = label
        self._create_ui()
        self._apply_theme()

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(dp(8))

        # 标签行
        label = QLabel(self._label)
        label.setObjectName("image_picker_label")
        main_layout.addWidget(label)

        # 控件行
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(dp(8))

        # 图片预览
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(dp(48), dp(48))
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setScaledContents(True)
        controls_layout.addWidget(self.preview_label)

        # 路径输入框（只读）
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("未选择图片")
        self.path_input.setReadOnly(True)
        controls_layout.addWidget(self.path_input, stretch=1)

        # 选择按钮
        self.browse_btn = QPushButton("选择")
        self.browse_btn.setFixedWidth(dp(60))
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse_image)
        controls_layout.addWidget(self.browse_btn)

        # 清除按钮
        self.clear_btn = QPushButton("清除")
        self.clear_btn.setFixedWidth(dp(60))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_image)
        controls_layout.addWidget(self.clear_btn)

        main_layout.addLayout(controls_layout)

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 标签样式
        label = self.findChild(QLabel, "image_picker_label")
        if label:
            label.setStyleSheet(f"""
                QLabel#image_picker_label {{
                    font-family: {palette.ui_font};
                    font-size: {sp(13)}px;
                    color: {palette.text_primary};
                    font-weight: 500;
                }}
            """)

        # 预览框样式
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px dashed {palette.border_color};
                border-radius: {dp(4)}px;
            }}
        """)

        # 路径输入框样式
        self.path_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(10)}px;
            }}
        """)

        # 按钮样式
        btn_style = f"""
            QPushButton {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.browse_btn.setStyleSheet(btn_style)
        self.clear_btn.setStyleSheet(btn_style)

        self._update_preview()

    def _update_preview(self):
        """更新预览图"""
        if self._image_path and os.path.exists(self._image_path):
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                # 缩放到预览大小
                scaled = pixmap.scaled(
                    dp(48), dp(48),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                return

        # 显示空状态
        self.preview_label.clear()
        self.preview_label.setText("无")

    def _browse_image(self):
        """打开文件选择对话框"""
        # 使用上次选择的目录，或默认用户图片目录
        start_dir = ""
        if self._image_path:
            start_dir = os.path.dirname(self._image_path)
        if not start_dir:
            start_dir = os.path.expanduser("~/Pictures")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景图片",
            start_dir,
            self.IMAGE_FILTERS
        )

        if file_path:
            # set_path 会自动发射 image_changed 信号
            self.set_path(file_path)

    def _clear_image(self):
        """清除图片"""
        self._image_path = ""
        self.path_input.clear()
        self._update_preview()
        self.image_changed.emit("")

    def get_path(self) -> str:
        """获取当前图片路径"""
        return self._image_path

    def set_path(self, path: str, emit_signal: bool = True):
        """设置图片路径

        Args:
            path: 图片文件路径
            emit_signal: 是否发射变更信号
        """
        self._image_path = path or ""
        self.path_input.setText(path or "")
        self._update_preview()
        if emit_signal and path:
            self.image_changed.emit(path)

    # 属性接口
    path = property(get_path, set_path)
