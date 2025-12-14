# -*- coding: utf-8 -*-
"""
帧缩略图控件
用于在序列帧预览页面显示和选择帧
采用 Claude 暖色主题风格
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image


class FrameThumbnail(QFrame):
    """帧缩略图控件"""

    # 点击信号
    clicked = pyqtSignal(int)  # 参数为帧索引

    def __init__(self, frame_index: int, image: Image.Image, thumb_size: int = 70, parent=None):
        """
        初始化帧缩略图

        Args:
            frame_index: 帧索引
            image: PIL Image对象
            thumb_size: 缩略图大小
            parent: 父控件
        """
        super().__init__(parent)
        self.frame_index = frame_index
        self.selected = False
        self.order_number = 0  # 选中顺序号

        self.setup_ui(image, thumb_size)
        self.update_style()

    def setup_ui(self, image: Image.Image, thumb_size: int):
        """设置UI"""
        self.setFixedHeight(thumb_size + 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # 缩略图
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(thumb_size, thumb_size)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 1px solid #ddd9d3;
                border-radius: 6px;
            }
        """)
        self.set_image(image, thumb_size)
        layout.addWidget(self.thumb_label)

        # 序号标签
        self.order_label = QLabel("")
        self.order_label.setFixedWidth(30)
        self.order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.order_label.setStyleSheet("""
            QLabel {
                color: #c6613f;
                font-weight: bold;
                font-size: 14px;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.order_label)

        layout.addStretch()

        # 帧索引标签
        self.index_label = QLabel(f"#{self.frame_index}")
        self.index_label.setStyleSheet("""
            QLabel {
                color: #615e5a;
                font-size: 11px;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.index_label)

    def set_image(self, image: Image.Image, thumb_size: int):
        """设置缩略图图片"""
        # 创建缩略图
        thumb = image.copy()
        thumb.thumbnail((thumb_size - 4, thumb_size - 4), Image.LANCZOS)

        # 转换为QPixmap
        if thumb.mode != "RGBA":
            thumb = thumb.convert("RGBA")

        data = thumb.tobytes("raw", "RGBA")
        qimage = QImage(data, thumb.width, thumb.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        self.thumb_label.setPixmap(pixmap)

    def set_selected(self, selected: bool, order: int = 0):
        """设置选中状态"""
        self.selected = selected
        self.order_number = order
        self.order_label.setText(str(order) if selected and order > 0 else "")
        self.update_style()

    def update_style(self):
        """更新样式"""
        if self.selected:
            # 选中状态 - 使用 Claude 主题色
            self.setStyleSheet("""
                FrameThumbnail {
                    background-color: rgba(198, 97, 63, 0.12);
                    border: 2px solid #c6613f;
                    border-radius: 8px;
                }
            """)
            self.thumb_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    border: 2px solid #c6613f;
                    border-radius: 6px;
                }
            """)
        else:
            # 未选中状态 - 暖色调背景
            self.setStyleSheet("""
                FrameThumbnail {
                    background-color: #ebe8e3;
                    border: 2px solid transparent;
                    border-radius: 8px;
                }
                FrameThumbnail:hover {
                    background-color: #e8e4df;
                    border: 2px solid #ddd9d3;
                }
            """)
            self.thumb_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    border: 1px solid #ddd9d3;
                    border-radius: 6px;
                }
            """)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.frame_index)
        super().mousePressEvent(event)
