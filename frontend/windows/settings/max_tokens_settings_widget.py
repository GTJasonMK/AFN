"""
Max Tokens配置界面 - 书籍风格

管理各个生成过程的最大输出tokens配置。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QGroupBox, QFormLayout, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors
from .config_io_helper import export_config_json, import_config_json


class MaxTokensSettingsWidget(QWidget):
    """Max Tokens配置管理界面 - 书籍风格"""

    # 默认值定义（与后端config.py保持一致）
    DEFAULTS = {
        # 小说系统
        'llm_max_tokens_blueprint': 8192,
        'llm_max_tokens_chapter': 8192,
        'llm_max_tokens_outline': 4096,
        'llm_max_tokens_manga': 8192,
        'llm_max_tokens_analysis': 8192,
        'llm_max_tokens_default': 4096,
        # 编程系统
        'llm_max_tokens_coding_blueprint': 8192,
        'llm_max_tokens_coding_system': 8000,
        'llm_max_tokens_coding_module': 6000,
        'llm_max_tokens_coding_feature': 4000,
        'llm_max_tokens_coding_prompt': 16384,
        'llm_max_tokens_coding_directory': 20000,
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

        # 创建滚动区域（配置项较多时需要滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, dp(8), 0)
        scroll_layout.setSpacing(dp(16))

        # 小说系统配置组
        self.novel_group = self._create_novel_group()
        scroll_layout.addWidget(self.novel_group)

        # 编程系统配置组
        self.coding_group = self._create_coding_group()
        scroll_layout.addWidget(self.coding_group)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))

        # 导入按钮
        self.import_btn = QPushButton("导入配置")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(lambda: self.importConfig())
        button_layout.addWidget(self.import_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出配置")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(lambda: self.exportConfig())
        button_layout.addWidget(self.export_btn)

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

        main_layout.addLayout(button_layout)

    def _create_spinbox_row(
        self,
        key: str,
        label_text: str,
        help_text: str,
        min_val: int,
        max_val: int,
        default_val: int,
        step: int = 512,
    ) -> QWidget:
        """创建SpinBox配置行"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setSingleStep(step)
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

    def _create_novel_group(self) -> QGroupBox:
        """创建小说系统配置组"""
        group = QGroupBox("小说系统")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))
        form_layout.setSpacing(dp(16))

        # 蓝图生成
        row = self._create_spinbox_row(
            'llm_max_tokens_blueprint',
            "蓝图生成",
            "蓝图/创意构思生成的最大tokens（1024-32768）",
            1024, 32768, 8192
        )
        label = QLabel("蓝图生成")
        self._labels['llm_max_tokens_blueprint'] = label
        form_layout.addRow(label, row)

        # 章节写作
        row = self._create_spinbox_row(
            'llm_max_tokens_chapter',
            "章节写作",
            "章节内容生成的最大tokens（1024-32768）",
            1024, 32768, 8192
        )
        label = QLabel("章节写作")
        self._labels['llm_max_tokens_chapter'] = label
        form_layout.addRow(label, row)

        # 大纲生成
        row = self._create_spinbox_row(
            'llm_max_tokens_outline',
            "大纲生成",
            "章节大纲生成的最大tokens（1024-16384）",
            1024, 16384, 4096
        )
        label = QLabel("大纲生成")
        self._labels['llm_max_tokens_outline'] = label
        form_layout.addRow(label, row)

        # 漫画分镜
        row = self._create_spinbox_row(
            'llm_max_tokens_manga',
            "漫画分镜",
            "漫画分镜/提示词生成的最大tokens（1024-32768）",
            1024, 32768, 8192
        )
        label = QLabel("漫画分镜")
        self._labels['llm_max_tokens_manga'] = label
        form_layout.addRow(label, row)

        # 分析任务
        row = self._create_spinbox_row(
            'llm_max_tokens_analysis',
            "分析任务",
            "内容分析、评估任务的最大tokens（1024-32768）",
            1024, 32768, 8192
        )
        label = QLabel("分析任务")
        self._labels['llm_max_tokens_analysis'] = label
        form_layout.addRow(label, row)

        # 通用默认
        row = self._create_spinbox_row(
            'llm_max_tokens_default',
            "通用默认",
            "其他创意任务的默认最大tokens（512-16384）",
            512, 16384, 4096
        )
        label = QLabel("通用默认")
        self._labels['llm_max_tokens_default'] = label
        form_layout.addRow(label, row)

        return group

    def _create_coding_group(self) -> QGroupBox:
        """创建编程系统配置组"""
        group = QGroupBox("编程系统")

        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))
        form_layout.setSpacing(dp(16))

        # 编程蓝图
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_blueprint',
            "编程蓝图",
            "编程项目蓝图生成的最大tokens（1024-32768）",
            1024, 32768, 8192
        )
        label = QLabel("编程蓝图")
        self._labels['llm_max_tokens_coding_blueprint'] = label
        form_layout.addRow(label, row)

        # 系统生成
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_system',
            "系统生成",
            "系统架构生成的最大tokens（1024-32768）",
            1024, 32768, 8000
        )
        label = QLabel("系统生成")
        self._labels['llm_max_tokens_coding_system'] = label
        form_layout.addRow(label, row)

        # 模块生成
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_module',
            "模块生成",
            "模块设计生成的最大tokens（1024-32768）",
            1024, 32768, 6000
        )
        label = QLabel("模块生成")
        self._labels['llm_max_tokens_coding_module'] = label
        form_layout.addRow(label, row)

        # 功能大纲
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_feature',
            "功能大纲",
            "功能大纲生成的最大tokens（1024-16384）",
            1024, 16384, 4000
        )
        label = QLabel("功能大纲")
        self._labels['llm_max_tokens_coding_feature'] = label
        form_layout.addRow(label, row)

        # 功能Prompt
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_prompt',
            "功能Prompt",
            "功能Prompt生成的最大tokens（1024-32768）",
            1024, 32768, 16384
        )
        label = QLabel("功能Prompt")
        self._labels['llm_max_tokens_coding_prompt'] = label
        form_layout.addRow(label, row)

        # 目录生成
        row = self._create_spinbox_row(
            'llm_max_tokens_coding_directory',
            "目录生成",
            "目录结构生成的最大tokens（大项目需要更大值，4096-32768）",
            4096, 32768, 20000
        )
        label = QLabel("目录生成")
        self._labels['llm_max_tokens_coding_directory'] = label
        form_layout.addRow(label, row)

        return group

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # GroupBox样式 - 书香风格
        group_style = f"""
            QGroupBox {{
                font-family: {palette.serif_font};
                font-size: {sp(16)}px;
                font-weight: 700;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                margin-top: {dp(24)}px;
                padding-top: {dp(24)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {dp(16)}px;
                top: {dp(8)}px;
                padding: 0 {dp(8)}px;
                background-color: {palette.bg_secondary};
                color: {palette.accent_color};
            }}
        """
        self.novel_group.setStyleSheet(group_style)
        self.coding_group.setStyleSheet(group_style)

        # 标签样式
        label_style = f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {palette.text_primary};
                background: transparent;
            }}
        """
        for label in self._labels.values():
            label.setStyleSheet(label_style)

        # 帮助文字样式
        help_style = f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_tertiary};
                background: transparent;
                font-style: italic;
            }}
        """
        for help_label in self._help_labels.values():
            help_label.setStyleSheet(help_style)

        # SpinBox样式 - 温暖质感
        spinbox_style = f"""
            QSpinBox {{
                font-family: {palette.ui_font};
                padding: {dp(8)}px {dp(12)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                background-color: {palette.bg_primary};
                color: {palette.text_primary};
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            QSpinBox:focus {{
                border: 1px solid {palette.accent_color};
                background-color: {palette.bg_secondary};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(24)}px;
                background-color: transparent;
                border: none;
                border-radius: {dp(4)}px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {palette.border_color};
            }}
        """
        for spinbox in self._spinboxes.values():
            spinbox.setStyleSheet(spinbox_style)

        # 滚动区域样式
        scroll_style = f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {palette.bg_secondary};
                width: {dp(8)}px;
                border-radius: {dp(4)}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {palette.border_color};
                border-radius: {dp(4)}px;
                min-height: {dp(32)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {palette.text_tertiary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        self.findChild(QScrollArea).setStyleSheet(scroll_style)

        # 重置按钮样式
        secondary_btn_style = f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;
                font-size: {sp(14)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_primary};
            }}
        """
        self.reset_btn.setStyleSheet(secondary_btn_style)
        self.import_btn.setStyleSheet(secondary_btn_style)
        self.export_btn.setStyleSheet(secondary_btn_style)

        # 保存按钮样式
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}
            QPushButton:pressed {{
                background-color: {palette.accent_light};
            }}
        """)

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    @handle_errors("加载配置")
    def loadConfig(self):
        """加载当前配置"""
        self.config_data = self.api_client.get_max_tokens_config()

        # 更新UI
        for key, spinbox in self._spinboxes.items():
            value = self.config_data.get(key, self.DEFAULTS.get(key, 4096))
            spinbox.setValue(value)

    @handle_errors("保存配置")
    def saveConfig(self):
        """保存配置"""
        # 收集配置数据
        config = {}
        for key, spinbox in self._spinboxes.items():
            config[key] = spinbox.value()

        # 调用API保存
        result = self.api_client.update_max_tokens_config(config)

        # 根据热更新结果显示不同提示
        if result.get('hot_reload', False):
            MessageService.show_success(self, "配置已保存并立即生效")
        else:
            MessageService.show_success(self, "配置已保存，重启应用后生效")

    def resetToDefaults(self):
        """恢复默认值"""
        for key, spinbox in self._spinboxes.items():
            default_val = self.DEFAULTS.get(key, 4096)
            spinbox.setValue(default_val)

        MessageService.show_success(self, "已恢复默认值，点击保存生效")

    def exportConfig(self):
        """导出Max Tokens配置"""
        def _on_success(file_path: str, _export_data: dict):
            MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        export_config_json(
            self,
            "导出Max Tokens配置",
            "max_tokens_config.json",
            self.api_client.export_max_tokens_config,
            on_success=_on_success,
            error_title="错误",
            error_template="导出失败：{error}",
        )

    def importConfig(self):
        """导入Max Tokens配置"""
        def _on_success(result: dict):
            MessageService.show_success(self, result.get('message', '导入成功'))
            self.loadConfig()

        import_config_json(
            self,
            "导入Max Tokens配置",
            "max_tokens",
            "Max Tokens配置导出文件",
            self.api_client.import_max_tokens_config,
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
