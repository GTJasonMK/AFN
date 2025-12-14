# -*- coding: utf-8 -*-
"""
图片生成页面
使用API生成图片的界面
"""

import os
import random
import time
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QTextEdit, QProgressBar, QFileDialog,
    QMessageBox, QCheckBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent

from backend import Config, ApiClient, Logger
from .workers import GeneratorThread


class GeneratorPage(QWidget):
    """图片生成页面"""

    # 信号：生成完成
    images_generated = pyqtSignal(list)  # 参数为文件路径列表

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.api_client = ApiClient(config.API_BASE_URL)
        self.logger = Logger()  # 日志记录器
        self.generated_files: List[str] = []
        self.generator_thread: Optional[GeneratorThread] = None

        # 提示词历史浏览
        self.history_index = -1
        self.current_input = ""

        # 日志记录用的临时变量
        self._gen_start_time: float = 0
        self._gen_params: dict = {}

        self.setup_ui()
        self.load_settings()

        # 安装事件过滤器以处理提示词编辑框的上下键
        self.prompt_edit.installEventFilter(self)

    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top Section: Settings Groups
        top_layout = QHBoxLayout()
        
        # Group 1: Basic Configuration
        config_group = QGroupBox("基础配置")
        config_layout = QFormLayout(config_group)
        config_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # API Key
        api_key_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("请输入您的 API Key")
        api_key_layout.addWidget(self.api_key_edit)
        self.show_key_cb = QCheckBox("显示")
        self.show_key_cb.toggled.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_key_cb)
        config_layout.addRow("API Key:", api_key_layout)

        # Model & Style
        self.model_combo = QComboBox()
        self.model_combo.addItems(Config.MODELS)
        config_layout.addRow("模型:", self.model_combo)

        self.style_combo = QComboBox()
        self.style_combo.addItems([s[0] for s in Config.STYLES])
        config_layout.addRow("风格:", self.style_combo)
        
        top_layout.addWidget(config_group, 1)

        # Group 2: Image Parameters
        params_group = QGroupBox("图片参数")
        params_layout = QGridLayout(params_group)
        
        params_layout.addWidget(QLabel("宽高比:"), 0, 0)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(Config.ASPECT_RATIOS)
        params_layout.addWidget(self.ratio_combo, 0, 1)

        params_layout.addWidget(QLabel("分辨率:"), 1, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(Config.RESOLUTIONS)
        params_layout.addWidget(self.resolution_combo, 1, 1)

        params_layout.addWidget(QLabel("生成数量:"), 2, 0)
        self.count_combo = QComboBox()
        self.count_combo.addItems(Config.COUNTS)
        params_layout.addWidget(self.count_combo, 2, 1)

        top_layout.addWidget(params_group, 1)

        # Group 3: Advanced Settings
        adv_group = QGroupBox("高级设置")
        adv_layout = QGridLayout(adv_group)

        adv_layout.addWidget(QLabel("质量预设:"), 0, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(Config.QUALITY_PRESETS.keys()))
        self.quality_combo.currentTextChanged.connect(self.on_quality_changed)
        adv_layout.addWidget(self.quality_combo, 0, 1)

        adv_layout.addWidget(QLabel("Temperature:"), 1, 0)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setDecimals(1)
        adv_layout.addWidget(self.temp_spin, 1, 1)

        adv_layout.addWidget(QLabel("Seed:"), 2, 0)
        seed_layout = QHBoxLayout()
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("随机")
        seed_layout.addWidget(self.seed_edit)
        self.random_seed_btn = QPushButton("🎲")
        self.random_seed_btn.setToolTip("生成随机种子")
        self.random_seed_btn.setFixedWidth(30)
        self.random_seed_btn.clicked.connect(self.random_seed)
        seed_layout.addWidget(self.random_seed_btn)
        adv_layout.addLayout(seed_layout, 2, 1)

        top_layout.addWidget(adv_group, 1)
        main_layout.addLayout(top_layout)

        # Middle Section: Prompts
        prompt_group = QGroupBox("提示词 (Prompt)")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setMinimumHeight(80)
        self.prompt_edit.setPlaceholderText("在此输入图片描述... (支持中文，按上下键查看历史)")
        self.prompt_edit.setText("一只可爱的香蕉卡通角色，微笑表情")
        prompt_layout.addWidget(self.prompt_edit)

        self.neg_prompt_edit = QTextEdit()
        self.neg_prompt_edit.setMinimumHeight(50)
        self.neg_prompt_edit.setMaximumHeight(60)
        self.neg_prompt_edit.setPlaceholderText("负面提示词 (Negative Prompt) - 可选，输入要避免的内容...")
        prompt_layout.addWidget(self.neg_prompt_edit)
        
        main_layout.addWidget(prompt_group)

        # Bottom Section: Output & Actions
        bottom_group = QGroupBox("输出与操作")
        bottom_layout = QVBoxLayout(bottom_group)

        # Save Path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        self.save_dir_edit = QLineEdit()
        path_layout.addWidget(self.save_dir_edit)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_save_dir)
        path_layout.addWidget(self.browse_btn)
        bottom_layout.addLayout(path_layout)

        # Action Buttons & Status
        action_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("🚀 开始生成")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.generate_btn.clicked.connect(self.generate)
        action_layout.addWidget(self.generate_btn, 2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        action_layout.addWidget(self.progress_bar, 3)

        # Result Actions
        self.view_btn = QPushButton("查看图片")
        self.view_btn.clicked.connect(self.view_result)
        self.view_btn.hide()
        self.view_btn.setProperty("secondary", True)
        action_layout.addWidget(self.view_btn)

        self.folder_btn = QPushButton("打开目录")
        self.folder_btn.clicked.connect(self.open_folder)
        self.folder_btn.hide()
        self.folder_btn.setProperty("secondary", True)
        action_layout.addWidget(self.folder_btn)

        self.goto_sprite_btn = QPushButton("去制作序列帧")
        self.goto_sprite_btn.clicked.connect(self.goto_sprite_page)
        self.goto_sprite_btn.hide()
        self.goto_sprite_btn.setProperty("secondary", True)
        action_layout.addWidget(self.goto_sprite_btn)

        bottom_layout.addLayout(action_layout)
        
        # Status Label
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("color: #666; margin-top: 5px;")
        bottom_layout.addWidget(self.status_label)

        main_layout.addWidget(bottom_group)

    def load_settings(self):
        """加载设置"""
        self.api_key_edit.setText(self.config.get("api_key", ""))
        self.model_combo.setCurrentText(self.config.get("last_model", "nano-banana-pro"))
        self.style_combo.setCurrentText(self.config.get("last_style", "无"))
        self.ratio_combo.setCurrentText(self.config.get("last_ratio", "1:1"))
        self.resolution_combo.setCurrentText(self.config.get("last_resolution", "原始"))
        self.count_combo.setCurrentText(self.config.get("last_count", "2"))
        self.quality_combo.setCurrentText(self.config.get("last_quality", "标准"))
        self.temp_spin.setValue(self.config.get("temperature", 0.7))
        self.seed_edit.setText(self.config.get("seed", ""))
        self.save_dir_edit.setText(self.config.get("save_dir", ""))

    def save_settings(self):
        """保存设置"""
        self.config.set("api_key", self.api_key_edit.text())
        self.config.set("last_model", self.model_combo.currentText())
        self.config.set("last_style", self.style_combo.currentText())
        self.config.set("last_ratio", self.ratio_combo.currentText())
        self.config.set("last_resolution", self.resolution_combo.currentText())
        self.config.set("last_count", self.count_combo.currentText())
        self.config.set("last_quality", self.quality_combo.currentText())
        self.config.set("temperature", self.temp_spin.value())
        self.config.set("seed", self.seed_edit.text())
        self.config.set("save_dir", self.save_dir_edit.text())
        self.config.save()

    def toggle_api_key_visibility(self, checked: bool):
        """切换API Key显示"""
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def on_quality_changed(self, quality: str):
        """质量预设改变"""
        preset = self.config.get_quality_preset(quality)
        if preset:
            self.temp_spin.setValue(preset["temperature"])

    def random_seed(self):
        """生成随机种子"""
        self.seed_edit.setText(str(random.randint(1, 999999999)))

    def browse_save_dir(self):
        """浏览保存目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择保存目录",
            self.save_dir_edit.text()
        )
        if dir_path:
            self.save_dir_edit.setText(dir_path)

    def generate(self):
        """开始生成"""
        # 验证输入
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "错误", "请输入API Key")
            return

        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "错误", "请输入提示词")
            return

        save_dir = self.save_dir_edit.text().strip()
        if not save_dir or not os.path.isdir(save_dir):
            QMessageBox.warning(self, "错误", "请选择有效的保存目录")
            return

        # 构建完整提示词
        full_prompt = prompt
        style_suffix = self.config.get_style_suffix(self.style_combo.currentText())
        if style_suffix:
            full_prompt += f"，{style_suffix}"

        neg_prompt = self.neg_prompt_edit.toPlainText().strip()
        if neg_prompt:
            full_prompt += f"\n\n避免: {neg_prompt}"

        # 保存提示词到历史
        self.config.add_prompt_to_history(prompt)

        # 获取参数
        preset = self.config.get_quality_preset(self.quality_combo.currentText())
        max_tokens = preset["max_tokens"] if preset else 4096
        temperature = preset["temperature"] if preset else self.temp_spin.value()
        count = int(self.count_combo.currentText())
        ratio = self.config.get_ratio_tuple(self.ratio_combo.currentText())
        resolution = self.resolution_combo.currentText()

        # 记录开始时间和参数（用于日志）
        self._gen_start_time = time.time()
        self._gen_params = {
            "model": self.model_combo.currentText(),
            "style": self.style_combo.currentText(),
            "ratio": self.ratio_combo.currentText(),
            "resolution": resolution,
            "count": count,
            "quality": self.quality_combo.currentText(),
            "temperature": temperature,
            "seed": self.seed_edit.text(),
            "prompt": prompt,
            "negative_prompt": neg_prompt,
            "full_prompt": full_prompt,
            "save_dir": save_dir
        }

        # 隐藏结果按钮
        self.view_btn.hide()
        self.folder_btn.hide()
        self.goto_sprite_btn.hide()
        self.generated_files = []

        # 开始生成
        self.generate_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("正在生成图片...")

        # 创建并启动线程
        self.generator_thread = GeneratorThread(
            api_client=self.api_client,
            api_key=api_key,
            prompt=full_prompt,
            model=self.model_combo.currentText(),
            max_tokens=max_tokens,
            temperature=temperature,
            count=count,
            ratio=ratio,
            resolution=resolution,
            save_dir=save_dir
        )
        self.generator_thread.progress.connect(self.on_progress)
        self.generator_thread.finished.connect(self.on_finished)
        self.generator_thread.error.connect(self.on_error)
        self.generator_thread.start()

    def on_progress(self, msg: str):
        """进度更新"""
        self.status_label.setText(msg)

    def on_finished(self, files: List[str]):
        """生成完成"""
        self.generate_btn.setEnabled(True)
        self.progress_bar.hide()
        self.generated_files = files
        self.status_label.setText(f"生成完成，共 {len(files)} 张图片")
        self.view_btn.show()
        self.folder_btn.show()
        self.goto_sprite_btn.show()
        self.save_settings()

        # 记录日志
        duration = time.time() - self._gen_start_time
        self.logger.log_generation(
            model=self._gen_params.get("model", ""),
            style=self._gen_params.get("style", ""),
            ratio=self._gen_params.get("ratio", ""),
            resolution=self._gen_params.get("resolution", ""),
            count=self._gen_params.get("count", 0),
            quality=self._gen_params.get("quality", ""),
            temperature=self._gen_params.get("temperature", 0.7),
            seed=self._gen_params.get("seed", ""),
            prompt=self._gen_params.get("prompt", ""),
            negative_prompt=self._gen_params.get("negative_prompt", ""),
            full_prompt=self._gen_params.get("full_prompt", ""),
            success=True,
            image_paths=files,
            duration_seconds=duration,
            save_dir=self._gen_params.get("save_dir", "")
        )

        # 发送信号
        self.images_generated.emit(files)

    def on_error(self, msg: str):
        """生成错误"""
        self.generate_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText("生成失败")

        # 记录日志
        duration = time.time() - self._gen_start_time
        self.logger.log_generation(
            model=self._gen_params.get("model", ""),
            style=self._gen_params.get("style", ""),
            ratio=self._gen_params.get("ratio", ""),
            resolution=self._gen_params.get("resolution", ""),
            count=self._gen_params.get("count", 0),
            quality=self._gen_params.get("quality", ""),
            temperature=self._gen_params.get("temperature", 0.7),
            seed=self._gen_params.get("seed", ""),
            prompt=self._gen_params.get("prompt", ""),
            negative_prompt=self._gen_params.get("negative_prompt", ""),
            full_prompt=self._gen_params.get("full_prompt", ""),
            success=False,
            error_message=msg,
            duration_seconds=duration,
            save_dir=self._gen_params.get("save_dir", "")
        )

        QMessageBox.critical(self, "生成失败", msg)

    def view_result(self):
        """查看结果"""
        if self.generated_files:
            os.startfile(self.generated_files[0])

    def open_folder(self):
        """打开文件夹"""
        if self.generated_files:
            os.startfile(os.path.dirname(self.generated_files[0]))

    def goto_sprite_page(self):
        """切换到序列帧预览页面"""
        # 通过父窗口切换标签页
        parent = self.parent()
        while parent:
            if hasattr(parent, 'switch_to_sprite_page'):
                parent.switch_to_sprite_page()
                break
            parent = parent.parent()

    def eventFilter(self, obj, event):
        """事件过滤器，处理提示词编辑框的上下键"""
        if obj == self.prompt_edit and event.type() == QEvent.Type.KeyPress:
            history = self.config.get_prompt_history()
            if event.key() == Qt.Key.Key_Up and history:
                if self.history_index == -1:
                    self.current_input = self.prompt_edit.toPlainText()
                if self.history_index < len(history) - 1:
                    self.history_index += 1
                    idx = len(history) - 1 - self.history_index
                    self.prompt_edit.setPlainText(history[idx])
                    # 将光标移到末尾
                    cursor = self.prompt_edit.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.prompt_edit.setTextCursor(cursor)
                return True  # 事件已处理
            elif event.key() == Qt.Key.Key_Down and history:
                if self.history_index > 0:
                    self.history_index -= 1
                    idx = len(history) - 1 - self.history_index
                    self.prompt_edit.setPlainText(history[idx])
                    cursor = self.prompt_edit.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.prompt_edit.setTextCursor(cursor)
                elif self.history_index == 0:
                    self.history_index = -1
                    self.prompt_edit.setPlainText(self.current_input)
                    cursor = self.prompt_edit.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.prompt_edit.setTextCursor(cursor)
                return True  # 事件已处理
        return super().eventFilter(obj, event)