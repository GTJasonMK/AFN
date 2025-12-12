"""
高级配置界面 - 书籍风格

管理系统级配置参数，如章节生成、大纲阈值等。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QFrame, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors


class AdvancedSettingsWidget(QWidget):
    """高级配置管理界面 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.config_data = {}
        self._create_ui_structure()
        self._apply_styles()
        self.loadConfig()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        layout.setSpacing(dp(20))

        # 说明文字
        self.desc_label = QLabel("这些配置会影响章节生成和大纲规划的行为。")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 章节生成配置组
        self.chapter_group = self._create_chapter_generation_group()
        layout.addWidget(self.chapter_group)

        # 大纲配置组
        self.outline_group = self._create_outline_config_group()
        layout.addWidget(self.outline_group)

        layout.addStretch()

        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        # 重置按钮
        self.reset_btn = QPushButton("恢复默认值")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(lambda: self.resetToDefaults())
        button_layout.addWidget(self.reset_btn)

        # 保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(lambda: self.saveConfig())
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _create_chapter_generation_group(self):
        """创建章节生成配置组"""
        group = QGroupBox("章节生成")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(20), dp(16), dp(20), dp(20))
        form_layout.setSpacing(dp(16))

        # 候选版本数
        version_widget = QWidget()
        version_layout = QHBoxLayout(version_widget)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(dp(12))

        self.version_count_spinbox = QSpinBox()
        self.version_count_spinbox.setRange(1, 5)
        self.version_count_spinbox.setValue(3)
        self.version_count_spinbox.setFixedWidth(dp(80))
        self.version_count_spinbox.setMinimumHeight(dp(36))
        version_layout.addWidget(self.version_count_spinbox)

        self.version_help = QLabel("每章生成的候选版本数（1-5个）")
        version_layout.addWidget(self.version_help)
        version_layout.addStretch()

        self.version_label = QLabel("候选版本数量")
        form_layout.addRow(self.version_label, version_widget)

        # 并行生成开关
        parallel_widget = QWidget()
        parallel_layout = QHBoxLayout(parallel_widget)
        parallel_layout.setContentsMargins(0, 0, 0, 0)
        parallel_layout.setSpacing(dp(12))

        self.parallel_checkbox = QCheckBox("启用并行生成")
        self.parallel_checkbox.setChecked(True)
        parallel_layout.addWidget(self.parallel_checkbox)

        self.parallel_help = QLabel("多个版本同时生成，显著提升速度")
        parallel_layout.addWidget(self.parallel_help)
        parallel_layout.addStretch()

        form_layout.addRow("", parallel_widget)

        return group

    def _create_outline_config_group(self):
        """创建大纲配置组"""
        group = QGroupBox("大纲规划")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(20), dp(16), dp(20), dp(20))
        form_layout.setSpacing(dp(16))

        # 分部大纲阈值
        threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.setSpacing(dp(12))

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(10, 100)
        self.threshold_spinbox.setValue(25)
        self.threshold_spinbox.setSingleStep(5)
        self.threshold_spinbox.setFixedWidth(dp(80))
        self.threshold_spinbox.setMinimumHeight(dp(36))
        threshold_layout.addWidget(self.threshold_spinbox)

        self.threshold_help = QLabel("超过此章节数将先生成分部大纲（10-100章）")
        threshold_layout.addWidget(self.threshold_help)
        threshold_layout.addStretch()

        self.threshold_label = QLabel("长篇分部阈值")
        form_layout.addRow(self.threshold_label, threshold_widget)

        return group

    def _apply_styles(self):
        """应用书籍风格主题"""
        bg_primary = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        ui_font = theme_manager.ui_font()

        # 说明文字样式
        self.desc_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_secondary};
                padding: {dp(4)}px 0;
            }}
        """)

        # GroupBox样式
        group_style = f"""
            QGroupBox {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: 600;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
                margin-top: {dp(8)}px;
                padding-top: {dp(12)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {dp(16)}px;
                padding: 0 {dp(8)}px;
                background-color: {bg_primary};
            }}
        """
        self.chapter_group.setStyleSheet(group_style)
        self.outline_group.setStyleSheet(group_style)

        # 标签样式
        label_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: 500;
                color: {text_primary};
                background: transparent;
            }}
        """
        self.version_label.setStyleSheet(label_style)
        self.threshold_label.setStyleSheet(label_style)

        # 帮助文字样式
        help_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                background: transparent;
            }}
        """
        self.version_help.setStyleSheet(help_style)
        self.parallel_help.setStyleSheet(help_style)
        self.threshold_help.setStyleSheet(help_style)

        # SpinBox样式
        spinbox_style = f"""
            QSpinBox {{
                font-family: {ui_font};
                padding: {dp(8)}px {dp(12)}px;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                background-color: {bg_secondary};
                color: {text_primary};
                font-size: {sp(13)}px;
            }}
            QSpinBox:focus {{
                border: 2px solid {accent_color};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                background-color: {bg_secondary};
                border: none;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {accent_color};
            }}
            QSpinBox::up-arrow {{
                width: {dp(10)}px;
                height: {dp(10)}px;
            }}
            QSpinBox::down-arrow {{
                width: {dp(10)}px;
                height: {dp(10)}px;
            }}
        """
        self.version_count_spinbox.setStyleSheet(spinbox_style)
        self.threshold_spinbox.setStyleSheet(spinbox_style)

        # CheckBox样式
        self.parallel_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                spacing: {dp(8)}px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: {dp(18)}px;
                height: {dp(18)}px;
                border: 2px solid {border_color};
                border-radius: {dp(4)}px;
                background-color: {bg_secondary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {accent_color};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_color};
                border-color: {accent_color};
            }}
        """)

        # 重置按钮样式
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(20)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton:hover {{
                color: {accent_color};
                border-color: {accent_color};
            }}
        """)

        # 保存按钮样式
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: {accent_color};
                color: {bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(20)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
            }}
        """)

    @handle_errors("加载配置")
    def loadConfig(self):
        """加载当前配置"""
        self.config_data = self.api_client.get_advanced_config()

        # 更新UI
        self.version_count_spinbox.setValue(
            self.config_data.get('writer_chapter_version_count', 3)
        )
        self.parallel_checkbox.setChecked(
            self.config_data.get('writer_parallel_generation', True)
        )
        self.threshold_spinbox.setValue(
            self.config_data.get('part_outline_threshold', 25)
        )

    @handle_errors("保存配置")
    def saveConfig(self):
        """保存配置"""
        # 收集配置数据
        config = {
            'writer_chapter_version_count': self.version_count_spinbox.value(),
            'writer_parallel_generation': self.parallel_checkbox.isChecked(),
            'part_outline_threshold': self.threshold_spinbox.value(),
        }

        # 调用API保存
        result = self.api_client.update_advanced_config(config)

        # 根据热更新结果显示不同提示
        if result.get('hot_reload', False):
            MessageService.show_success(self, "配置已保存并立即生效")
        else:
            MessageService.show_success(self, "配置已保存，重启应用后生效")

    def resetToDefaults(self):
        """恢复默认值"""
        self.version_count_spinbox.setValue(3)
        self.parallel_checkbox.setChecked(True)
        self.threshold_spinbox.setValue(25)

        MessageService.show_success(self, "已恢复默认值，点击保存生效")

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass