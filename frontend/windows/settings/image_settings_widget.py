"""
图片生成配置管理 - 书籍风格

类似于LLM配置的设计，支持多厂商的图片生成API配置。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFrame, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService, confirm
from utils.async_worker import AsyncAPIWorker


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
        self.setWindowTitle("编辑配置" if config else "新增配置")
        self.setMinimumWidth(dp(480))
        self._setup_ui()
        self._apply_styles()
        self._load_config()

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
        form.addRow("默认模型:", self.model_combo)

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
        """)

    def _on_provider_changed(self, index):
        """提供商类型改变"""
        provider = self.provider_combo.currentData()
        models = PRESET_MODELS.get(provider, [])
        self.model_combo.clear()
        self.model_combo.addItems(models)

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
        }


class ImageSettingsWidget(QWidget):
    """图片生成配置管理 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.configs = []
        self._test_worker = None
        self._create_ui_structure()
        self._apply_styles()
        self.loadConfigs()

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

        # 顶部操作栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(dp(12))

        # 新增按钮
        self.add_btn = QPushButton("+ 新增配置")
        self.add_btn.setObjectName("primary_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.createConfig)
        top_bar.addWidget(self.add_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 配置列表
        self.config_list = QListWidget()
        self.config_list.setObjectName("config_list")
        self.config_list.setMinimumHeight(dp(240))
        layout.addWidget(self.config_list, stretch=1)

        # 底部操作按钮栏
        action_bar = QHBoxLayout()
        action_bar.setSpacing(dp(12))

        # 测试按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setObjectName("secondary_btn")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.testSelectedConfig)
        action_bar.addWidget(self.test_btn)

        # 激活按钮
        self.activate_btn = QPushButton("激活")
        self.activate_btn.setObjectName("secondary_btn")
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.clicked.connect(self.activateSelectedConfig)
        action_bar.addWidget(self.activate_btn)

        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setObjectName("secondary_btn")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.editSelectedConfig)
        action_bar.addWidget(self.edit_btn)

        action_bar.addStretch()

        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("danger_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.deleteSelectedConfig)
        action_bar.addWidget(self.delete_btn)

        layout.addLayout(action_bar)

        # 初始状态禁用操作按钮
        self.updateActionButtons()
        self.config_list.itemSelectionChanged.connect(self.updateActionButtons)

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
        for btn in [self.test_btn, self.activate_btn, self.edit_btn]:
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
                color: white;
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

    def loadConfigs(self):
        """加载配置列表"""
        try:
            self.configs = self.api_client.get_image_configs()
            self.renderConfigs()
        except Exception as e:
            MessageService.show_error(self, f"加载配置失败: {str(e)}", "错误")

    def renderConfigs(self):
        """渲染配置列表"""
        self.config_list.clear()

        for config in self.configs:
            item_text = self.formatConfigText(config)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get('config_name', '未命名')
        is_active = config.get('is_active', False)
        provider = config.get('provider_type', '')
        model = config.get('model_name', '')

        # 提供商显示名称
        provider_name = dict(PROVIDER_TYPES).get(provider, provider)
        status = " [当前激活]" if is_active else ""
        return f"{name}{status}\n{provider_name}\n模型: {model}"

    def updateActionButtons(self):
        """更新操作按钮状态"""
        has_selection = len(self.config_list.selectedItems()) > 0

        self.test_btn.setEnabled(has_selection)
        self.activate_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)

        if has_selection:
            selected_item = self.config_list.selectedItems()[0]
            config = selected_item.data(Qt.ItemDataRole.UserRole)
            is_active = config.get('is_active', False)
            self.delete_btn.setEnabled(not is_active)
        else:
            self.delete_btn.setEnabled(False)

    def getSelectedConfig(self):
        """获取选中的配置"""
        items = self.config_list.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None

    def createConfig(self):
        """创建新配置"""
        dialog = ImageConfigDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.create_image_config(data)
                MessageService.show_success(self, "配置创建成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"创建失败: {str(e)}", "错误")

    def editSelectedConfig(self):
        """编辑选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        dialog = ImageConfigDialog(config=config, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.update_image_config(config['id'], data)
                MessageService.show_success(self, "配置更新成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"更新失败: {str(e)}", "错误")

    def deleteSelectedConfig(self):
        """删除选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        if confirm(self, f"确定要删除配置 \"{config['config_name']}\" 吗?", "确认删除"):
            try:
                self.api_client.delete_image_config(config['id'])
                MessageService.show_success(self, "配置已删除")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"删除失败: {str(e)}", "错误")

    def activateSelectedConfig(self):
        """激活选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        try:
            self.api_client.activate_image_config(config['id'])
            MessageService.show_success(self, f"已激活配置: {config['config_name']}")
            self.loadConfigs()
        except Exception as e:
            MessageService.show_error(self, f"激活失败: {str(e)}", "错误")

    def testSelectedConfig(self):
        """测试选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        self._cleanup_test_worker()

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")

        self._test_worker = AsyncAPIWorker(
            self.api_client.test_image_config,
            config['id']
        )
        self._test_worker.success.connect(self._on_test_success)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.start()

    def _on_test_success(self, result: dict):
        """测试成功回调"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        success = result.get('success', False)
        message = result.get('message', '')

        if success:
            MessageService.show_success(self, f"连接成功: {message}")
        else:
            MessageService.show_error(self, f"连接失败: {message}", "测试结果")

    def _on_test_error(self, error_msg: str):
        """测试失败回调"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        MessageService.show_error(self, f"测试失败: {error_msg}", "错误")

    def _cleanup_test_worker(self):
        """清理测试Worker"""
        if self._test_worker is not None:
            try:
                if self._test_worker.isRunning():
                    self._test_worker.cancel()
                    self._test_worker.quit()
                    self._test_worker.wait(3000)
            except RuntimeError:
                pass
            finally:
                self._test_worker = None

    def __del__(self):
        """析构时断开信号连接"""
        self._cleanup_test_worker()
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
