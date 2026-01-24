"""
图片生成配置管理 - 书籍风格

类似于LLM配置的设计，支持多厂商的图片生成API配置。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from .base_config_list_widget import BaseConfigListWidget


# 提供商类型选项
PROVIDER_TYPES = [
    ("openai_compatible", "OpenAI 兼容接口"),
    ("stability", "Stability AI"),
    ("comfyui", "本地 ComfyUI"),
]

# 预设模型列表
PRESET_MODELS = {
    "openai_compatible": [
        "nano-banana-pro",
        "dall-e-3",
        "dall-e-2",
        "gemini-2.5-flash",
        "gemini-3-pro-image-preview",
    ],
    "stability": [
        "stable-diffusion-xl-1024-v1-0",
        "stable-diffusion-v1-6",
    ],
    "comfyui": [
        "custom",
    ],
}

# 风格选项
STYLE_OPTIONS = [
    ("none", "无"),
    ("anime", "动漫卡通"),
    ("realistic", "写实摄影"),
    ("manga", "日式漫画"),
    ("oil_painting", "油画艺术"),
    ("watercolor", "水彩插画"),
    ("render_3d", "3D渲染"),
    ("pixel", "像素艺术"),
    ("cyberpunk", "赛博朋克"),
    ("minimalist", "极简主义"),
]

# 宽高比选项
RATIO_OPTIONS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"]

# 分辨率选项
RESOLUTION_OPTIONS = ["原始", "1K", "2K"]

# 质量选项
QUALITY_OPTIONS = [
    ("draft", "草稿"),
    ("standard", "标准"),
    ("high", "高质量"),
]


class ImageConfigDialog(QDialog):
    """图片生成配置对话框"""

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        self._theme_connected = False
        self.setWindowTitle("编辑配置" if config else "新增配置")
        self.setMinimumWidth(dp(480))
        self._setup_ui()
        self._apply_styles()
        self._load_config()
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题切换信号"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题切换信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except (TypeError, RuntimeError):
                pass
            self._theme_connected = False

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def closeEvent(self, event):
        """关闭时断开信号连接"""
        self._disconnect_theme_signal()
        super().closeEvent(event)

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(dp(16))
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))

        form = QFormLayout()
        form.setSpacing(dp(12))

        # 配置名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("如：本地生图服务")
        form.addRow("配置名称:", self.name_edit)

        # 提供商类型
        self.provider_combo = QComboBox()
        for value, label in PROVIDER_TYPES:
            self.provider_combo.addItem(label, value)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("提供商类型:", self.provider_combo)

        # API地址
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("如：http://127.0.0.1:8000")
        form.addRow("API 地址:", self.url_edit)

        # API密钥
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("输入 API Key")
        form.addRow("API 密钥:", self.key_edit)

        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        # 禁用自动补全，避免将用户输入的大小写转换为预设项的大小写
        self.model_combo.setCompleter(None)
        form.addRow("默认模型:", self.model_combo)

        # API模式选择（仅OpenAI兼容接口显示）
        self.use_image_api_checkbox = QCheckBox("使用图片生成API (DALL-E等需要勾选)")
        self.use_image_api_checkbox.setToolTip(
            "勾选: 使用 /v1/images/generations 端点 (适用于DALL-E、Gemini等图片生成模型)\n"
            "不勾选: 使用 /v1/chat/completions 端点 (适用于支持图片输出的聊天模型)"
        )
        form.addRow("API模式:", self.use_image_api_checkbox)

        # 默认风格
        self.style_combo = QComboBox()
        for value, label in STYLE_OPTIONS:
            self.style_combo.addItem(label, value)
        form.addRow("默认风格:", self.style_combo)

        # 默认宽高比
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(RATIO_OPTIONS)
        form.addRow("默认宽高比:", self.ratio_combo)

        # 默认分辨率
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(RESOLUTION_OPTIONS)
        form.addRow("默认分辨率:", self.resolution_combo)

        # 默认质量
        self.quality_combo = QComboBox()
        for value, label in QUALITY_OPTIONS:
            self.quality_combo.addItem(label, value)
        form.addRow("默认质量:", self.quality_combo)

        layout.addLayout(form)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 初始化模型列表
        self._on_provider_changed(0)

    def _apply_styles(self):
        """应用样式"""
        palette = theme_manager.get_book_palette()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {palette.bg_secondary};
            }}
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_primary};
            }}
            QLineEdit, QComboBox {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                padding: {dp(8)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                background-color: {palette.bg_primary};
                color: {palette.text_primary};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {palette.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(8)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {palette.bg_primary};
                color: {palette.text_primary};
                selection-background-color: {palette.accent_color};
            }}
            QCheckBox {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                spacing: {dp(8)}px;
            }}
            QCheckBox::indicator {{
                width: {dp(16)}px;
                height: {dp(16)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(3)}px;
                background-color: {palette.bg_primary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
            QDialogButtonBox QPushButton {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                padding: {dp(8)}px {dp(20)}px;
                border-radius: {dp(4)}px;
                min-width: {dp(80)}px;
            }}
            QDialogButtonBox QPushButton[text="OK"],
            QDialogButtonBox QPushButton[text="确定"] {{
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
            }}
            QDialogButtonBox QPushButton[text="OK"]:hover,
            QDialogButtonBox QPushButton[text="确定"]:hover {{
                background-color: {palette.text_primary};
            }}
            QDialogButtonBox QPushButton[text="Cancel"],
            QDialogButtonBox QPushButton[text="取消"] {{
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
            }}
            QDialogButtonBox QPushButton[text="Cancel"]:hover,
            QDialogButtonBox QPushButton[text="取消"]:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """)

    def _on_provider_changed(self, index):
        """提供商类型改变"""
        provider = self.provider_combo.currentData()
        models = PRESET_MODELS.get(provider, [])
        self.model_combo.clear()
        self.model_combo.addItems(models)

        # 只有OpenAI兼容接口需要选择API模式
        is_openai_compatible = provider == "openai_compatible"
        self.use_image_api_checkbox.setVisible(is_openai_compatible)

    def _load_config(self):
        """加载配置数据"""
        if not self.config:
            return

        self.name_edit.setText(self.config.get('config_name', ''))

        # 设置提供商
        provider = self.config.get('provider_type', 'openai_compatible')
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break

        self.url_edit.setText(self.config.get('api_base_url', ''))
        self.key_edit.setText(self.config.get('api_key', ''))
        self.model_combo.setCurrentText(self.config.get('model_name', ''))

        # 设置风格
        style = self.config.get('default_style', 'anime')
        for i in range(self.style_combo.count()):
            if self.style_combo.itemData(i) == style:
                self.style_combo.setCurrentIndex(i)
                break

        # 设置宽高比
        ratio = self.config.get('default_ratio', '16:9')
        index = self.ratio_combo.findText(ratio)
        if index >= 0:
            self.ratio_combo.setCurrentIndex(index)

        # 设置分辨率
        resolution = self.config.get('default_resolution', '1K')
        index = self.resolution_combo.findText(resolution)
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)

        # 设置质量
        quality = self.config.get('default_quality', 'standard')
        for i in range(self.quality_combo.count()):
            if self.quality_combo.itemData(i) == quality:
                self.quality_combo.setCurrentIndex(i)
                break

        # 设置API模式
        extra_params = self.config.get('extra_params', {}) or {}
        use_image_api = extra_params.get('use_image_api', False)
        self.use_image_api_checkbox.setChecked(use_image_api)

    def getData(self) -> dict:
        """获取表单数据"""
        return {
            'config_name': self.name_edit.text().strip(),
            'provider_type': self.provider_combo.currentData(),
            'api_base_url': self.url_edit.text().strip(),
            'api_key': self.key_edit.text().strip(),
            'model_name': self.model_combo.currentText().strip(),
            'default_style': self.style_combo.currentData(),
            'default_ratio': self.ratio_combo.currentText(),
            'default_resolution': self.resolution_combo.currentText(),
            'default_quality': self.quality_combo.currentData(),
            'extra_params': {
                'use_image_api': self.use_image_api_checkbox.isChecked(),
            },
        }


