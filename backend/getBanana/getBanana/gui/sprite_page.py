# -*- coding: utf-8 -*-
"""
序列帧预览页面
用于分割精灵图并预览动画效果
"""

import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QScrollArea, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PIL import Image

from backend import ImageProcessor
from .widgets import FrameThumbnail


class SpritePage(QWidget):
    """序列帧预览页面"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 数据
        self.image_files: List[str] = []  # 可用图片列表
        self.current_image_path: Optional[str] = None
        self.frames: List[Image.Image] = []  # 分割后的帧
        self.selected_order: List[int] = []  # 选中的帧顺序
        self.current_frame: int = 0  # 当前播放帧
        self.playing: bool = False  # 播放状态
        self.thumbnails: List[FrameThumbnail] = []  # 缩略图控件列表

        # 定时器
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.next_animation_frame)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5)
        main_layout.addWidget(splitter)

        # ===== 左侧：帧列表 =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel("帧列表")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_bar.addWidget(title_label)
        self.selected_count_label = QLabel("(已选: 0)")
        self.selected_count_label.setStyleSheet("color: #666;")
        title_bar.addWidget(self.selected_count_label)
        title_bar.addStretch()
        left_layout.addLayout(title_bar)

        # 操作按钮区域
        action_group = QGroupBox()
        action_group.setStyleSheet("QGroupBox { border: none; padding: 0; margin: 0; }")
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        action_layout.addWidget(self.select_all_btn)
        
        self.invert_btn = QPushButton("反选")
        self.invert_btn.clicked.connect(self.invert_selection)
        action_layout.addWidget(self.invert_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_selection)
        action_layout.addWidget(self.clear_btn)
        
        left_layout.addWidget(action_group)

        # 缩略图滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: 1px solid #ddd; border-radius: 4px; background-color: #fff; }
            QScrollBar:vertical { width: 10px; }
        """)

        self.thumb_container = QWidget()
        self.thumb_container.setStyleSheet("background-color: #f9f9f9;")
        self.thumb_layout = QVBoxLayout(self.thumb_container)
        self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.thumb_layout.setSpacing(8)
        self.thumb_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_area.setWidget(self.thumb_container)

        left_layout.addWidget(self.scroll_area)
        left_widget.setMinimumWidth(220)
        splitter.addWidget(left_widget)

        # ===== 右侧：控制和预览 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(15)

        # 1. 顶部控制区 (图片选择 + 分割参数)
        top_control_group = QGroupBox("图片源与分割设置")
        top_control_layout = QFormLayout(top_control_group)
        top_control_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # 图片选择
        img_sel_layout = QHBoxLayout()
        self.image_combo = QComboBox()
        self.image_combo.setMinimumWidth(250)
        self.image_combo.currentIndexChanged.connect(self.on_image_selected)
        img_sel_layout.addWidget(self.image_combo, 1)
        
        self.browse_btn = QPushButton("📂 打开...")
        self.browse_btn.clicked.connect(self.browse_file)
        img_sel_layout.addWidget(self.browse_btn)
        top_control_layout.addRow("选择图片:", img_sel_layout)

        # 分割参数
        split_params_layout = QHBoxLayout()
        
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(1)
        self.rows_spin.setPrefix("行: ")
        split_params_layout.addWidget(self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 50)
        self.cols_spin.setValue(1)
        self.cols_spin.setPrefix("列: ")
        split_params_layout.addWidget(self.cols_spin)

        self.load_btn = QPushButton("✂️ 加载并分割")
        self.load_btn.clicked.connect(self.load_and_split)
        split_params_layout.addWidget(self.load_btn)
        
        split_params_layout.addStretch()
        top_control_layout.addRow("分割参数:", split_params_layout)

        right_layout.addWidget(top_control_group)

        # 2. 预览区域 (占据主要空间)
        preview_group = QGroupBox("动画预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(2, 10, 2, 2)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("background-color: #333; border-radius: 4px;")
        self.preview_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label = QLabel("请选择图片并加载分割")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #888; font-size: 16px;")
        self.preview_scroll.setWidget(self.preview_label)
        
        preview_layout.addWidget(self.preview_scroll)
        right_layout.addWidget(preview_group, 1)

        # 3. 底部播放控制
        bottom_control_group = QGroupBox("播放控制")
        bottom_layout = QHBoxLayout(bottom_control_group)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedWidth(40)
        self.prev_btn.clicked.connect(self.prev_frame)
        bottom_layout.addWidget(self.prev_btn)

        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setFixedWidth(80)
        self.play_btn.clicked.connect(self.toggle_play)
        bottom_layout.addWidget(self.play_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedWidth(40)
        self.next_btn.clicked.connect(self.next_frame)
        bottom_layout.addWidget(self.next_btn)

        bottom_layout.addSpacing(20)
        
        bottom_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(12)
        self.fps_spin.valueChanged.connect(self.update_fps)
        bottom_layout.addWidget(self.fps_spin)

        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(QLabel("缩放:"))
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(1.0)
        self.scale_spin.valueChanged.connect(self.update_preview)
        bottom_layout.addWidget(self.scale_spin)

        bottom_layout.addStretch()

        # 信息标签
        info_layout = QVBoxLayout()
        self.frame_label = QLabel("帧: 0/0")
        self.size_label = QLabel("尺寸: -")
        info_layout.addWidget(self.frame_label)
        info_layout.addWidget(self.size_label)
        bottom_layout.addLayout(info_layout)

        bottom_layout.addSpacing(20)
        self.export_btn = QPushButton("💾 导出选中帧")
        self.export_btn.clicked.connect(self.export_frames)
        bottom_layout.addWidget(self.export_btn)

        right_layout.addWidget(bottom_control_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 750]) # Set initial sizes

    def set_image_files(self, files: List[str]):
        """设置可用的图片文件列表"""
        self.image_files = files
        self.update_image_combo()

    def add_image_file(self, path: str):
        """添加图片文件"""
        if path and path not in self.image_files:
            self.image_files.append(path)
            self.update_image_combo()

    def update_image_combo(self):
        """更新图片下拉框"""
        self.image_combo.clear()
        for path in self.image_files:
            self.image_combo.addItem(os.path.basename(path), path)
        if self.image_files:
            self.image_combo.setCurrentIndex(0)

    def on_image_selected(self, index: int):
        """图片选择改变"""
        if index >= 0 and index < len(self.image_files):
            self.current_image_path = self.image_files[index]
            # 清空当前数据
            self.clear_frames()

    def browse_file(self):
        """浏览文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择精灵图",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*.*)"
        )
        if path:
            self.add_image_file(path)
            # 选择这个文件
            index = self.image_files.index(path)
            self.image_combo.setCurrentIndex(index)

    def clear_frames(self):
        """清空帧数据"""
        self.stop_play()
        self.frames = []
        self.selected_order = []
        self.current_frame = 0
        self.clear_thumbnails()
        self.preview_label.clear()
        self.preview_label.setText("请加载图片")
        self.frame_label.setText("帧: 0/0")
        self.size_label.setText("尺寸: -")
        self.selected_count_label.setText("(已选: 0)")

    def clear_thumbnails(self):
        """清空缩略图"""
        for thumb in self.thumbnails:
            thumb.deleteLater()
        self.thumbnails = []

    def load_and_split(self):
        """加载并分割图片"""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "错误", "请先选择有效的图片文件")
            return

        rows = self.rows_spin.value()
        cols = self.cols_spin.value()

        # 加载图片
        img = ImageProcessor.load_image(self.current_image_path)
        if not img:
            QMessageBox.warning(self, "错误", "加载图片失败")
            return

        # 检查尺寸
        frame_w = img.width // cols
        frame_h = img.height // cols
        if frame_w < 1 or frame_h < 1:
            QMessageBox.warning(self, "错误", "图片太小，无法按指定行列分割")
            return

        # 分割
        self.frames = ImageProcessor.split_sprite_sheet(img, rows, cols)
        if not self.frames:
            QMessageBox.warning(self, "错误", "分割失败")
            return

        # 默认全选
        self.selected_order = list(range(len(self.frames)))
        self.current_frame = 0
        self.size_label.setText(f"尺寸: {frame_w}x{frame_h}")

        # 创建缩略图
        self.create_thumbnails()
        self.update_selection_display()
        self.update_preview()
        self.update_frame_label()

    def create_thumbnails(self):
        """创建缩略图"""
        self.clear_thumbnails()

        for i, frame in enumerate(self.frames):
            thumb = FrameThumbnail(i, frame)
            thumb.clicked.connect(self.on_thumbnail_clicked)
            self.thumb_layout.addWidget(thumb)
            self.thumbnails.append(thumb)

    def on_thumbnail_clicked(self, frame_index: int):
        """缩略图点击"""
        if frame_index in self.selected_order:
            self.selected_order.remove(frame_index)
        else:
            self.selected_order.append(frame_index)

        self.update_selection_display()

        if self.selected_order:
            self.current_frame = len(self.selected_order) - 1
            self.update_preview()
        else:
            self.preview_label.clear()

        self.update_frame_label()

    def update_selection_display(self):
        """更新选中状态显示"""
        for thumb in self.thumbnails:
            if thumb.frame_index in self.selected_order:
                order = self.selected_order.index(thumb.frame_index) + 1
                thumb.set_selected(True, order)
            else:
                thumb.set_selected(False)

        self.selected_count_label.setText(f"(已选: {len(self.selected_order)})")

    def select_all(self):
        """全选"""
        self.selected_order = list(range(len(self.frames)))
        self.current_frame = 0
        self.update_selection_display()
        self.update_frame_label()
        if self.frames:
            self.update_preview()

    def clear_selection(self):
        """清空选择"""
        self.selected_order = []
        self.current_frame = 0
        self.update_selection_display()
        self.update_frame_label()
        self.preview_label.clear()

    def invert_selection(self):
        """反选"""
        unselected = [i for i in range(len(self.frames)) if i not in self.selected_order]
        self.selected_order = unselected
        self.current_frame = 0
        self.update_selection_display()
        self.update_frame_label()
        if self.selected_order:
            self.update_preview()
        else:
            self.preview_label.clear()

    def update_preview(self):
        """更新预览"""
        if not self.frames or not self.selected_order:
            return

        frame_idx = self.selected_order[self.current_frame % len(self.selected_order)]
        frame = self.frames[frame_idx]
        scale = self.scale_spin.value()

        # 缩放
        if scale != 1.0:
            frame = ImageProcessor.scale_image(frame, scale)

        # 转换为QPixmap
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")
        data = frame.tobytes("raw", "RGBA")
        qimage = QImage(data, frame.width, frame.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        self.preview_label.setPixmap(pixmap)
        self.preview_label.setFixedSize(pixmap.size()) # Update label size to fit image

    def update_frame_label(self):
        """更新帧标签"""
        total = len(self.selected_order)
        if total > 0:
            current = self.current_frame % total + 1
            frame_idx = self.selected_order[self.current_frame % total]
            self.frame_label.setText(f"帧: {current}/{total} (#{frame_idx})")
        else:
            self.frame_label.setText("帧: 0/0")

    def toggle_play(self):
        """切换播放"""
        if not self.selected_order:
            QMessageBox.warning(self, "提示", "请先选择要播放的帧")
            return

        if self.playing:
            self.stop_play()
        else:
            self.start_play()

    def start_play(self):
        """开始播放"""
        self.playing = True
        self.play_btn.setText("⏸ 暂停")
        delay = int(1000 / self.fps_spin.value())
        self.play_timer.start(delay)

    def stop_play(self):
        """停止播放"""
        self.playing = False
        self.play_btn.setText("▶ 播放")
        self.play_timer.stop()

    def update_fps(self):
        """更新FPS"""
        if self.playing:
            self.start_play() # Restart timer with new delay

    def next_animation_frame(self):
        """下一动画帧"""
        if not self.selected_order:
            return
        self.current_frame = (self.current_frame + 1) % len(self.selected_order)
        self.update_preview()
        self.update_frame_label()

    def prev_frame(self):
        """上一帧"""
        if not self.selected_order:
            return
        self.current_frame = (self.current_frame - 1) % len(self.selected_order)
        self.update_preview()
        self.update_frame_label()

    def next_frame(self):
        """下一帧"""
        if not self.selected_order:
            return
        self.current_frame = (self.current_frame + 1) % len(self.selected_order)
        self.update_preview()
        self.update_frame_label()

    def export_frames(self):
        """导出帧"""
        if not self.selected_order:
            QMessageBox.warning(self, "警告", "请先选择要导出的帧")
            return

        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not dir_path:
            return

        base_name = "sprite"
        if self.current_image_path:
            base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]

        count, error = ImageProcessor.export_frames(
            self.frames, self.selected_order, dir_path, base_name
        )

        if error:
            QMessageBox.critical(self, "错误", f"导出失败: {error}")
        else:
            QMessageBox.information(self, "成功", f"已导出 {count} 帧到:\n{dir_path}")