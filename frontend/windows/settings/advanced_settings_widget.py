"""
高级配置界面 - 书籍风格

管理系统级配置参数，如章节生成、大纲阈值等。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QFrame, QFormLayout, QGroupBox,
    QFileDialog
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors
from .ui_helpers import (
    apply_settings_import_export_reset_save_styles,
    build_import_export_reset_save_bar,
    build_settings_group_box_style,
    build_settings_help_label_style,
    build_settings_label_style,
    build_settings_spinbox_style,
)
import json


class AdvancedSettingsWidget(QWidget):
    """高级配置管理界面 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.config_data = {}
        self._create_ui_structure()
        self._apply_styles()
        # 注意：loadConfig() 由 SettingsView._load_page_data() 延迟调用

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 功能开关配置组（放在最前面）
        self.feature_group = self._create_feature_toggles_group()
        layout.addWidget(self.feature_group)

        # 章节生成配置组
        self.chapter_group = self._create_chapter_generation_group()
        layout.addWidget(self.chapter_group)

        # 大纲配置组
        self.outline_group = self._create_outline_config_group()
        layout.addWidget(self.outline_group)

        layout.addStretch()

        # 底部按钮栏
        button_layout, buttons = build_import_export_reset_save_bar(
            on_import=self.importConfig,
            on_export=self.exportConfig,
            on_reset=self.resetToDefaults,
            on_save=self.saveConfig,
        )
        self.import_btn = buttons["import_btn"]
        self.export_btn = buttons["export_btn"]
        self.reset_btn = buttons["reset_btn"]
        self.save_btn = buttons["save_btn"]

        layout.addLayout(button_layout)

    def _create_feature_toggles_group(self):
        """创建功能开关配置组"""
        group = QGroupBox("功能开关")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))
        form_layout.setSpacing(dp(16))

        # 编程项目功能开关
        coding_widget = QWidget()
        coding_layout = QHBoxLayout(coding_widget)
        coding_layout.setContentsMargins(0, 0, 0, 0)
        coding_layout.setSpacing(dp(12))

        self.coding_enabled_checkbox = QCheckBox("启用编程项目(Prompt工程)功能")
        self.coding_enabled_checkbox.setChecked(False)  # 默认关闭
        coding_layout.addWidget(self.coding_enabled_checkbox)

        self.coding_help = QLabel("关闭后首页将隐藏编程项目相关入口")
        coding_layout.addWidget(self.coding_help)
        coding_layout.addStretch()

        form_layout.addRow("", coding_widget)

        return group

    def _create_chapter_generation_group(self):
        """创建章节生成配置组"""
        group = QGroupBox("章节生成")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))  # 修正：20不符合8pt网格
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
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))  # 修正：20不符合8pt网格
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
        palette = theme_manager.get_book_palette()

        # GroupBox样式 - 书香风格
        group_style = build_settings_group_box_style(palette)
        self.feature_group.setStyleSheet(group_style)
        self.chapter_group.setStyleSheet(group_style)
        self.outline_group.setStyleSheet(group_style)

        # 标签样式
        label_style = build_settings_label_style(palette)
        self.version_label.setStyleSheet(label_style)
        self.threshold_label.setStyleSheet(label_style)

        # 帮助文字样式
        help_style = build_settings_help_label_style(palette)
        self.coding_help.setStyleSheet(help_style)
        self.version_help.setStyleSheet(help_style)
        self.parallel_help.setStyleSheet(help_style)
        self.threshold_help.setStyleSheet(help_style)

        # SpinBox样式 - 温暖质感
        spinbox_style = build_settings_spinbox_style(palette, widget_type="QSpinBox")
        self.version_count_spinbox.setStyleSheet(spinbox_style)
        self.threshold_spinbox.setStyleSheet(spinbox_style)

        # CheckBox样式
        checkbox_style = f"""
            QCheckBox {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_primary};
                spacing: {dp(8)}px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: {dp(20)}px;
                height: {dp(20)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                background-color: {palette.bg_primary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {palette.accent_color};
            }}
            QCheckBox::indicator:checked {{
                background-color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.coding_enabled_checkbox.setStyleSheet(checkbox_style)
        self.parallel_checkbox.setStyleSheet(checkbox_style)

        apply_settings_import_export_reset_save_styles(
            self,
            palette,
            save_btn=self.save_btn,
            secondary_btns=(self.reset_btn, self.import_btn, self.export_btn),
        )

    @handle_errors("加载配置")
    def loadConfig(self):
        """加载当前配置"""
        self.config_data = self.api_client.get_advanced_config()

        # 更新UI
        self.coding_enabled_checkbox.setChecked(
            self.config_data.get('coding_project_enabled', False)
        )
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
        # 收集配置数据（保留未在UI中显示的字段的原值）
        config = {
            'coding_project_enabled': self.coding_enabled_checkbox.isChecked(),
            'writer_chapter_version_count': self.version_count_spinbox.value(),
            'writer_parallel_generation': self.parallel_checkbox.isChecked(),
            'part_outline_threshold': self.threshold_spinbox.value(),
            'agent_context_max_chars': self.config_data.get('agent_context_max_chars', 128000),
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
        self.coding_enabled_checkbox.setChecked(False)  # 编程项目默认关闭
        self.version_count_spinbox.setValue(3)
        self.parallel_checkbox.setChecked(True)
        self.threshold_spinbox.setValue(25)

        MessageService.show_success(self, "已恢复默认值，点击保存生效")

    def exportConfig(self):
        """导出高级配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出高级配置",
            "advanced_config.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                export_data = self.api_client.export_advanced_config()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"导出失败：{str(e)}", "错误")

    def importConfig(self):
        """导入高级配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入高级配置",
            "",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                # 验证数据格式
                if not isinstance(import_data, dict):
                    MessageService.show_warning(self, "导入文件格式不正确", "格式错误")
                    return

                if import_data.get('export_type') != 'advanced':
                    MessageService.show_warning(self, "导入文件类型不正确，需要高级配置导出文件", "格式错误")
                    return

                result = self.api_client.import_advanced_config(import_data)
                if result.get('success'):
                    MessageService.show_success(self, result.get('message', '导入成功'))
                    self.loadConfig()  # 重新加载配置到UI
                else:
                    MessageService.show_error(self, result.get('message', '导入失败'), "错误")
            except Exception as e:
                MessageService.show_error(self, f"导入失败：{str(e)}", "错误")

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