class ImageSettingsWidget(BaseConfigListWidget):
    """图片生成配置管理 - 书籍风格"""

    activate_success_template = "已激活配置: {name}"
    delete_confirm_template = "确定要删除配置 \"{name}\" 吗?"
    error_message_templates = {
        "load": "加载配置失败: {error}",
        "create": "创建失败: {error}",
        "update": "更新失败: {error}",
        "delete": "删除失败: {error}",
        "activate": "激活失败: {error}",
        "export": "导出失败：{error}",
        "import": "导入失败：{error}",
    }

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 主要按钮
        self.add_btn.setStyleSheet(f"""
            QPushButton#primary_btn {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;
                font-size: {sp(13)}px;
                font-weight: 600;
            }}
            QPushButton#primary_btn:hover {{
                background-color: {palette.text_primary};
            }}
        """)

        # 次要按钮样式
        secondary_style = f"""
            QPushButton#secondary_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton#secondary_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
            QPushButton#secondary_btn:disabled {{
                color: {palette.border_color};
            }}
        """
        for btn in [self.import_btn, self.export_all_btn, self.test_btn,
                    self.activate_btn, self.edit_btn, self.export_btn]:
            btn.setStyleSheet(secondary_style)

        # 删除按钮
        self.delete_btn.setStyleSheet(f"""
            QPushButton#danger_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {theme_manager.ERROR};
                border: 1px solid {theme_manager.ERROR_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton#danger_btn:hover {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton#danger_btn:disabled {{
                color: {palette.border_color};
            }}
        """)

        # 配置列表
        self.config_list.setStyleSheet(f"""
            QListWidget#config_list {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px;
                outline: none;
            }}
            QListWidget#config_list::item {{
                background-color: transparent;
                border-left: 3px solid transparent;
                padding: {dp(16)}px {dp(12)}px;
                color: {palette.text_primary};
                border-bottom: 1px solid {palette.border_color};
            }}
            QListWidget#config_list::item:last-child {{
                border-bottom: none;
            }}
            QListWidget#config_list::item:hover {{
                background-color: {palette.bg_secondary};
                border-left: 3px solid {palette.accent_light};
            }}
            QListWidget#config_list::item:selected {{
                background-color: {palette.bg_secondary};
                border-left: 3px solid {palette.accent_color};
            }}
        """)

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def fetch_configs(self):
        return self.api_client.get_image_configs()

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get("config_name", "未命名")
        is_active = config.get("is_active", False)
        provider = config.get("provider_type", "")
        model = config.get("model_name", "")

        provider_name = dict(PROVIDER_TYPES).get(provider, provider)
        status = " [当前激活]" if is_active else ""
        return f"{name}{status}\n{provider_name}\n模型: {model}"

    def create_config_dialog(self, config=None):
        return ImageConfigDialog(config=config, parent=self)

    def create_config(self, data):
        return self.api_client.create_image_config(data)

    def update_config(self, config_id, data):
        return self.api_client.update_image_config(config_id, data)

    def delete_config(self, config_id):
        return self.api_client.delete_image_config(config_id)

    def activate_config(self, config_id):
        return self.api_client.activate_image_config(config_id)

    def test_config(self, config_id):
        return self.api_client.test_image_config(config_id)

    def export_config(self, config_id):
        return self.api_client.export_image_config(config_id)

    def export_configs(self):
        return self.api_client.export_image_configs()

    def import_configs(self, import_data):
        return self.api_client.import_image_configs(import_data)

    def get_export_all_filename(self):
        return "image_configs.json"

    def handle_test_success(self, result):
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            MessageService.show_success(self, f"连接成功: {message}")
        else:
            MessageService.show_error(self, f"连接失败: {message}", "测试结果")

    def handle_test_error(self, error_msg: str):
        MessageService.show_error(self, f"测试失败: {error_msg}", "错误")
