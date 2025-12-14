# -*- coding: utf-8 -*-
"""
主窗口模块
整合图片生成和序列帧预览功能
"""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout
)
from PyQt6.QtCore import Qt

from backend import Config
from .generator_page import GeneratorPage
from .sprite_page import SpritePage


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 加载配置
        self.config = Config()

        # 设置窗口
        self.setWindowTitle("Banana Studio")
        self.setMinimumSize(1000, 700)
        self.resize(1050, 750)

        # 创建UI
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 中央控件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 图片生成页面
        self.generator_page = GeneratorPage(self.config)
        self.generator_page.images_generated.connect(self.on_images_generated)
        self.tab_widget.addTab(self.generator_page, "  图片生成  ")

        # 序列帧预览页面
        self.sprite_page = SpritePage()
        self.tab_widget.addTab(self.sprite_page, "  序列帧预览  ")

    def on_images_generated(self, files: list):
        """图片生成完成"""
        # 将生成的图片传递给序列帧页面
        self.sprite_page.set_image_files(files)

    def switch_to_sprite_page(self):
        """切换到序列帧预览页面"""
        self.tab_widget.setCurrentIndex(1)

    def closeEvent(self, event):
        """关闭事件"""
        # 停止播放
        self.sprite_page.stop_play()
        # 保存配置
        self.generator_page.save_settings()
        event.accept()
