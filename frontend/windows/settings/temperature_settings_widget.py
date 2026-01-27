"""
Temperature配置界面 - 书籍风格

管理各个生成过程的LLM Temperature配置。
Temperature值影响生成内容的创造性：值越高越有创造力，值越低越确定性。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QPushButton, QGroupBox, QFormLayout, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors
from .config_io_helper import export_config_json, import_config_json
from .ui_helpers import (
    apply_settings_import_export_reset_save_styles,
    build_import_export_reset_save_bar,
    build_settings_group_box_style,
    build_settings_help_label_style,
    build_settings_label_style,
    build_settings_spinbox_style,
)


class TemperatureSettingsWidget(QWidget):
    """Temperature配置管理界面 - 书籍风格"""

    # 默认值定义（与后端config.py保持一致）
    DEFAULTS = {
        'llm_temp_inspiration': 0.8,
        'llm_temp_blueprint': 0.3,
        'llm_temp_outline': 0.7,
        'llm_temp_writing': 0.75,
        'llm_temp_evaluation': 0.3,
        'llm_temp_summary': 0.15,
    }

    # 配置项的中文名称和说明
    CONFIG_INFO = {
        'llm_temp_inspiration': ('灵感对话', '创意构思阶段，需要高创造力（推荐0.7-1.0）'),
        'llm_temp_blueprint': ('蓝图生成', '结构化输出，需要稳定性（推荐0.2-0.4）'),
        'llm_temp_outline': ('大纲生成', '平衡创意与结构（推荐0.5-0.8）'),
        'llm_temp_writing': ('章节写作', '内容创作，需要创造力（推荐0.6-0.9）'),
        'llm_temp_evaluation': ('章节评审', '客观分析，需要一致性（推荐0.2-0.4）'),
        'llm_temp_summary': ('摘要生成', '精确提取，需要高确定性（推荐0.1-0.3）'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.config_data = {}
        self._spinboxes = {}  # 存储所有spinbox的引用
        self._labels = {}  # 存储所有label的引用
        self._help_labels = {}  # 存储所有帮助标签的引用
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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(dp(16))

        # 顶部说明
        intro_label = QLabel(
            "Temperature 控制 LLM 输出的随机性和创造力。\n"
            "值越高（接近2.0）输出越有创造力但可能不稳定；"
            "值越低（接近0.0）输出越确定但可能重复。"
        )
        intro_label.setObjectName("intro_label")
        intro_label.setWordWrap(True)
        main_layout.addWidget(intro_label)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, dp(8), 0)
        scroll_layout.setSpacing(dp(16))

        # Temperature配置组
        self.temp_group = self._create_temperature_group()
        scroll_layout.addWidget(self.temp_group)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

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

        main_layout.addLayout(button_layout)

    def _create_spinbox_row(
        self,
        key: str,
        label_text: str,
        help_text: str,
        default_val: float,
    ) -> QWidget:
        """创建SpinBox配置行"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.0, 2.0)
        spinbox.setValue(default_val)
        spinbox.setSingleStep(0.05)
        spinbox.setDecimals(2)
        spinbox.setFixedWidth(dp(100))
        spinbox.setMinimumHeight(dp(36))
        layout.addWidget(spinbox)

        help_label = QLabel(help_text)
        layout.addWidget(help_label)
        layout.addStretch()

        # 存储引用
        self._spinboxes[key] = spinbox
        self._help_labels[key] = help_label

        return widget

    def _create_temperature_group(self) -> QGroupBox:
        """创建Temperature配置组"""
        group = QGroupBox("Temperature 配置")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))
        form_layout.setSpacing(dp(16))

        for key, (label_text, help_text) in self.CONFIG_INFO.items():
            default_val = self.DEFAULTS.get(key, 0.5)
            row = self._create_spinbox_row(key, label_text, help_text, default_val)
            label = QLabel(label_text)
            self._labels[key] = label
            form_layout.addRow(label, row)

        return group

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 介绍标签样式
        intro_style = f"""
            QLabel#intro_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: {palette.bg_secondary};
                padding: {dp(12)}px {dp(16)}px;
                border-radius: {dp(6)}px;
                border: 1px solid {palette.border_color};
            }}
        """
        self.findChild(QLabel, "intro_label").setStyleSheet(intro_style)

        # GroupBox样式 - 书香风格
        group_style = build_settings_group_box_style(palette)
        self.temp_group.setStyleSheet(group_style)

        # 标签样式
        label_style = build_settings_label_style(palette)
        for label in self._labels.values():
            label.setStyleSheet(label_style)

        # 帮助文字样式
        help_style = build_settings_help_label_style(palette)
        for help_label in self._help_labels.values():
            help_label.setStyleSheet(help_style)

        # SpinBox样式 - 温暖质感
        spinbox_style = build_settings_spinbox_style(palette, widget_type="QDoubleSpinBox")
        for spinbox in self._spinboxes.values():
            spinbox.setStyleSheet(spinbox_style)

        apply_settings_import_export_reset_save_styles(
            self,
            palette,
            save_btn=self.save_btn,
            secondary_btns=(self.reset_btn, self.import_btn, self.export_btn),
            scroll_area=self.findChild(QScrollArea),
        )

    @handle_errors("加载配置")
    def loadConfig(self):
        """加载当前配置"""
        self.config_data = self.api_client.get_temperature_config()

        # 更新UI
        for key, spinbox in self._spinboxes.items():
            value = self.config_data.get(key, self.DEFAULTS.get(key, 0.5))
            spinbox.setValue(value)

    @handle_errors("保存配置")
    def saveConfig(self):
        """保存配置"""
        # 收集配置数据
        config = {}
        for key, spinbox in self._spinboxes.items():
            config[key] = spinbox.value()

        # 调用API保存
        result = self.api_client.update_temperature_config(config)

        # 根据热更新结果显示不同提示
        if result.get('hot_reload', False):
            MessageService.show_success(self, "配置已保存并立即生效")
        else:
            MessageService.show_success(self, "配置已保存，重启应用后生效")

    def resetToDefaults(self):
        """恢复默认值"""
        for key, spinbox in self._spinboxes.items():
            default_val = self.DEFAULTS.get(key, 0.5)
            spinbox.setValue(default_val)

        MessageService.show_success(self, "已恢复默认值，点击保存生效")

    def exportConfig(self):
        """导出Temperature配置"""
        def _on_success(file_path: str, _export_data: dict):
            MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        export_config_json(
            self,
            "导出Temperature配置",
            "temperature_config.json",
            self.api_client.export_temperature_config,
            on_success=_on_success,
            error_title="错误",
            error_template="导出失败：{error}",
        )

    def importConfig(self):
        """导入Temperature配置"""
        def _on_success(result: dict):
            MessageService.show_success(self, result.get('message', '导入成功'))
            self.loadConfig()

        import_config_json(
            self,
            "导入Temperature配置",
            "temperature",
            "Temperature配置导出文件",
            self.api_client.import_temperature_config,
            on_success=_on_success,
            error_title="错误",
            error_template="导入失败：{error}",
            warning_title="格式错误",
        )

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
