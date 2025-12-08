"""
高级配置界面

管理系统级配置参数，如章节生成、大纲阈值等。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QFrame, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt
from api.client import ArborisAPIClient
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors


class AdvancedSettingsWidget(QWidget):
    """高级配置管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = ArborisAPIClient()
        self.config_data = {}
        self.setupUI()
        self.loadConfig()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(20))

        # 保存ui_font引用
        self.ui_font = theme_manager.ui_font()

        # 标题
        self.title_label = QLabel("高级配置")
        layout.addWidget(self.title_label)

        # 说明文字
        self.desc_label = QLabel("这些配置会影响章节生成和大纲规划的行为。修改后需要重启应用生效。")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 章节生成配置组
        self.chapter_group = self.createChapterGenerationGroup()
        layout.addWidget(self.chapter_group)

        # 大纲配置组
        self.outline_group = self.createOutlineConfigGroup()
        layout.addWidget(self.outline_group)

        layout.addStretch()

        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 重置按钮
        self.reset_btn = QPushButton("恢复默认值")
        self.reset_btn.clicked.connect(lambda: self.resetToDefaults())
        button_layout.addWidget(self.reset_btn)

        # 保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(lambda: self.saveConfig())
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        # 应用样式
        self._apply_styles()

    def _apply_styles(self):
        """应用主题样式（主题切换时调用）"""
        self.ui_font = theme_manager.ui_font()

        # 标题样式
        self.title_label.setStyleSheet(f"""
            font-family: {self.ui_font};
            font-size: {sp(24)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)

        # 说明文字样式
        self.desc_label.setStyleSheet(f"""
            font-family: {self.ui_font};
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            margin-bottom: {dp(10)}px;
        """)

        # 章节生成配置组样式
        self.chapter_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {self.ui_font};
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                margin-top: {dp(12)}px;
                padding-top: {dp(16)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {dp(10)}px;
                padding: 0 {dp(5)}px;
            }}
        """)

        # 大纲配置组样式
        self.outline_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {self.ui_font};
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                margin-top: {dp(12)}px;
                padding-top: {dp(16)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {dp(10)}px;
                padding: 0 {dp(5)}px;
            }}
        """)

        # SpinBox样式
        spinbox_style = self.getSpinBoxStyle()
        self.version_count_spinbox.setStyleSheet(spinbox_style)
        self.threshold_spinbox.setStyleSheet(spinbox_style)

        # CheckBox样式
        self.parallel_checkbox.setStyleSheet(self.getCheckBoxStyle())

        # 按钮样式
        self.reset_btn.setStyleSheet(ButtonStyles.secondary())
        self.save_btn.setStyleSheet(ButtonStyles.primary())

        # 更新所有label样式
        for label in self.findChildren(QLabel):
            obj_name = label.objectName()
            if obj_name == "version_label" or obj_name == "threshold_label":
                label.setStyleSheet(self.getLabelStyle())
            elif obj_name == "help_text":
                label.setStyleSheet(self.getHelpTextStyle())

    def createChapterGenerationGroup(self):
        """创建章节生成配置组"""
        group = QGroupBox("章节生成")
        # 样式由_apply_styles统一管理

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(16), dp(8), dp(16), dp(16))
        form_layout.setSpacing(dp(12))

        # 候选版本数
        self.version_count_spinbox = QSpinBox()
        self.version_count_spinbox.setRange(1, 5)
        self.version_count_spinbox.setValue(3)
        self.version_count_spinbox.setFixedWidth(dp(80))

        version_label = QLabel("候选版本数量")
        version_label.setObjectName("version_label")
        version_help = QLabel("每章生成的候选版本数（1-5个）")
        version_help.setObjectName("help_text")

        version_widget = QWidget()
        version_layout = QHBoxLayout(version_widget)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(dp(12))
        version_layout.addWidget(self.version_count_spinbox)
        version_layout.addWidget(version_help)
        version_layout.addStretch()

        form_layout.addRow(version_label, version_widget)

        # 并行生成开关
        self.parallel_checkbox = QCheckBox("启用并行生成")
        self.parallel_checkbox.setChecked(True)

        parallel_help = QLabel("多个版本同时生成，显著提升速度")
        parallel_help.setObjectName("help_text")

        parallel_widget = QWidget()
        parallel_layout = QHBoxLayout(parallel_widget)
        parallel_layout.setContentsMargins(0, 0, 0, 0)
        parallel_layout.setSpacing(dp(12))
        parallel_layout.addWidget(self.parallel_checkbox)
        parallel_layout.addWidget(parallel_help)
        parallel_layout.addStretch()

        form_layout.addRow("", parallel_widget)

        return group

    def createOutlineConfigGroup(self):
        """创建大纲配置组"""
        group = QGroupBox("大纲规划")
        # 样式由_apply_styles统一管理

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(16), dp(8), dp(16), dp(16))
        form_layout.setSpacing(dp(12))

        # 分部大纲阈值
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(10, 100)
        self.threshold_spinbox.setValue(25)
        self.threshold_spinbox.setSingleStep(5)
        self.threshold_spinbox.setFixedWidth(dp(80))

        threshold_label = QLabel("长篇分部阈值")
        threshold_label.setObjectName("threshold_label")
        threshold_help = QLabel("超过此章节数将先生成分部大纲（10-100章）")
        threshold_help.setObjectName("help_text")

        threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.setSpacing(dp(12))
        threshold_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addWidget(threshold_help)
        threshold_layout.addStretch()

        form_layout.addRow(threshold_label, threshold_widget)

        return group

    def getSpinBoxStyle(self):
        """获取SpinBox样式"""
        return f"""
            QSpinBox {{
                font-family: {self.ui_font};
                padding: {dp(8)}px {dp(12)}px;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {sp(14)}px;
            }}
            QSpinBox:focus {{
                border: 2px solid {theme_manager.PRIMARY};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {theme_manager.PRIMARY};
            }}
        """

    def getCheckBoxStyle(self):
        """获取CheckBox样式"""
        return f"""
            QCheckBox {{
                font-family: {self.ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                spacing: {dp(8)}px;
            }}
            QCheckBox::indicator {{
                width: {dp(20)}px;
                height: {dp(20)}px;
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
            QCheckBox::indicator:checked::after {{
                content: "✓";
            }}
        """

    def getLabelStyle(self):
        """获取标签样式"""
        return f"""
            font-family: {self.ui_font};
            font-size: {sp(14)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """

    def getHelpTextStyle(self):
        """获取帮助文本样式"""
        return f"""
            font-family: {self.ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
            font-style: italic;
        """

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